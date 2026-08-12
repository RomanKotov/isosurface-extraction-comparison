def process_r_function(algorithms, fun, extra_settings, dimensions):
    results = {}
    for title, Algorithm, default_settings in algorithms:
        updated_settings = {**default_settings, **extra_settings}
        print(f"Processing: {title}")
        algo = Algorithm(updated_settings)
        algo.fit(fun, dimensions)
        results[title] = algo
    return results


def compute_with_settings(algorithms, function_settings, settings):
    results = {}
    fun_name, fun, dimensions = function_settings
    for config_name, config_options in settings:
        heading = f"{fun_name}, {config_name}"
        print(heading)
        result = process_r_function(
            algorithms, fun, config_options, dimensions
        )
        results[heading] = result
    return results
