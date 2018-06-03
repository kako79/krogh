import datetime
import sys
from parameters import *
from evaluate import evaluate_points
from data import *
from units import get_units


if __name__ == '__main__':
    units = get_units()

    param_values = None
    base_file_name = "results " + datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')

    if len(sys.argv) > 1:
        param_values = Parameters(load_param_values(sys.argv[1]))
        base_file_name = "results " + sys.argv[1]

    if not param_values:
        param_values = Parameters({
            # CMRO2 source: http://www.frca.co.uk/article.aspx?articleid=100344
            "CMRO2": [3.0] * units.mlO2 / units.hundred_g / units.min,

            # Length of the capillary.
            "z_capillary": [200] * units.um,

            # The experimentally obtained average values of blood flow velocities in cerebral capillaries indicate
            # that these velocities vary mainly from 0.5 to 1.5 mm/sec.
            "velocity": [1.0] * units.mm / units.sec,

            # Diffusion coefficient (diffusivity) of oxygen in tissue.
            # http://rsif.royalsocietypublishing.org/content/royinterface/12/107/20150245.full.pdf
            # says this is 1.65e-5 cm^2/sec
            "D": [1.65e-5] * units.cm ** 2 / units.sec,

            # Radius of tissue cylinder.
            "r_Krogh": [20] * units.um,

            # Radius of capillary.
            "r_capillary": [3] * units.um,

            # Initial pressure at the top of the cylinder.
            "paO2": [200] * units.mmHg,

            # Haemoglobin concentration.
            "Hb": [10] * units.g / units.dL,

            "r_steps": [100],
            "z_steps": [1000],

            "sigma": [3.1e-5] * units.mlO2 / units.hundred_ml / units.mmHg,

            "test": [True],

            "paO2_multiple": [1.1],

            "velocity_multiple": [1.1],
        })

    print("Parameter values:")
    print_param_values(param_values)

    csv_results_file_name = base_file_name + ".csv"
    raw_results_file_name = base_file_name + ".pickle"

    print()
    print("Results will be in '%s'" % csv_results_file_name)
    print()

    param_grid = create_param_grid(param_values)
    results = evaluate_points(param_grid)

    export_csv(csv_results_file_name, results)
    save_results(raw_results_file_name, results)
