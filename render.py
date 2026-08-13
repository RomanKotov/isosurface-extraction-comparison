import pandas as pd
import numpy as np
import math
import trimesh

from dataclasses import fields
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from core.algorithm import AbstractAlgorithm, FitMeta
from core.function import AbstractFunction

COLORMAP = plt.colormaps['Spectral']


def render_static(mesh: trimesh.Trimesh):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    m = Poly3DCollection(mesh.vertices[mesh.faces])
    m.set_edgecolor('k')
    ax.add_collection3d(m)
    plt.tight_layout()
    plt.show()


def render_diff(mesh: trimesh.Trimesh, function: AbstractFunction):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    data = mesh.vertices[mesh.faces]
    n_faces, n_items, n_cols = data.shape
    reshaped = np.array(mesh.triangles_center)
    diff = function.compute(
        reshaped[:, 0], reshaped[:, 1], reshaped[:, 2]
    )
    diff_max = np.max(np.abs(diff))
    diff_min = - diff_max
    norm = Normalize(vmin=diff_min, vmax=diff_max)
    colors = COLORMAP(norm(diff))

    m = Poly3DCollection(data)
    m.set_edgecolor('black')
    m.set_facecolor(colors)
    ax.add_collection3d(m)
    ax.set_box_aspect([1, 1, 1])

    sm = cm.ScalarMappable(norm=norm, cmap=COLORMAP)
    sm.set_array([])
    fig.subplots_adjust(right=0.95)
    fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.04, label="Difference")

    plt.tight_layout()
    plt.show()


def visualize_side_by_side(
        function: AbstractFunction,
        results: dict[str, AbstractAlgorithm],
        suptitle: str
):
    ncols = 3 if len(results) > 4 else 2
    ncols = min(len(results), ncols)
    nrows = math.ceil(len(results) / ncols)
    results_to_render = iter(results.items())
    diff_max = 0
    preprocessed = []
    for row in range(nrows):
        for col in range(ncols):
            item = next(results_to_render, None)
            if item is None:
                break

            title, algorithm = item
            mesh = algorithm.mesh
            data = mesh.vertices[mesh.faces]
            n_faces, n_items, n_cols = data.shape
            reshaped = np.array(mesh.triangles_center)
            diff = function.compute(
                reshaped[:, 0], reshaped[:, 1], reshaped[:, 2]
            )
            diff_max = max(np.max(np.abs(diff)), diff_max)
            preprocessed.append({
                "title": title,
                "diff": diff,
                "data": data,
                "position": (nrows, ncols, row * ncols + col + 1),
            })

    diff_min = -diff_max
    norm = Normalize(vmin=diff_min, vmax=diff_max)
    axes = []
    fig = plt.figure(figsize=(ncols * 5, nrows * 5))
    for item in preprocessed:
        ax = fig.add_subplot(*item["position"], projection='3d')
        colors = COLORMAP(norm(item["diff"]))

        m = Poly3DCollection(item["data"])
        m.set_edgecolor('black')
        m.set_facecolor(colors)
        ax.add_collection3d(m)
        ax.set_box_aspect([1, 1, 1])
        ax.set_title(item["title"])
        axes.append(ax)

    sm = cm.ScalarMappable(norm=norm, cmap=COLORMAP)
    sm.set_array([])
    fig.subplots_adjust(right=0.95, hspace=0.02)
    fig.colorbar(sm, ax=axes, shrink=0.8, pad=0.02, label="Difference")
    fig.suptitle(suptitle)

    plt.show()


def table_results(results: dict[str, AbstractAlgorithm]):
    table_columns = [{
        "key": f.name,
        "title": f.metadata["title"]
    } for f in fields(FitMeta)]

    def process_item(item: AbstractAlgorithm):
        return {
            col["title"]: getattr(item.meta, col["key"])
            for col in table_columns
        }
    return pd.DataFrame.from_dict({
        title: process_item(results[title])
        for title in results
    }, orient="index")
