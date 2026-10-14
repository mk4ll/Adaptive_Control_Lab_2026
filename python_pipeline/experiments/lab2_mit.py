"""
Lab I.2 - Adaptive velocity control with the MIT rule.

  1. MIT controller (u = th1*r - th2*y) on step and sinusoidal references
  2. Stability map: sweep adaptation gain gamma x reference amplitude r0 and classify
     each run as stable / unstable automatically.

Why the map: for the ideal first-order plant the linearised MIT loop is second order and
always stable, but every real loop has unmodelled dynamics (velocity filter, PWM driver,
sampling + serial delay, motor inductance). With one extra pole the linearised loop
becomes third order and is stable only while  gamma * r0^2  stays below a bound
(the MIT rule scales with the SQUARE of the signal level). The map tests exactly this.
"""
import numpy as np

from experiments.common import HEADERS, INTERPRETATION, Design, run_adaptive
from lab import config, signals
from lab.analysis import COLORS, Report, plt, tracking_metrics
from lab.controllers import MITController
from lab.runner import rest, run_experiment


def main(rig, sim, args):
    rep = Report("lab2_mit", sim)
    d = Design(sim)
    rep.h2("Design")
    d.describe(rep)
    ideal = {"th1": d.bm / d.b_n, "th2": (d.am - d.a) / d.b_n}
    rep.text(f"MIT rule, gamma = {config.MIT_GAMMA}. Ideal parameters: th1* = bm/b = {ideal['th1']:.3g}, "
             f"th2* = (am - a)/b = {ideal['th2']:.3g}.")

    rep.h2("1. Tracking with the MIT rule")
    rows = []
    for name, (ref, T) in d.references(fast_sine=True).items():
        ctrl = MITController(d.am, d.bm, config.MIT_GAMMA, d.ys)
        row, _ = run_adaptive(rig, rep, ctrl, ref, T, f"mit_{name}", ideal)
        rows.append(row)
    rep.table(HEADERS, rows)
    rep.text(INTERPRETATION)

    if args.quick:
        rep.save()
        return

    rep.h2("2. Stability map: gamma x reference amplitude")
    T = 24.0
    results = []
    for gamma in config.MIT_GAMMA_SWEEP:
        for amp in config.MIT_AMP_SWEEP:
            rest(rig)
            ctrl = MITController(d.am, d.bm, gamma, d.ys)
            ctrl.param_limit = config.MIT_MAP_PARAM_LIMIT     # stop early once it clearly diverges
            name = f"mit_map_g{gamma:g}_r{amp:g}"
            log = run_experiment(rig, ctrl, signals.square(amp * d.ys, 8.0), T, name)
            rep.save_log(log)
            m = tracking_metrics(log)
            # unstable = aborted, error growing over the run, or error as large as the reference itself
            e = log["e_n"]
            n = len(e)
            growing = m["rms_e_end"] > 1.5 * np.sqrt(np.mean(e[n // 4: n // 2] ** 2)) + 0.02
            stable = log.ok and not growing and m["rms_e_end"] < 0.5 * amp
            # stuck = shaft hardly moved (stiction never broken): poor tracking, but not an instability
            y_end = np.abs(log["omega"][3 * n // 4:]) / d.ys
            stuck = log.ok and not stable and np.max(y_end) < 0.3 * amp
            verdict = "stable" if stable else ("STUCK (stiction)" if stuck else "UNSTABLE")
            results.append([gamma, amp, gamma * amp**2, m["rms_e_end"], verdict, log.status])

    rep.table(["gamma", "r0 (norm)", "gamma*r0^2", "RMS e last 25%", "verdict", "status"], results)
    stab = [r[2] for r in results if r[4] == "stable"]
    unst = [r[2] for r in results if r[4] == "UNSTABLE"]
    if not unst:
        rep.text("No instability in the tested range - extend MIT_GAMMA_SWEEP in lab/config.py.")
    elif not stab or max(stab) < min(unst):
        rep.text(f"**Observed condition:** every stable run has gamma*r0^2 <= {max(stab, default=0):.3g} and every "
                 f"unstable run gamma*r0^2 >= {min(unst):.3g}: a single threshold on gamma*r0^2 separates them, "
                 f"confirming the MIT-rule condition gamma*r0^2 < c with c in that interval.")
    else:
        rep.text("**Observed:** stable and unstable runs overlap in gamma*r0^2, so gamma*r0^2 alone does not explain "
                 "the boundary here - inspect the plots (dead zone at small r0? saturation at large r0?).")

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for r in results:
        if r[4].startswith("STUCK"):
            ax.plot(r[1], r[0], "s", ms=9, color="#8a8a85")
            continue
        ok = r[4] == "stable"
        ax.plot(r[1], r[0], "o" if ok else "X", ms=10, color=COLORS[2] if ok else COLORS[1])
    amps = np.linspace(min(config.MIT_AMP_SWEEP), max(config.MIT_AMP_SWEEP), 50)
    if stab and unst and max(stab) < min(unst):
        c = np.sqrt(max(stab) * min(unst))        # boundary estimate between the two groups
        ax.plot(amps, c / amps**2, color="#8a8a85", ls="--", lw=1.2, label=f"gamma*r0^2 = {c:.3g}")
    ax.plot([], [], "o", color=COLORS[2], label="stable"), ax.plot([], [], "X", color=COLORS[1], label="unstable")
    ax.plot([], [], "s", color="#8a8a85", label="stuck (stiction)")
    ax.legend()
    ax.set_yscale("log"), ax.set_xlabel("reference amplitude r0 (normalised)"), ax.set_ylabel("gamma")
    ax.set_title("MIT rule stability map")
    rep.figure(fig, "mit_stability_map")
    rep.save()
