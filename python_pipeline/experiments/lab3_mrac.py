"""
Lab I.3 - Velocity control with scalar (direct, Lyapunov-based) MRAC.

  u = k*y + l*r,   dk/dt = -gamma*y*e,   dl/dt = -gamma*r*e        (sign(b) = +1)

Experiments: multi-level steps, slow sinusoid (PE check), and a long constant step
(LONG_RUN_TIME, default 10 min) to see whether the parameters drift / the loop goes unstable.
Parameters start at zero; the ideal values come from the Lab I.1 model.
"""
from experiments.common import HEADERS, INTERPRETATION, Design, disturbance_from_args, long_run_time, run_adaptive
from lab import config
from lab.analysis import Report
from lab.controllers import MRACScalar


def main(rig, sim, args):
    rep = Report("lab3_mrac", sim)
    d = Design(sim)
    rep.h2("Design")
    d.describe(rep)
    ideal = {"k": (d.a - d.am) / d.b_n, "l": d.bm / d.b_n}
    rep.text(f"Scalar MRAC, gamma = {config.MRAC_GAMMA}. Matching conditions: -a + b k* = -am, b l* = bm  ->  "
             f"k* = {ideal['k']:.3g}, l* = {ideal['l']:.3g}. Initial estimates: 0.")

    rep.h2("Experiments")
    rows = []
    for name, (ref, T) in d.references(long_run_time(args), fast_sine=True).items():
        ctrl = MRACScalar(d.am, d.bm, config.MRAC_GAMMA, d.ys)
        row, _ = run_adaptive(rig, rep, ctrl, ref, T, f"mrac_{name}", ideal, disturbance_from_args(args))
        rows.append(row)
    rep.table(HEADERS, rows)
    rep.text(INTERPRETATION)
    rep.text("\n**Expected:** with steps the regressor w = [y, r] becomes collinear (y -> r) so PE fails and "
             "(k, l) settle on *some* point of the line k*y + l*r = matching value, not necessarily (k*, l*). "
             "One sinusoid is sufficiently rich for 2 parameters, but the SLOW sine (period >> 1/am) keeps y ~ r, so "
             "PE is weak; the faster sine (FAST_SINE_PERIOD) separates y from r, the PE level rises and (k, l) should "
             "approach the ideal values (up to the first-order model error and the dead zone). "
             "On the long step, watch the drift column: no PE + noise can make the estimates wander.")
    rep.save()
