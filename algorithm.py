import gc
import time
import torch
import tracemalloc
import trimesh
import tqdm

import numpy as np

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from skimage.measure import marching_cubes

from r import AbstractRF, Array3D
from flexicubes import FlexiCubes as FC


NUMBER_OF_TEST_SAMPLES = 5000
DEGENERATE_TRIANGLE_AREA = 1e-9

type DimensionRange = tuple[float, float]
type ResultDimensions = tuple[DimensionRange, DimensionRange, DimensionRange]
type IntermediateMeshResult = tuple[Array3D, Array3D]


@dataclass
class HistoryItem:
    title: str
    mesh: trimesh.Trimesh


@dataclass
class FitMeta:
    elapsed_time_seconds: float = field(
        default=0,
        metadata={"title": "Computation time, seconds"}
    )
    mean_error: float = field(
        default=0,
        metadata={"title": "Mean Error"}
    )
    max_error: float = field(
        default=0,
        metadata={"title": "Max Error"}
    )
    rmse_error: float = field(
        default=0,
        metadata={"title": "RMSE Error"}
    )
    elapsed_memory: int = field(
        default=0,
        metadata={"title": "Memory used for building mesh, bytes"}
    )
    triangle_count: int = field(
        default=0,
        metadata={"title": "Number of triangles"}
    )
    degenerate_faces: int = field(
        default=0,
        metadata={"title": "Number of degenerate triangles"}
    )
    consistent_winding: bool = field(
        default=False,
        metadata={"title": "Is mesh manifold"}
    )
    watertight: bool = field(
        default=False,
        metadata={"title": "Is mesh watertight"}
    )


class AbstractAlgorithm(ABC):
    def __init__(self, options: dict):
        self.settings = self.parse_settings(options)
        self._history: list[HistoryItem] = []

    def __str__(self):
        return f"{self.__class__.__name__}({self.options})"

    @abstractmethod
    def parse_settings(self, options: dict) -> dict:
        raise NotImplementedError("Unable to parse options")

    @abstractmethod
    def _do_fit(self, r_function) -> IntermediateMeshResult:
        raise NotImplementedError("Unable to fit this algorithm")

    def fit(self, r_function: AbstractRF, dimensions: ResultDimensions):
        self._meta = FitMeta()
        self._history: list[HistoryItem] = []
        self._result_dimensions = dimensions
        gc.disable()
        tracemalloc.start()
        memory_start, peak_start = tracemalloc.get_traced_memory()
        start = time.perf_counter()
        try:
            vertices, faces = self._do_fit(r_function)
        finally:
            memory_end, peak_end = tracemalloc.get_traced_memory()
            end = time.perf_counter()
            self._meta.elapsed_time_seconds = end - start
            self._meta.elapsed_memory = memory_end - memory_start
            tracemalloc.stop()
            gc.enable()

        self._meta.triangle_count = len(faces)
        self._add_history_item("Result", vertices, faces)
        self._calculate_deviation(r_function)

    @property
    def meta(self):
        return self._meta

    @property
    def history(self):
        return self._history

    @property
    def mesh(self):
        return self._history[-1].mesh

    def _scale_mesh(self, mesh: trimesh.Trimesh):
        dimensions = np.array(self._result_dimensions)
        v = mesh.vertices
        scaled_vertices = (v - v.min()) / (v.max() - v.min())
        scaled_vertices = (
            scaled_vertices * (dimensions[:, 1] - dimensions[:, 0]).T
        ) - abs(dimensions[:, 0])
        return trimesh.Trimesh(vertices=scaled_vertices, faces=mesh.faces)

    def _calculate_deviation(self, r_function: AbstractRF):
        mesh = self.mesh
        self._meta.watertight = mesh.is_watertight
        self._meta.consistent_winding = mesh.is_winding_consistent
        self._meta.degenerate_faces = np.sum(
            mesh.area_faces < DEGENERATE_TRIANGLE_AREA
        )
        mesh = self._scale_mesh(mesh)
        points, face_index = trimesh.sample.sample_surface(
            mesh, NUMBER_OF_TEST_SAMPLES
        )
        sdf_values = r_function.compute(
            points[:, 0], points[:, 1], points[:, 2]
        )
        self._meta.mean_error = np.mean(np.abs(sdf_values))
        self._meta.max_error = np.max(np.abs(sdf_values))
        self._meta.rmse_error = np.sqrt(np.mean(sdf_values**2))
        self._add_history_item("Scaled result", mesh.vertices, mesh.faces)

    def _add_history_item(self, title: str, vertices: Array3D, faces: Array3D):
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        self._history.append(HistoryItem(title=title, mesh=mesh))


class MarchingCubes(AbstractAlgorithm):
    def parse_settings(self, options):
        return {
            "resolution": options.get("resolution", 5),
            "method": options.get("method", "lewiner"),
        }

    def _do_fit(self, r_function: AbstractRF):
        volume = self._get_volume(r_function)
        verts, faces, normals, values = marching_cubes(
            volume, level=0.0, method=self.settings["method"]
        )
        return verts, faces

    def _get_volume(self, r_function: AbstractRF):
        xmin, xmax = -.5, .5
        ymin, ymax = -.5, .5
        zmin, zmax = -.5, .5
        resolution = self.settings["resolution"]
        x = np.linspace(xmin, xmax, resolution)
        y = np.linspace(ymin, ymax, resolution)
        z = np.linspace(zmin, zmax, resolution)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
        return r_function.compute(X, Y, Z)


class FlexiCubes(AbstractAlgorithm):
    def parse_settings(self, options):
        return {
            "resolution": options.get("resolution", 5),
            "iterations": options.get("iterations", 400),
            "device": options.get("device", "cpu"),
            "method": options.get("method", "default"),
            "learning_rate": options.get("learning_rate", 0.05),
            "gradient_step": options.get("gradient_step", 1e-6),
            "scale": options.get("scale", 1.0),
        }

    def _do_fit(self, r_function: AbstractRF):
        match self.settings["method"]:
            case "default":
                return self.fit_default(r_function)
            case "learn":
                return self.fit_learn(r_function)
            case "gradient":
                return self.fit_gradient(r_function)
            case method:
                raise ValueError(f"Unknown learning method {method}")

    def fit_default(self, r_function: AbstractRF):
        device = self.settings["device"]
        resolution = self.settings["resolution"]

        fc = FC(device)
        x_nx3, cube_fx8 = fc.construct_voxel_grid(resolution)
        x_nx3 *= self.settings["scale"]

        x, y, z = x_nx3.split(1, dim=1)
        sdf = r_function.compute(x, y, z)

        vertices, faces, L_dev = fc(
            x_nx3,
            sdf,
            cube_fx8,
            resolution
        )
        return vertices.detach().cpu().numpy(), faces.detach().cpu().numpy()

    def fit_gradient(self, r: AbstractRF):
        device = self.settings["device"]
        resolution = self.settings["resolution"]

        fc = FC(device)
        x_nx3, cube_fx8 = fc.construct_voxel_grid(resolution)
        x_nx3 *= self.settings["scale"]

        x, y, z = x_nx3.split(1, dim=1)
        sdf = r.compute(x, y, z)

        def grad_f(x3):
            h = self.settings["gradient_step"]
            x, y, z = x3.split(1, dim=1)
            dh = 2 * h
            df_dx = (r.compute(x + h, y, z) - r.compute(x - h, y, z)) / dh
            df_dy = (r.compute(x, y + h, z) - r.compute(x, y - h, z)) / dh
            df_dz = (r.compute(x, y, z + h) - r.compute(x, y, z - h)) / dh
            result = torch.stack([df_dx, df_dy, df_dz], axis=1)
            return result

        vertices, faces, L_dev = fc(
            x_nx3,
            sdf,
            cube_fx8,
            resolution,
            grad_func=grad_f
        )
        return vertices.detach().cpu().numpy(), faces.detach().cpu().numpy()

    def fit_learn(self, r_function: AbstractRF):
        device = self.settings["device"]
        resolution = self.settings["resolution"]
        learning_rate = self.settings["learning_rate"]
        iterations = self.settings["iterations"]

        fc = FC(device)
        x_nx3, cube_fx8 = fc.construct_voxel_grid(resolution)
        x_nx3 *= self.settings["scale"]

        sdf = torch.rand_like(x_nx3[:, 0]) - 0.1
        sdf = torch.nn.Parameter(sdf.clone().detach(), requires_grad=True)

        weight = torch.zeros(
            (cube_fx8.shape[0], 21), dtype=torch.float, device=device
        )
        weight = torch.nn.Parameter(
            weight.clone().detach(), requires_grad=True
        )
        deform = torch.nn.Parameter(
            torch.zeros_like(x_nx3), requires_grad=True
        )
        grid_verts = x_nx3 + (2-1e-8) / (resolution * 2) * torch.tanh(deform)

        vertices, faces, L_dev = fc(
            grid_verts,
            sdf,
            cube_fx8,
            resolution,
            beta_fx12=weight[:, :12],
            alpha_fx8=weight[:, 12:20],
            gamma_f=weight[:, 20],
            training=False
        )

        self._add_history_item(
            title="Initial Mesh",
            vertices=vertices.detach().cpu().numpy(),
            faces=faces.detach().cpu().numpy()
        )

        def lr_schedule(iteration):
            return max(0.0, 10 ** (-(iteration) * 0.0002))

        optimizer = torch.optim.Adam([sdf, weight, deform], lr=learning_rate)

        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer,
            lr_lambda=lr_schedule
        )

        def res(xyz):
            x, y, z = xyz.split(1, dim=1)
            return r_function.compute(x, y, z)

        def sdf_diff(sdf, verts):
            target = res(verts).reshape(-1)
            diff = ((target.nan_to_num(0.1)-sdf.nan_to_num(0.1))**2).mean()
            diff = ((target-sdf)**2).mean()
            return diff

        for it in tqdm.tqdm(range(iterations)):
            optimizer.zero_grad()
            grid_verts = x_nx3
            vertices, faces, L_dev = fc(
                grid_verts,
                sdf,
                cube_fx8,
                resolution,
                beta_fx12=weight[:, :12],
                alpha_fx8=weight[:, 12:20],
                gamma_f=weight[:, 20],
                training=True
            )
            sdf_loss = sdf_diff(sdf, grid_verts)
            total_loss = sdf_loss
            total_loss.backward()
            optimizer.step()
            scheduler.step()
            if (it + 1) % 20 == 0:
                with torch.no_grad():
                    v, f, L_dev = fc(
                        grid_verts,
                        sdf,
                        cube_fx8,
                        resolution,
                        beta_fx12=weight[:, :12],
                        alpha_fx8=weight[:, 12:20],
                        gamma_f=weight[:, 20],
                        training=False
                    )
                    self._add_history_item(
                        title=f"Iteration {it+1}",
                        vertices=v.detach().cpu().numpy(),
                        faces=f.detach().cpu().numpy()
                    )
        with torch.no_grad():
            v, f, L_dev = fc(
                grid_verts,
                sdf,
                cube_fx8,
                resolution,
                beta_fx12=weight[:, :12],
                alpha_fx8=weight[:, 12:20],
                gamma_f=weight[:, 20],
                training=False
            )
            return v.detach().cpu().numpy(), f.detach().cpu().numpy()
