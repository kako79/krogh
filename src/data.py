import pickle
import csv


def save_results(file_name, results):
    with open(file_name, 'wb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


def load_results(file_name):
    with open(file_name, 'rb') as f:
        return pickle.load(f)


def export_csv(file_name, results):
    fields = {
        "CMRO2": "params.CMRO2",
        "z_cap": "params.z_capillary",
        "vel": "params.velocity",
        "D": "params.D",
        "r_Krogh": "params.r_Krogh",
        "r_cap": "params.r_capillary",
        "paO2": "params.paO2",
        "Hb": "params.Hb",
        "pbO2": "base_results.pbO2",
        "jvO2_sat": "base_results.jugular_venous_o2_sat",
        "hf": "base_results.hypoxic_fraction",
        "ratio_pbO2_paO2": "ratio_pbO2_paO2",
        "paO2up_hf": "paO2up_hf",
        "ratio_pbO2_vel": "ratio_pbO2_vel",
        "velup_hf": "velup_hf",
        "tenpercentvel": "velocity_params.velocity",
        "tenpercentvelpbO2": "velocity_search.pbO2",
        "tenpercentvelhf": "velocity_search.hypoxic_fraction",
        "tenpercentPa": "paO2_params.paO2",
        "tenpercentPapbO2": "paO2_search.pbO2",
        "tenpercentPahf": "paO2_search.hypoxic_fraction",
        "tenpercentCMRO2": "CMRO2_params.CMRO2",
        "tenpercentCMRO2pbO2": "CMRO2_search.pbO2",
        "tenpercentCMRO2hf": "CMRO2_search.hypoxic_fraction",
        "tenpercentHb": "hb_params.Hb",
        "tenpercentHbpbO2": "hb_search.pbO2",
        "tenpercentHbhf": "hb_search.hypoxic_fraction",
    }

    def get_field(d, field):
        sep_index = field.find(".")
        if sep_index < 0:
            return d[field]
        else:
            sub_d = d[field[0:sep_index]]
            return get_field(sub_d, field[sep_index+1:])

    def strip_units(v):
        try:
            return v.magnitude
        except AttributeError:
            return v

    rows = [
        [strip_units(get_field(result, field)) for name, field in fields.items()]
        for result in results
    ]

    with open(file_name, 'w') as f:
        w = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        headers = list(fields.keys())
        w.writerow(headers)

        for row in rows:
            w.writerow(row)
