import pint


units = None


def get_units():
    global units

    if units is None:
        units = pint.UnitRegistry()
        units.define("hundred_ml = 100 * ml")
        units.define("hundred_g = 100 * g")
        units.define("mlO2 = [volumeO2]")
        pint._APP_REGISTRY = units

    return units
