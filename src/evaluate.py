import multiprocessing
import os
from solver import integrate
from joblib import Parallel, delayed
from search import search
from units import get_units


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

        target_pbO2 = base_pbO2 * 1.1

        # Search for 10% increase in pbO2 via Hb.
        log("Searching for pbO2 increase to %s via Hb." % target_pbO2)
        hb_search_range = {'Hb': (params['Hb'], params['Hb'] * 4)}
        hb_search_results, hb_search_params = search(params, 'pbO2', target_pbO2, hb_search_range, job_number=job_number)
        results["hb_search"] = hb_search_results
        results["hb_params"] = hb_search_params
        log("Hb search done, got pbO2 of %s using Hb of %s." % (hb_search_results['pbO2'], hb_search_params['paO2']))

        # Search for 10% increase in pbO2 via velocity.
        log("Searching for pbO2 increase to %s via velocity." % target_pbO2)
        vel_search_range = {'velocity': (params['velocity'], params['velocity'] * 2)}
        vel_search_results, vel_search_params = search(params, 'pbO2', target_pbO2, vel_search_range, job_number=job_number)
        results["velocity_search"] = vel_search_results
        results["velocity_params"] = vel_search_params
        log("Velocty search done, got pbO2 of %s using Hb of %s." % (vel_search_results['pbO2'], vel_search_results['paO2']))

        # Search for 10% increase in pbO2 via paO2.
        log("Searching for pbO2 increase to %s via paO2." % target_pbO2)
        paO2_search_range = {'paO2': (params['paO2'], params['paO2'] * 2)}
        paO2_search_results, paO2_search_params = search(params, 'pbO2', target_pbO2, paO2_search_range, job_number=job_number)
        results["paO2_search"] = paO2_search_results
        results["paO2_params"] = paO2_search_params
        log("PaO2 search done, got pbO2 of %s using Hb of %s." % (paO2_search_results['pbO2'], paO2_search_results['paO2']))

        # Search for 10% increase in pbO2 via CMRO2.
        log("Searching for pbO2 increase to %s via CMRO2." % target_pbO2)
        cmro2_search_range = {'CMRO2': (params['CMRO2'] * 0.5, params['CMRO2'])}
        cmro2_search_results, cmro2_search_params = search(params, 'pbO2', target_pbO2, cmro2_search_range, job_number=job_number)
        results["CMRO2_search"] = cmro2_search_results
        results["CMRO2_params"] = cmro2_search_params
        log("CMRO2 search done, got pbO2 of %s using Hb of %s." % (cmro2_search_results['pbO2'], cmro2_search_results['paO2']))

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

    # results_list = [evaluate_point(params) for params in params_list]

    par = Parallel(n_jobs=num_cores)
    results_list = par(delayed(evaluate_point)(params) for params in params_list)

    return results_list
