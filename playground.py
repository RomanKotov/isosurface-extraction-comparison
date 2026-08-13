from render import (
    visualize_algorithms_side_by_side,
    visualize_functions_side_by_side
)
import settings as s
from compute import compute_single_function, compute_single_algorithm


def visualize_function_diff(algorithms, function_config, settings):
    data = compute_single_function(algorithms, function_config, settings)
    _title, fun, _dimensions = function_config
    for heading, results in data.items():
        visualize_algorithms_side_by_side(fun, results, heading)


def visualize_algorithm_diff(algorithm, functions, settings):
    data = compute_single_algorithm(algorithm, functions, settings)
    for heading, results in data.items():
        visualize_functions_side_by_side(results, heading)


visualize_algorithm_diff(
    s.algorithm_marhing_cubes_lorensen,
    [s.function_cube_with_hole, s.function_cube_with_hole_close_to_max],
    [("playground resolution", {'resolution': 10})]
)


visualize_function_diff(
    s.algorithms_marching_cubes,
    s.function_cube_with_hole,
    [("playground resolution", {'resolution': 10})]
)
