import pandas as pd

from dataclasses import fields
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from algorithm import Mesh, AbstractAlgorithm, FitMeta


def render_static(mesh: Mesh):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    m = Poly3DCollection(mesh.vertices[mesh.faces])
    m.set_edgecolor('k')
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
