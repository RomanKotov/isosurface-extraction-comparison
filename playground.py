from render import visualize_side_by_side
import settings as s
from compute import compute_with_settings


def visualize_diff(algorithms, r_function_config, settings):
    data = compute_with_settings(algorithms, r_function_config, settings)
    _title, fun, _dimensions = r_function_config
    for heading, results in data.items():
        visualize_side_by_side(fun, results, heading)


visualize_diff(
    s.algorithms_marching_cubes,
    s.function_cube_with_hole,
    [("playground resolution", {'resolution': 10})]
)
