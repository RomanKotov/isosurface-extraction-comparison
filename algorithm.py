import time
import torch
import tqdm

import numpy as np

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from skimage.measure import marching_cubes

from r import AbstractRF, Array3D
from flexicubes import FlexiCubes as FC


@dataclass
class Mesh:
    vertices: Array3D
    faces: Array3D


@dataclass
class HistoryItem:
    title: str
    mesh: Mesh


@dataclass
class FitMeta:
    elapsed_time_seconds: float = field(default=0)


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
    def _do_fit(self, r_function) -> Mesh:
        raise NotImplementedError("Unable to fit this algorithm")

    def fit(self, r_function: AbstractRF):
        self._meta = FitMeta()
        self._history: list[HistoryItem] = []
        start = time.perf_counter()
        self._mesh = self._do_fit(r_function)
        end = time.perf_counter()
        self._meta.elapsed_time_seconds = end - start

    @property
    def meta(self):
        return self._meta

    @property
    def history(self):
        return self._history

    @property
    def mesh(self):
        return self._mesh

    def _add_history_item(self, item: HistoryItem):
        self._history.append(item)


class MarchingCubes(AbstractAlgorithm):
    def parse_settings(self, options):
        return {
            "resolution": options.get("resolution", 5),
            "x_range": options.get("x_range", (-1, 1)),
            "y_range": options.get("y_range", (-1, 1)),
            "z_range": options.get("z_range", (-1, 1)),
        }

    def _do_fit(self, r_function: AbstractRF):
        xmin, xmax = self.settings["x_range"]
        ymin, ymax = self.settings["y_range"]
        zmin, zmax = self.settings["z_range"]
        resolution = self.settings["resolution"]
        x = np.linspace(xmin, xmax, resolution)
        y = np.linspace(ymin, ymax, resolution)
        z = np.linspace(zmin, zmax, resolution)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")

        volume = r_function.compute(X, Y, Z)
        verts, faces, normals, values = marching_cubes(volume, level=0.0)
        return Mesh(vertices=verts, faces=faces)


class FlexiCubes(AbstractAlgorithm):
    def parse_settings(self, options):
        return {
            "resolution": options.get("resolution", 5),
            "iterations": options.get("iterations", 200),
            "x_range": options.get("x_range", (-1, 1)),
            "y_range": options.get("y_range", (-1, 1)),
            "z_range": options.get("z_range", (-1, 1)),
            "device": options.get("device", "cpu"),
            "learning_rate": options.get("learning_rate", 0.01),
        }

    def _do_fit(self, r_function: AbstractRF):
        device = self.settings["device"]
        resolution = self.settings["resolution"]
        learning_rate = self.settings["learning_rate"]
        iterations = self.settings["iterations"]
        fc = FC(device)
        x_nx3, cube_fx8 = fc.construct_voxel_grid(resolution)
        sdf = torch.rand_like(x_nx3[:, 0]) - 0.1
        sdf = torch.nn.Parameter(sdf.clone().detach(), requires_grad=True)
        weight = torch.zeros(
            (cube_fx8.shape[0], 21), dtype=torch.float, device=device)
        weight = torch.nn.Parameter(
            weight.clone().detach(), requires_grad=True)
        all_edges = cube_fx8[:, fc.cube_edges].reshape(-1, 2)
        grid_edges = torch.unique(all_edges, dim=0)
        deform = torch.nn.Parameter(
            torch.zeros_like(x_nx3), requires_grad=True)
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

        self._add_history_item(HistoryItem(
            title="Initial Mesh",
            mesh=Mesh(
                vertices=vertices.detach().cpu().numpy(),
                faces=faces.detach().cpu().numpy()
            )
        ))

        def lr_schedule(iteration):
            return max(0.0, 10 ** (-(iteration) * 0.0002))

        optimizer = torch.optim.Adam([sdf, weight, deform], lr=learning_rate)

        scheduler = torch.optim.lr_scheduler.LambdaLR(
            optimizer,
            lr_lambda=lr_schedule
        )

        def res(xyz):
            x, y, z = grid_verts.split(1, dim=1)
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
                        HistoryItem(
                            title=f"Iteration {it+1}",
                            mesh=Mesh(
                                vertices=v.detach().cpu().numpy(),
                                faces=f.detach().cpu().numpy()
                            )
                        )
                    )
        return self.history[-1].mesh
