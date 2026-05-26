from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from algorithm import Mesh


def render_static(mesh: Mesh):
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')

    m = Poly3DCollection(mesh.vertices[mesh.faces])
    m.set_edgecolor('k')
    ax.add_collection3d(m)
    plt.tight_layout()
    plt.show()
