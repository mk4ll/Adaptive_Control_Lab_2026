"""
Lab I.5 - Robust adaptive velocity control (scalar MRAC and ADI).

Uncertainty model (linearly parameterised):  offset + Coulomb friction  ->  basis [1, tanh(y/v0)]
  MRAC:  u = k*y + d0 + dc*tanh(y/v0) + l*r
  ADI:   dy/dt = a_hat*y + d0_hat + dc_hat*tanh(y/v0) + b_hat*u

Every robust modification (none, deadzone, sigma, e-mod, projection) is run for both
controllers on steps, slow sine and a long constant step. Use --disturbance <PWM> to add
a bounded random input disturbance that makes parameter drift visible faster.
"""
import numpy as np

from experiments.common import HEADERS, INTERPRETATION, Design, disturbance_from_args, run_adaptive
from lab import config
from lab.analysis import COLORS, Report, plt
from lab.controllers import ADIScalar, MRACScalar, Robust


def make_controller(kind, method, d):
    """
    Estimates start at (and sigma/e-mod leak toward) the nominal Lab I.1 model values (ADI: 50 % of them,
    as in Lab I.4), including the Coulomb friction measured there (stop threshold us, normalised by U_MAX).
    Offset/friction terms adapt FRICTION_GAMMA_SCALE times slower than the linear terms.
    """
    robust = Robust(method)
    friction = 0.5 * (d.model.us_pos + d.model.us_neg) / config.U_MAX     # Coulomb friction [normalised PWM]
    s = config.FRICTION_GAMMA_SCALE
    if kind == "mrac":
        theta0 = [(d.a - d.am) / d.b_n, 0.0, friction, d.bm / d.b_n]       # u = k y + d0 + dc tanh(y/v0) + l r
        gamma = config.MRAC_GAMMA * np.array([1, s, s, 1])
        return MRACScalar(d.am, d.bm, gamma, d.ys, theta0, extended=True, robust=robust)
    # same 50 % start for a_hat, b_hat as Lab I.4 (fair comparison); friction torque opposes motion
    theta0 = [-0.5 * d.a, 0.0, -0.5 * d.b_n * friction, 0.5 * d.b_n]
    gamma = config.ADI_GAMMA * np.array([1, s, s, 1])
    return ADIScalar(d.am, d.bm, config.ADI_KE, gamma, d.ys, theta0, 0.1 * d.b_n,
                     extended=True, robust=robust)


def main(rig, sim, args):
    rep = Report("lab5_robust", sim)
    d = Design(sim)
    rep.h2("Design")
    d.describe(rep)
    rep.text(f"Robust settings: deadzone e0 = {config.DEADZONE_E0}, sigma = {config.SIGMA}, "
             f"projection bound = {config.PROJ_BOUND}, friction basis v0 = {config.FRICTION_V0}. "
             f"Disturbance: {getattr(args, 'disturbance', 0) or config.DISTURBANCE_PWM} PWM.\n\n"
             f"Initial estimates = nominal values from the Lab I.1 model (ADI: 50 %, as in Lab I.4), with the Coulomb "
             f"friction term seeded from the measured stop threshold; sigma and e-mod leak toward them (leaking toward 0, "
             f"the textbook form, biases the feedforward gain l -> 0). Offset/friction terms adapt "
             f"{config.FRICTION_GAMMA_SCALE}x slower. Friction basis driven by "
             f"{'the reference-model velocity ym (non-zero at standstill, helps break stiction)' if config.FRICTION_FROM_REFERENCE else 'the measured velocity y'}.")
    long_T = args.long if args.long else (60.0 if args.quick else 300.0)
    dist = disturbance_from_args(args)
    ideal = {"mrac": {"k": (d.a - d.am) / d.b_n, "l": d.bm / d.b_n},
             "adi": {"a_hat": -d.a, "b_hat": d.b_n}}

    for kind in ("mrac", "adi"):
        rep.h2(f"{kind.upper()} with robust modifications")
        rows, long_logs = [], {}
        for method in config.ROBUST_METHODS:
            for name, (ref, T) in d.references(long_T).items():
                ctrl = make_controller(kind, method, d)
                row, log = run_adaptive(rig, rep, ctrl, ref, T, f"{kind}_{method}_{name}", ideal[kind], dist)
                rows.append(row)
                if name == "long_step":
                    long_logs[method] = log
        rep.table(HEADERS, rows)

        # comparison of the long runs: parameter norm over time per method
        fig, axes = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
        for i, (method, log) in enumerate(long_logs.items()):
            P = np.column_stack([log[k] for k in log.keys() if k.startswith("p_")])
            axes[0].plot(log["t"], np.linalg.norm(P, axis=1), color=COLORS[i % len(COLORS)], label=method)
            axes[1].plot(log["t"], np.abs(log["e_n"]), color=COLORS[i % len(COLORS)], lw=1.0, label=method)
        axes[0].set_ylabel("||theta||"), axes[0].legend(ncol=5)
        axes[0].set_title(f"{kind.upper()} long constant step: parameter norm and tracking error")
        axes[1].set_ylabel("|e| (norm)"), axes[1].set_yscale("log"), axes[1].set_xlabel("time [s]")
        rep.figure(fig, f"{kind}_long_comparison")
    rep.text(INTERPRETATION)
    rep.text("\n**What to look for:** with *none*, ||theta|| may keep growing on the long step (drift: "
             "no PE + noise/disturbance). *sigma* and *e-mod* bound the parameters at the cost of a small "
             "steady bias, *deadzone* freezes adaptation once |e| < e0, *projection* keeps them in the box "
             "without biasing them inside it.")
    rep.save()
