import pandas as pd
import numpy as np
import trimesh

from dataclasses import fields
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from algorithm import AbstractAlgorithm, FitMeta
from r import AbstractRF

COLORMAP = plt.colormaps['bwr']


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
    diff_min = np.min(diff)
    diff_max = np.max(diff)
    normalized_diff = (diff - diff_min) / (diff_max - diff_min)

    colors = COLORMAP(normalized_diff)

    m = Poly3DCollection(data)
    m.set_edgecolor('black')
    m.set_facecolor(colors)

    ax.add_collection3d(m)
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
