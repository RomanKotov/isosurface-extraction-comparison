import pandas as pd
import numpy as np
import trimesh

from dataclasses import fields
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from algorithm import AbstractAlgorithm, FitMeta
from r import AbstractRF

COLORMAP = plt.colormaps['Spectral']


def render_static(mesh: trimesh.Trimesh):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    m = Poly3DCollection(mesh.vertices[mesh.faces])
    m.set_edgecolor('k')
    ax.add_collection3d(m)
    plt.tight_layout()
    plt.show()


def render_diff(mesh: trimesh.Trimesh, r_function: AbstractRF):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    data = mesh.vertices[mesh.faces]
    n_faces, n_items, n_cols = data.shape
    reshaped = np.array(mesh.triangles_center)
    diff = r_function.compute(
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


def table_results(results: dict[str, AbstractAlgorithm]):
    table_columns = [f.name for f in fields(FitMeta)]

    def process_item(item: AbstractAlgorithm):
        return {
            col: getattr(item.meta, col) for col in table_columns
        }
    return pd.DataFrame.from_dict({
        title: process_item(results[title])
        for title in results
    }, orient="index")
