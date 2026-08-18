from render import visualize_side_by_side
import settings as s
from compute import compute_single_function, compute_single_algorithm


def visualize_function_diff(algorithms, function_config, settings):
    data = compute_single_function(algorithms, function_config, settings)
    for heading, results in data.items():
        visualize_side_by_side(results, heading)


def visualize_algorithm_diff(algorithm, functions, settings):
    data = compute_single_algorithm(algorithm, functions, settings)
    for heading, results in data.items():
        visualize_side_by_side(results, heading)


visualize_algorithm_diff(
    s.algorithm_flexicubes_default,
    [s.function_sphere, s.function_sdf_sphere],
    [("playground resolution", {'cells': 10})]
)


visualize_function_diff(
    s.algorithms_marching_cubes,
    s.function_cube_with_hole,
    [("playground resolution", {'cells': 10})]
)
