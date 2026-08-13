import core.algorithm as algorithm
import core.function as fn


# Isosurface algorithms

algorithm_marching_cubes_lewiner = (
    "Marching Cubes, Lewiner",
    algorithm.MarchingCubes,
    {"method": "lewiner"}
)

algorithm_marhing_cubes_lorensen = (
    "Marching Cubes, Lorensen",
    algorithm.MarchingCubes,
    {"method": "lorensen"}
)

algorithm_flexicubes_default = (
    "FlexiCubes, default",
    algorithm.FlexiCubes,
    {"method": "default"}
)

algorithm_flexicubes_gradient = (
    "FlexiCubes, gradient",
    algorithm.FlexiCubes,
    {"method": "gradient"}
)

algorithm_flexicubes_learn = (
    "FlexiCubes, learn from random",
    algorithm.FlexiCubes,
    {"method": "learn"}
)

algorithms_marching_cubes = [
    algorithm_marching_cubes_lewiner,
    algorithm_marhing_cubes_lorensen
]

algorithms_flexicubes = [
    algorithm_flexicubes_default,
    algorithm_flexicubes_gradient,
    algorithm_flexicubes_learn,
]

all_algorithms = [
    *algorithms_marching_cubes,
    *algorithms_flexicubes
]


# Resolution settings

resolution_settings = [
    (f"resolution={r}", {"resolution": r}) for r in [10, 20, 30]
]

large_resolution_settings = [
    (f"resolution={r}", {"resolution": r}) for r in [64, 128, 256]
]


# R functions

function_sphere = (
    "Sphere",
    fn.Sphere(radius=0.3),
    ((-.3, .3), (-.3, .3), (-.3, .3))
)

function_cube_with_hole = (
    "Cube with hole",
    (
        fn.Box(size=(0.2, 0.2, 0.2)) & ~fn.CylinderZ(radius=0.1, height=8.0)
    ),
    ((-.2, .2), (-.2, .2), (-.2, .2))
)

function_cube_with_hole_thin_walls = (
    "Cube with hole, thin walls",
    (
        fn.Box(size=(0.2, 0.2, 0.2)) & ~fn.CylinderZ(radius=0.18, height=8.0)
    ),
    ((-.2, .2), (-.2, .2), (-.2, .2))
)

function_cube_with_hole_close_to_max = (
    "Cube with hole, close to max",
    (
        fn.Box(size=(0.49, 0.49, 0.49)) & ~fn.CylinderZ(radius=0.1, height=8.0)
    ),
    ((-.49, .49), (-.49, .49), (-.49, .49))
)
