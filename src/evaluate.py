import multiprocessing
import os
from solver import integrate
from joblib import Parallel, delayed
from units import get_units


def search(initial_params, is_finished, get_next_params):
    params = initial_params
    results = integrate(**params)
    while not is_finished(results):
        params = get_next_params(params)
        results = integrate(**params)

    return results, params


def evaluate_point(params):
    is_test = params.get("test", False)
    job_number = params.get("job_number", 0)

    def log(s):
        print("[{}] {}".format(job_number, s))

    results = {
        "params": params
    }

    # First get the results at the specified parameter values.
    base_results = integrate(**params)

    results["base_results"] = base_results
    log("Base results done.")

    if params["paO2_multiple"] == 1.0:
        results["paO2_results"] = base_results
        paO2_results = base_results
    else:
        paO2_params = params.copy()
        paO2_params["paO2"] *= params["paO2_multiple"]
        paO2_results = integrate(**paO2_params)
        results["paO2_results"] = paO2_results
    log("Pa increase results done.")

    if params["velocity_multiple"] == 1.0:
        results["velocity_results"] = base_results
        vel_results = base_results
    else:
        vel_params = params.copy()
        vel_params["velocity"] *= params["velocity_multiple"]
        vel_results = integrate(**vel_params)
        results["velocity_results"] = vel_results
    log("Velocity increase results done.")

    results["ratio_pbO2_paO2"] = paO2_results["pbO2"] / base_results["pbO2"]
    results["paO2up_hf"] = paO2_results["hypoxic_fraction"]
    results["ratio_pbO2_vel"] = vel_results["pbO2"] / base_results["pbO2"]
    results["velup_hf"] = vel_results["hypoxic_fraction"]

    if params.get("no_search", False) == True:
        results["hb_search"] = base_results
        results["hb_params"] = params
        results["velocity_search"] = base_results
        results["velocity_params"] = params
        results["paO2_search"] = base_results
        results["paO2_params"] = params
        results["CMRO2_search"] = base_results
        results["CMRO2_params"] = params
    else:
        base_pbO2 = base_results["pbO2"]
        def is_pbO2_increased_ten_percent(search_results):
            if is_test:
                return True

            search_pbO2 = search_results["pbO2"]
            pbO2_increase = search_pbO2 / base_pbO2 - 1.0
            return pbO2_increase >= 0.1

        # Search for 10% increase in pbO2 via Hb
        def increase_hb(params):
            new_params = params.copy()
            new_params["Hb"] *= 1.01
            return new_params

        hb_search_params = increase_hb(params)
        hb_search_results, hb_final_params = search(hb_search_params, is_pbO2_increased_ten_percent, increase_hb)
        results["hb_search"] = hb_search_results
        results["hb_params"] = hb_final_params
        log("Hb search done.")

        # Search for 10% increase in pbO2 via velocity.
        def increase_velocity(params):
            new_params = params.copy()
            new_params["velocity"] *= 1.01
            return new_params

        vel_search_params = increase_velocity(params)
        vel_search_results, vel_final_params = search(vel_search_params, is_pbO2_increased_ten_percent, increase_velocity)
        results["velocity_search"] = vel_search_results
        results["velocity_params"] = vel_final_params
        log("Velocty search done.")

        # Search for 10% increase in pbO2 via paO2.
        def increase_paO2(params):
            new_params = params.copy()
            new_params["paO2"] *= 1.05
            return new_params

        paO2_search_params = increase_paO2(params)
        paO2_search_results, paO2_final_params = search(paO2_search_params, is_pbO2_increased_ten_percent, increase_paO2)
        results["paO2_search"] = paO2_search_results
        results["paO2_params"] = paO2_final_params
        log("PaO2 search done.")

        # Search for 10% increase in pbO2 via CMRO2.
        def decrease_CMRO2(params):
            new_params = params.copy()
            new_params["CMRO2"] *= 0.99
            return new_params

        cmro2_search_params = decrease_CMRO2(params)
        cmro2_search_results, cmro2_final_params = search(cmro2_search_params, is_pbO2_increased_ten_percent, decrease_CMRO2)
        results["CMRO2_search"] = cmro2_search_results
        results["CMRO2_params"] = cmro2_final_params
        log("CMRO2 search done.")

    return results


def evaluate_points(params_list, num_cores=None):
    # Attach a job number to each parameter set so that we can include it in any output.
    for i in range(len(params_list)):
        params_list[i]["job_number"] = i + 1

    if num_cores is None:
        num_cores = multiprocessing.cpu_count()

    print("Evaluating using {} cores.".format(num_cores))

    # This is necessary to make numpy work on OSX with joblib Parallel.
    os.environ["JOBLIB_START_METHOD"] = "forkserver"

    par = Parallel(n_jobs=num_cores)
    results_list = par(delayed(evaluate_point)(params) for params in params_list)

    return results_list
