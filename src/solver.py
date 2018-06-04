import numpy as np
from scipy.integrate import solve_bvp
from units import get_units


units = get_units()

def blood_o2_saturation(partial_pressure):
    a1 = -8.5322289e3
    a2 = 2.121301e3
    a3 = -6.7073989e1
    a4 = 9.3596087e5
    a5 = -3.1346258e4
    a6 = 2.3961674e3
    a7 = -6.7104406e1
    pp = partial_pressure.magnitude
    sats_percent = 100 * (a1 * pp + a2 * pp ** 2 + a3 * pp ** 3 + pp ** 4) / (
                a4 + a5 * pp + a6 * pp ** 2 + a7 * pp ** 3 + pp ** 4)

    # This is just a percentage and therefore unitless.
    return sats_percent


def get_blood_o2_concentration(partial_pressure, Hb):
    # The theoretical maximum oxygen carrying capacity is 1.39 ml O2/g Hb, but direct measurement gives a
    # capacity of 1.34 ml O2/g Hb. 1.34 is also known as Hufner's constant.
    # The oxygen content of blood is the volume of oxygen carried in each 100ml blood.
    # It is calculated by: (O2 carried by Hb) + (O2 in solution) = (1.34 x Hb x SpO2 x 0.01) + (0.023 x PaO2)
    # Where:
    # SO2 = percentage saturation of Hb with oxygen
    # Hb = haemoglobin concentration in grams per 100 ml blood
    # PO2 = partial pressure of oxygen (0.0225 = ml of O2 dissolved per 100 ml plasma per kPa, or 0.003 ml per mmHg)
    assert partial_pressure.units == units.mmHg
    assert Hb.units == units.g / units.dL

    # Multiply by 0.01 to convert sats from percentage to fraction.
    sats_fraction = 0.01 * blood_o2_saturation(partial_pressure)
    pressure_factor = 0.003 * units.mlO2 / units.dL / units.mmHg
    o2_capacity = 1.34 * units.mlO2 / units.g

    # Final units are mlO2 / dL
    Hb_concentration = o2_capacity * Hb * sats_fraction + pressure_factor * partial_pressure
    return Hb_concentration


class O2ConcentrationTable:
    _pressure_step = 0.01

    def __init__(self, Hb):
        pressure_values = np.arange(0, 2000, self._pressure_step) * units.mmHg
        self.table = get_blood_o2_concentration(pressure_values, Hb).magnitude

    def get_blood_o2_pressure(self, concentration):
        assert concentration.units == units.mlO2 / units.dL, ("concentration units are wrong: %s" % concentration.units)
        concentration_value = concentration.magnitude
        diffs = (self.table - concentration_value) ** 2
        min_index = np.argmin(diffs)
        pp = min_index * self._pressure_step * units.mmHg
        return pp


def integrate(CMRO2, z_capillary, velocity, D, r_Krogh, r_capillary, paO2, Hb, sigma, r_steps, z_steps,
              verbose=False, report_interval=10, test=False, job_number=0, **kwargs):

    def log(s):
        print("[{}] {}".format(job_number, s))


    if test:
        return {
            "paO2": paO2,
            "pbO2": 1,
            "av_o2_difference": 1,
            "jugular_venous_o2_sat": 1,
            "o2_extraction_fraction": 1,
            "pavO2": 1,
            "hypoxic_fraction": 1,
            "p": np.zeros(shape=(z_steps, r_steps))
        }

    # We need to convert between ml and cm^3 in a few places below and pint doesn't support that.
    ml_to_cm3 = units.ml / (units.cm ** 3)

    def gamma(CMRO2max, partial_pressure):
        if partial_pressure > 0.4:
            return CMRO2max.magnitude
        else:
            return 0.0  # * units.mlO2 / units.hundred_g / units.min

    sigma_ode = sigma.to(units.mlO2 / units.ml / units.mmHg) * ml_to_cm3
    gamma_factor = (CMRO2 / CMRO2.magnitude).to(units.mlO2 / units.g / units.sec).magnitude
    kappa_factor = 1e-8

    def odewboundary(D, CMRO2max, x, y):
        g = gamma(CMRO2max, y[0]) * gamma_factor
        s = sigma_ode
        kappa = kappa_factor * g / (D * s)
        return np.array([y[1], kappa.magnitude - y[1] / x])

    def boundarycd(paO2, ya, yb):
        return np.array([ya[0] - paO2.magnitude, yb[1]])

    CMRO2max = CMRO2
    r_steps = np.round(r_steps * r_Krogh / (20 * units.um)).astype(int)
    z_steps = np.round(z_steps * r_Krogh / (20 * units.um)).astype(int)

    dr = (r_Krogh - r_capillary) / r_steps
    dz = z_capillary / z_steps

    p = np.zeros(shape=(z_steps, r_steps)) * units.mmHg
    p[0, 0] = paO2

    # We need to convert between ml and cm^3 in a few places below and pint doesn't support that.
    ml_to_cm3 = units.ml / (units.cm ** 3)

    initial_grid_size = 10

    # ODE function specific to the parameters that were passed in.
    def ode(x, y):
        # x is the array of mesh points.
        # y is the array of values at each mesh point
        # y[:, i] is the value of the function at point x[i].
        m = len(x)
        dy = np.array([odewboundary(D, CMRO2max, x[i], y[:, i]) for i in range(m)]).T
        return dy

    table = O2ConcentrationTable(Hb)

    for z in range(z_steps):
        if z % report_interval == 0:
            log("step %s, pa: %s" % (z, p[z, 0]))

        z_paO2 = p[z, 0]

        def bc(ya, yb):
            return boundarycd(z_paO2, ya, yb)

        # x is the initial grid.
        x = np.linspace(r_capillary, r_Krogh, initial_grid_size) * units.um

        # y is a guess of the function value at the initial grid points.
        # Columns of y correspond to grid points, so it should have shape (2, initial_grid_size)
        # Start with a guess of an exponential decay to give the solver an easier time.
        y0 = z_paO2.magnitude / np.e * np.exp(1 / (x.magnitude - x[0].magnitude + 1))
        # The derivative of an exponential decay is equal to the function value.
        y1 = y0
        y = np.array([y0, y1])
        solution = solve_bvp(ode, bc, x, y, tol=1e-7, max_nodes=2000)

        r_values = np.linspace(r_capillary, r_Krogh, r_steps)
        p_sol, _ = solution.sol(r_values)

        min_pressure = np.min(p_sol)
        if np.min(p_sol) < 0:
            log("Warning: pressures are negative.  Lowest pressure = {}".format(min_pressure))

        if not solution.success:
            log("Solver warning: %s" % solution.message)

        p_sol = np.maximum(0, p_sol)
        p[z, :] = p_sol * units.mmHg

        pressure_gradient = (p[z, 0] - p[z, 1]) / (dr.to(units.cm))

        if verbose:
            log("p0: %s, p1: %s, pressure_gradient: %s" % (p[z, 0], p[z, 1], pressure_gradient))

        density_gradient = (sigma * pressure_gradient).to(units.mlO2 / units.ml / units.cm)

        if verbose:
            log("density_gradient: %s" % density_gradient)

        capillary_surface_area = (2 * np.pi * r_capillary * dz).to(units.cm ** 2)

        o2_extracted_per_second = D * capillary_surface_area * density_gradient * ml_to_cm3

        if verbose:
            log("o2_extracted_per_second: %s" % o2_extracted_per_second)

        o2_extracted = o2_extracted_per_second * dz.to(units.cm) / velocity

        if verbose:
            log("o2_extracted: %s" % o2_extracted)

        blood_o2_concentration = get_blood_o2_concentration(p[z, 0], Hb).to(units.mlO2 / units.ml)
        blood_o2_content = blood_o2_concentration * np.pi * dz.to(units.cm) * r_capillary.to(units.cm) ** 2 * ml_to_cm3

        if verbose:
            log("blood_o2_content: %s" % blood_o2_content)

        o2_concentration_remaining = ((blood_o2_content - o2_extracted)
                                      / (np.pi * dz.to(units.cm) * r_capillary.to(units.cm) ** 2)
                                      / ml_to_cm3).to(units.mlO2 / units.dL)

        if z < (z_steps - 1):
            p_next = table.get_blood_o2_pressure(o2_concentration_remaining)
            p[z + 1, 0] = p_next

    inner_radii = np.arange(0, r_steps) * dr + r_capillary
    outer_radii = np.arange(1, r_steps + 1) * dr + r_capillary
    element_volumes = (np.pi * ((outer_radii ** 2) - (inner_radii ** 2)) * dz)
    volume_weighted_pbO2 = np.multiply(p, element_volumes)
    total_weighted_pbO2 = np.sum(volume_weighted_pbO2)
    total_volume = z_steps * np.sum(element_volumes)
    average_pbO2 = total_weighted_pbO2 / total_volume

    # A-V oxygen pressure difference.
    pavO2 = p[0, 0] - p[-1, 0]

    # A-V oxygen concentration difference.
    av_o2_difference = get_blood_o2_concentration(p[0, 0], Hb) - get_blood_o2_concentration(p[-1, 0], Hb)

    # Fraction of oxygen concentration extracted.
    o2_extraction_fraction = av_o2_difference / get_blood_o2_concentration(p[0, 0], Hb)

    # Calculates jugular venous o2 saturation percentage.
    jugular_venous_o2_sat = blood_o2_saturation(p[-1, 0])

    hypoxic_volume = np.sum((p.magnitude <= 10.0) * element_volumes)
    hypoxic_fraction = hypoxic_volume / total_volume

    return {
        "paO2": paO2,
        "pbO2": average_pbO2,
        "av_o2_difference": av_o2_difference,
        "jugular_venous_o2_sat": jugular_venous_o2_sat,
        "o2_extraction_fraction": o2_extraction_fraction,
        "pavO2": pavO2,
        "hypoxic_fraction": hypoxic_fraction,
        "p": p
    }
