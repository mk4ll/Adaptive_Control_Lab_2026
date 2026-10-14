"""
Lab I.6 - Robust adaptive ANGLE control (vector MRAC, state x = [theta, omega]).

  reference model:  theta_m'' + 2 zeta wn theta_m' + wn^2 theta_m = wn^2 r
  control:          u = k1*theta + k2*omega + d0 + l*r   (+ dc*tanh(omega/v0) if ANGLE_FRICTION_BASIS)
  adaptation:       dtheta/dt = -Gamma * w * (e^T P B0),   Am^T P + P Am = -I

All robust modifications are compared on angle steps and a slow sine; a long constant
step is run without modification and with projection.
Requires an encoder (with a tachogenerator the angle is integrated and drifts).
"""
from experiments.common import HEADERS, INTERPRETATION, Design, disturbance_from_args, run_adaptive
from lab import config, signals
from lab.analysis import Report
from lab.controllers import MRACVector, Robust


def main(rig, sim, args):
    rep = Report("lab6_angle", sim)
    d = Design(sim)
    ys = config.ANGLE_SCALE
    b_n = d.model.b * config.U_MAX / ys          # normalised input gain for x = [theta, omega] / ANGLE_SCALE
    wn, zeta = config.ANGLE_WN, config.ANGLE_ZETA
    ideal = {"k1": -wn**2 / b_n, "k2": (d.a - 2 * zeta * wn) / b_n, "l": wn**2 / b_n}
    # stick-slip: a moving shaft needs ~us PWM to keep going -> compensate that at the output
    u0 = 0.5 * (d.model.us_pos + d.model.us_neg) if config.ANGLE_DEADZONE_COMP else 0.0

    def controller(method):
        return MRACVector(wn, zeta, config.ANGLE_GAMMA, ys, friction=config.ANGLE_FRICTION_BASIS,
                          robust=Robust(method), u0=u0)

    rep.h2("Design")
    rep.text(f"Plant: theta' = omega, omega' = -{d.a:.3g} omega + {b_n:.3g} u_n   "
             f"(angles normalised by {ys:.3g} rad, u_n = u/{config.U_MAX}).\n\n"
             f"Reference model: wn = {wn:.3g} rad/s, zeta = {zeta:g} (settling ~ {4 / (zeta * wn):.2g} s).\n\n"
             f"Matching: A + B k*^T = Am ->  k1* = {ideal['k1']:.3g}, k2* = {ideal['k2']:.3g}, l* = {ideal['l']:.3g}. "
             f"gamma = {config.ANGLE_GAMMA}, initial estimates 0. Dead-zone inverse at the output: u0 = {u0:.1f} PWM "
             f"(= measured stop threshold; near standstill the ideal linear gains ask for only a few PWM, which "
             f"stick-slip friction would swallow). wn is limited by the motor speed and the dead time.")

    long_T = args.long if args.long else (60.0 if args.quick else 300.0)
    refs = {
        "steps": (signals.staircase(config.ANGLE_LEVELS, config.REF_HOLD), config.RUN_TIME),
        "sine": (signals.sine(config.ANGLE_SINE_AMP, config.SINE_PERIOD), config.RUN_TIME),
    }
    dist = disturbance_from_args(args)
    rows = []
    for method in config.ROBUST_METHODS:
        for name, (ref, T) in refs.items():
            ctrl = controller(method)
            row, _ = run_adaptive(rig, rep, ctrl, ref, T, f"angle_{method}_{name}", ideal, dist,
                                  y_key="theta", y_label="theta [rad]")
            rows.append(row)
    for method in ("none", "projection"):
        ctrl = controller(method)
        row, _ = run_adaptive(rig, rep, ctrl, signals.constant(config.ANGLE_LEVELS[0]), long_T,
                              f"angle_{method}_long_step", ideal, dist, y_key="theta", y_label="theta [rad]")
        rows.append(row)

    rep.h2("Results")
    rep.table(HEADERS, rows)
    rep.text(INTERPRETATION + " Here e is the filtered error e^T P B0 (normalised).")
    rep.text("\n**What to look for:** at standstill the motor dead zone causes a small steady angle error; "
             "without robustness the adaptive gains then keep integrating that error (drift, possible limit "
             "cycle). The deadzone modification stops this once the error is inside e0; projection bounds it.")
    rep.save()
