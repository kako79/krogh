import GPyOpt as opt
from solver import integrate
from parameters import Parameters


def search(initial_params, target_param_name, target_param_value, search_param_ranges, tolerance=1, max_iter=20,
           job_number=0):

    space = [
        {
            'name': param_name,
            'type': 'continuous',
            'domain': (param_range[0].magnitude, param_range[1].magnitude)
        }
        for param_name, param_range in search_param_ranges.items()
    ]

    param_names = [item['name'] for item in space]
    results_cache = dict()

    def log(s):
        print("[{}] {}".format(job_number, s))

    # Evaluates the objective for a given set of search parameter values.
    def evaluate(param_values):
        param_values = param_values[0]
        log("Evaluating %s" % param_values)
        eval_params = initial_params.to_unitless()
        for p in range(len(param_names)):
            eval_params[param_names[p]] = param_values[p]

        params = Parameters.from_unitless(eval_params)
        result = integrate(**params)
        results_cache[str(param_values)] = result

        result_value = result[target_param_name].magnitude
        objective_value = (result_value - target_param_value.magnitude) ** 2
        log("result %s: %s, target %s: %s, objective value: %s"
            % (target_param_name, result_value, target_param_name, target_param_value, objective_value))

        return objective_value

    bo = opt.methods.BayesianOptimization(evaluate, maximize=False, domain=space, initial_design_numdata=3,
                                          normalize_Y=True, verbosity=True, verbosity_model=True, de_duplication=True,
                                          exact_feval=True)

    bo.run_optimization(max_iter=max_iter, eps=tolerance, verbosity=True)

    opt_param_values = bo.x_opt
    results = results_cache[str(opt_param_values)]

    return_params = initial_params.copy()
    for i in range(len(param_names)):
        name = param_names[i]
        value = opt_param_values[i] * search_param_ranges[name][0].units
        return_params[name] = value

    return results, return_params
