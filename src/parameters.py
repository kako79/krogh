import itertools
import json
from units import get_units


def _strip_units(v):
    try:
        return v.magnitude
    except AttributeError:
        return v


def _add_units(param_values):
    units = get_units()
    params = param_values.copy()
    params["CMRO2"] *= (1.0 * units.mlO2 / units.hundred_g / units.min)
    params["z_capillary"] *= units.um
    params["velocity"] *= (1.0 * units.mm / units.sec)
    params["D"] *= (1.0 * units.cm ** 2 / units.sec)
    params["r_Krogh"] *= units.um
    params["r_capillary"] *= units.um
    params["paO2"] *= units.mmHg
    params["Hb"] *= (1.0 * units.g / units.dL)
    params["sigma"] *= (1.0 * units.mlO2 / units.hundred_ml / units.mmHg)
    return params


class Parameters:
    def __init__(self, param_dict=None):
        self.param_dict = param_dict

    def to_unitless(self):
        return {
            name: _strip_units(value) for name, value in self.param_dict.items()
        }

    @staticmethod
    def from_unitless(value_dict):
        return Parameters(_add_units(value_dict))

    def __getstate__(self):
        return self.to_unitless()

    def __setstate__(self, state):
        self.param_dict = _add_units(state)

    def copy(self):
        return Parameters(self.param_dict.copy())

    def items(self):
        return self.param_dict.items()

    def keys(self):
        return self.param_dict.keys()

    def get(self, key, default_value):
        return self.param_dict.get(key, default_value)

    def __getitem__(self, item):
        return self.param_dict[item]

    def __setitem__(self, key, value):
        return self.param_dict.__setitem__(key, value)

    def __str__(self):
        return str(self.param_dict)

    def __repr__(self):
        return repr(self.param_dict)


def create_param_grid(param_dict):
    """ Creates a parameter grid from a dictionary of parameter names to lists of values. """

    grid = []

    names = list(param_dict.keys())

    values_lists = [param_dict[name] for name in names]

    for values in itertools.product(*values_lists):
        grid_point = Parameters({name: value for name, value in zip(names, values)})
        grid.append(grid_point)

    return grid


def load_param_values(file_name):
    units = get_units()

    with open(file_name, 'r') as f:
        param_values = json.load(f)
        params = _add_units(param_values)
        return params


def print_param_values(params):
    for name, values in params.items():
        print("{}: {}".format(name, values))

