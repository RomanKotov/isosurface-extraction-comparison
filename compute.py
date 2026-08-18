def process_single_function_many_algorithms(
        algorithms, fun, extra_settings, dimensions
):
    results = {}
    for title, Algorithm, default_settings in algorithms:
        updated_settings = {**default_settings, **extra_settings}
        print(f"Processing: {title}")
        algo = Algorithm(updated_settings)
        algo.fit(fun, dimensions)
        results[title] = algo
    return results


def compute_single_function(algorithms, function_settings, settings):
    results = {}
    fun_name, fun, dimensions = function_settings
    for config_name, config_options in settings:
        heading = f"{fun_name}, {config_name}"
        print(heading)
        result = process_single_function_many_algorithms(
            algorithms, fun, config_options, dimensions
        )
        results[heading] = result
    return results


def process_single_algorithm_many_functions(
        algorithm, functions, extra_settings
):
    results = {}
    _title, Algorithm, default_settings = algorithm
    updated_settings = {**default_settings, **extra_settings}
    for fun_name, fun, dimensions in functions:
        print(f"Processing: {fun_name}")
        algo = Algorithm(updated_settings)
        algo.fit(fun, dimensions)
        results[fun_name] = algo
    return results


def compute_single_algorithm(algorithm, functions, settings):
    results = {}
    title, _algo, _default_settings = algorithm
    for config_name, config_options in settings:
        heading = f"{title}, {config_name}"
        print(heading)
        result = process_single_algorithm_many_functions(
            algorithm, functions, config_options
        )
        results[heading] = result
    return results
