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
    "FlexiCubes, scalar field optimization (Adam + RMSE)",
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
    (f"cells={r}", {"cells": r}) for r in [8, 16, 24]
]

large_resolution_settings = [
    (f"cells={r}", {"cells": r}) for r in [32, 64, 128]
]


# R functions

function_sphere = (
    "Sphere",
    fn.Sphere(radius=0.3),
    ((-.3, .3), (-.3, .3), (-.3, .3))
)

function_sdf_sphere = (
    "SDF sphere",
    fn.SDFSphere(radius=0.3),
    ((-.3, .3), (-.3, .3), (-.3, .3))
)

function_cube_with_hole = (
    "Cube with hole",
    (
        fn.Box(size=(0.2, 0.2, 0.2)) & ~fn.CylinderZ(radius=0.1, height=8.0)
    ),
    ((-.21, .21), (-.21, .21), (-.21, .21))
)

function_cube_with_hole_thin_walls = (
    "Cube with hole, thin walls",
    (
        fn.Box(size=(0.2, 0.2, 0.2)) & ~fn.CylinderZ(radius=0.18, height=8.0)
    ),
    ((-.21, .21), (-.21, .21), (-.21, .21))
)

function_arc = (
    "Arc",
    (
        fn.Arc(
            center=(0, 0, 0),
            r1=.2,
            r2=.4,
            r3=.1,
            d1=.6,
            d2=.2,
            d3=.8,
        )
    ),
    ((-.01, .41), (-.41, .41), (-.41, .41))
)
