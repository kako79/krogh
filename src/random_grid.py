import sys
from parameters import *
from evaluate import evaluate_points
from data import *
from units import get_units
import random


def get_random_params(param_ranges):
    params = {}
    for name, value_range in param_ranges.items():
        if len(value_range) == 1:
            params[name] = value_range[0]
        else:
            range_min, range_max = value_range.magnitude
            range_size = range_max = range_min
            value = range_min + range_size * random.random()
            params[name] = value * value_range.units
    return params


if __name__ == "__main__":
    num_points = 100
    if len(sys.argv) > 1:
        num_points = int(sys.argv[1])

    print("Using %s random points." % num_points)
    print("Results will be saved to random_grid_results.csv")
    units = get_units()

    param_ranges = {
        # CMRO2 source: http://www.frca.co.uk/article.aspx?articleid=100344
        "CMRO2": [2.5, 4.5] * units.mlO2 / units.hundred_g / units.min,

        # Length of the capillary.
        "z_capillary": [200] * units.um,

        # The experimentally obtained average values of blood flow velocities in cerebral capillaries indicate
        # that these velocities vary mainly from 0.5 to 1.5 mm/sec.
        "velocity": [0.5, 1.5] * units.mm / units.sec,

        # Diffusion coefficient (diffusivity) of oxygen in tissue.
        # http://rsif.royalsocietypublishing.org/content/royinterface/12/107/20150245.full.pdf
        # says this is 1.65e-5 cm^2/sec
        "D": [1e-6, 1e-4] * units.cm ** 2 / units.sec,

        # Radius of tissue cylinder.
        "r_Krogh": [20, 40] * units.um,

        # Radius of capillary.
        "r_capillary": [3] * units.um,

        # Initial pressure at the top of the cylinder.
        "paO2": [150, 250] * units.mmHg,

        # Haemoglobin concentration.
        "Hb": [10, 12] * units.g / units.dL,

        "r_steps": [100],
        "z_steps": [1000],

        # sigma source: http://www.frca.co.uk/article.aspx?articleid=100344
        "sigma": [0.0031] * units.mlO2 / units.dL / units.mmHg,

        "test": [False],
        "paO2_multiple": [1.0],
        "velocity_multiple": [1.0],
        "no_search": [True]
    }

    param_grid = [get_random_params(param_ranges) for i in range(num_points)]

    results = evaluate_points(param_grid)

    export_csv('random_grid_results.csv', results)
