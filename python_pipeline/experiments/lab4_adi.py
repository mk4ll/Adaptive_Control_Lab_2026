"""
Lab I.4 - Velocity control with scalar Adaptive Dynamic Inversion (ADI, indirect adaptive).

  plant estimate:  dy/dt = a_hat*y + b_hat*u
  control:         u = (dym/dt - ke*e - a_hat*y) / b_hat
  adaptation:      da_hat/dt = gamma*y*e,   db_hat/dt = gamma*u*e,   b_hat >= b_min

Experiments: multi-level steps, slow sinusoid (PE check), long constant step.
Estimates start at 50 % of the identified values to show adaptation.
"""
from experiments.common import HEADERS, INTERPRETATION, Design, disturbance_from_args, long_run_time, run_adaptive
from lab import config
from lab.analysis import Report
from lab.controllers import ADIScalar


def main(rig, sim, args):
    rep = Report("lab4_adi", sim)
    d = Design(sim)
    rep.h2("Design")
    d.describe(rep)
    ideal = {"a_hat": -d.a, "b_hat": d.b_n}
    theta0 = [0.5 * ideal["a_hat"], 0.5 * ideal["b_hat"]]
    b_min = 0.1 * d.b_n
    rep.text(f"ADI, gamma = {config.ADI_GAMMA}, ke = {config.ADI_KE}. Ideal: a_hat* = -a = {ideal['a_hat']:.3g}, "
             f"b_hat* = {ideal['b_hat']:.3g}. Initial: {theta0[0]:.3g}, {theta0[1]:.3g}; projection b_hat >= {b_min:.3g}.\n\n"
             f"Error dynamics de/dt = -ke*e + (estimation errors)*regressor, so the error decays at rate ke "
             f"independently of the reference model.")

    rep.h2("Experiments")
    rows = []
    for name, (ref, T) in d.references(long_run_time(args), fast_sine=True).items():
        ctrl = ADIScalar(d.am, d.bm, config.ADI_KE, config.ADI_GAMMA, d.ys, theta0, b_min)
        row, _ = run_adaptive(rig, rep, ctrl, ref, T, f"adi_{name}", ideal, disturbance_from_args(args))
        rows.append(row)
    rep.table(HEADERS, rows)
    rep.text(INTERPRETATION)
    rep.text("\n**Expected:** on constant references the regressor [y, u] is collinear -> no PE, estimates "
             "stop wherever a_hat*y + b_hat*u matches the true dynamics. The slow sine excites weakly, the fast "
             "sine clearly (compare the PE levels), so (a_hat, b_hat) should move toward (-a, b) mainly on sine_fast. Compare with Lab I.3: ADI identifies the plant "
             "(indirect), MRAC identifies the controller (direct).")
    rep.save()
