"""
Follow-up experiments suggested by the first results (run only what is missing, not whole labs):

    python run.py extras --part lab6rest    Lab I.6 runs not done yet + sigma-mod leaking toward nominal values
    python run.py extras --part mitfine     finer MIT stability map around gamma*r0^2 ~ 15
    python run.py extras --part lab5dz      Lab I.5 deadzone modification with e0 = 0.06 (above the noise)
    python run.py extras --part mraclong    plain scalar MRAC (Lab I.3) on a 30 min constant step
    python run.py extras --part mitlow      MIT stability map at gamma = 5-30 (repaired motor)
    python run.py extras --part all         lab6rest, mitfine, lab5dz, mraclong in this order

Each part writes its own report: results/<rig|sim>/extras_<part>_<time>/summary.md
"""
import numpy as np

from experiments.common import HEADERS, INTERPRETATION, Design, run_adaptive
from experiments.lab2_mit import stability_map
from experiments.lab5_robust import make_controller
from lab import config, signals
from lab.analysis import Report
from lab.controllers import MRACScalar, MRACVector, Robust

PARTS = ["lab6rest", "mitfine", "lab5dz", "mraclong"]          # "mitlow" is run on request

MIT_FINE_GAMMAS = [40.0, 50.0, 60.0, 70.0, 85.0]
MIT_FINE_AMPS = [0.4, 0.5, 0.6, 0.7]
MIT_LOW_GAMMAS = [5.0, 10.0, 15.0, 20.0, 30.0]     # repaired motor: boundary turned out below gamma = 40
DEADZONE_E0_WIDE = 0.06
MRAC_LONG_TIME = 1800.0


def lab6rest(rig, sim, args):
    rep = Report("extras_lab6rest", sim)
    d = Design(sim)
    ys = config.ANGLE_SCALE
    b_n = d.model.b * config.U_MAX / ys
    wn, zeta = config.ANGLE_WN, config.ANGLE_ZETA
    ideal = {"k1": -wn**2 / b_n, "k2": (d.a - 2 * zeta * wn) / b_n, "l": wn**2 / b_n}
    u0 = 0.5 * (d.model.us_pos + d.model.us_neg) if config.ANGLE_DEADZONE_COMP else 0.0
    nominal = [ideal["k1"], ideal["k2"], 0.0, ideal["l"]]          # [k1, k2, d0, l]
    long_T = args.long if args.long else (60.0 if args.quick else 300.0)

    rep.h2("Lab I.6: remaining runs and sigma-modification toward nominal values")
    rep.text(f"Same design as Lab I.6 (wn = {wn} rad/s, zeta = {zeta:g}, gamma = {config.ANGLE_GAMMA}, "
             f"dead-zone inverse {u0:.1f} PWM, model results/rig/model.json). Ideal: k1* = {ideal['k1']:.3g}, "
             f"k2* = {ideal['k2']:.3g}, l* = {ideal['l']:.3g}.\n\n"
             f"`sigma_nominal`: the estimates START at the nominal model values and sigma-modification leaks toward "
             f"them (theta0 = nominal) instead of toward 0, as in Lab I.5.")
    runs = [
        ("angle_projection_sine", "projection", None, signals.sine(config.ANGLE_SINE_AMP, config.SINE_PERIOD), config.RUN_TIME),
        ("angle_none_long_step", "none", None, signals.constant(config.ANGLE_LEVELS[0]), long_T),
        ("angle_projection_long_step", "projection", None, signals.constant(config.ANGLE_LEVELS[0]), long_T),
        ("angle_sigma_nominal_steps", "sigma", nominal, signals.staircase(config.ANGLE_LEVELS, config.REF_HOLD), config.RUN_TIME),
        ("angle_sigma_nominal_sine", "sigma", nominal, signals.sine(config.ANGLE_SINE_AMP, config.SINE_PERIOD), config.RUN_TIME),
    ]
    skip = {s.strip() for s in getattr(args, "skip", "").split(",") if s.strip()}
    if skip:
        rep.text(f"Skipped (already measured in an earlier attempt): {', '.join(sorted(skip))}.")
    rows = []
    try:
        for name, method, theta0, ref, T in runs:
            if name in skip:
                continue
            ctrl = MRACVector(wn, zeta, config.ANGLE_GAMMA, ys, theta0=theta0, friction=config.ANGLE_FRICTION_BASIS,
                              robust=Robust(method), u0=u0)
            row, log = run_adaptive(rig, rep, ctrl, ref, T, name, ideal, None, y_key="theta", y_label="theta [rad]")
            n = len(log["t"])
            row.append(f"{np.sqrt(np.mean(log['e_theta'][3 * n // 4:] ** 2)):.3f}")
            rows.append(row)
    finally:
        rep.table(HEADERS + ["RMS angle error last 25% [rad]"], rows)
        rep.text(INTERPRETATION + " Here e is the filtered error e^T P B0 (normalised).")
        rep.save()


def mitfine(rig, sim, args):
    rep = Report("extras_mitfine", sim)
    d = Design(sim)
    d.describe(rep)
    rep.h2("Finer MIT stability map around gamma*r0^2 ~ 15")
    rep.text(f"gamma in {MIT_FINE_GAMMAS}, r0 in {MIT_FINE_AMPS} (normalised), square wave period 8 s, 24 s per run; "
             f"same classification as Lab I.2 (runs abort once |theta| > {config.MIT_MAP_PARAM_LIMIT}).")
    stability_map(rig, rep, d, MIT_FINE_GAMMAS, MIT_FINE_AMPS)
    rep.save()


def mitlow(rig, sim, args):
    rep = Report("extras_mitlow", sim)
    d = Design(sim)
    d.describe(rep)
    rep.h2("MIT stability map at low gamma (repaired motor)")
    rep.text(f"On the repaired motor almost every run of the gamma = 40-85 sweep was unstable, so the boundary lies "
             f"lower. gamma in {MIT_LOW_GAMMAS}, r0 in {MIT_FINE_AMPS}; same classification as Lab I.2.")
    stability_map(rig, rep, d, MIT_LOW_GAMMAS, MIT_FINE_AMPS)
    rep.save()


def lab5dz(rig, sim, args):
    rep = Report("extras_lab5dz", sim)
    d = Design(sim)
    d.describe(rep)
    long_T = args.long if args.long else (60.0 if args.quick else 300.0)
    rep.h2(f"Lab I.5 deadzone modification with e0 = {DEADZONE_E0_WIDE} (was {config.DEADZONE_E0})")
    rep.text(f"In Lab I.5 the deadzone e0 = {config.DEADZONE_E0} was below the velocity noise (|e| ~ 0.03-0.05), so "
             f"adaptation never switched off and the ADI parameters kept drifting. Here e0 = {DEADZONE_E0_WIDE}; "
             f"everything else as in Lab I.5.")
    ideal = {"mrac": {"k": (d.a - d.am) / d.b_n, "l": d.bm / d.b_n}, "adi": {"a_hat": -d.a, "b_hat": d.b_n}}
    rows = []
    try:
        for kind in ("mrac", "adi"):
            for name, (ref, T) in d.references(long_T).items():
                ctrl = make_controller(kind, "deadzone", d)
                ctrl.robust.e0 = DEADZONE_E0_WIDE
                row, _ = run_adaptive(rig, rep, ctrl, ref, T, f"{kind}_deadzone_e0wide_{name}", ideal[kind])
                rows.append(row)
    finally:
        rep.table(HEADERS, rows)
        rep.text(INTERPRETATION)
        rep.save()


def mraclong(rig, sim, args):
    rep = Report("extras_mraclong", sim)
    d = Design(sim)
    d.describe(rep)
    T = getattr(args, "mrac_long", None) or (120.0 if args.quick else MRAC_LONG_TIME)
    ideal = {"k": (d.a - d.am) / d.b_n, "l": d.bm / d.b_n}
    rep.h2(f"Plain scalar MRAC (Lab I.3) on a {T / 60:.0f} min constant step")
    rep.text(f"gamma = {config.MRAC_GAMMA}, estimates start at 0, reference 0.5 omega_max. Question: does the linear "
             f"parameter drift seen in the 10 min run of Lab I.3 keep growing, saturate, or end in a burst?")
    rows = []
    try:
        ctrl = MRACScalar(d.am, d.bm, config.MRAC_GAMMA, d.ys)
        row, log = run_adaptive(rig, rep, ctrl, signals.constant(0.5 * d.ys), T, f"mrac_long_{T / 60:.0f}min", ideal)
        rows.append(row)
        t, k, l = log["t"], log["p_k"], log["p_l"]
        marks = [m for m in (60, 300, 600, 900, 1200, 1500, 1799) if m < t[-1]]
        drift = [[f"{m / 60:.0f} min", f"{np.interp(m, t, k):.3f}", f"{np.interp(m, t, l):.3f}",
                  f"{np.sqrt(np.mean(log['e_n'][(t > m - 30) & (t <= m)] ** 2)):.4f}"] for m in marks]
    finally:
        rep.table(HEADERS, rows)
        if rows:
            rep.table(["time", "k", "l", "RMS e (last 30 s)"], drift)
        rep.save()


def main(rig, sim, args):
    part = getattr(args, "part", None) or "all"
    for p in (PARTS if part == "all" else [part]):
        print(f"\n---------------- extras: {p} ----------------")
        globals()[p](rig, sim, args)
