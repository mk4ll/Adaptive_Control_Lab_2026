"""
Lab I.1 (part D) - effect of the load potentiometer on the second motor, one position per call:

    python run.py load --position middle
    python run.py load --position minimum
    python run.py load --position maximum

Each call runs steps of +/- LOAD_STEP_PWM (twice each, the breakaway is random) and saves the logs
in results/<rig|sim>/load_test/. The report load_test/summary.md is rebuilt from all positions measured so far.
"""
import json

import numpy as np

from experiments.lab1_identification import T0, analyse_step
from lab import config, signals
from lab.analysis import COLORS, Report, plt
from lab.controllers import OpenLoop
from lab.runner import Log, rest, run_experiment

LOAD_STEP_PWM = 180
REPEATS = 2
ORDER = ["minimum", "end_A", "middle", "end_B", "maximum"]


def main(rig, sim, args):
    pos = args.position
    if pos is None:
        raise SystemExit("Give the potentiometer position: --position minimum|middle|maximum")
    outdir = config.RESULTS_DIR / ("sim" if sim else "rig") / "load_test"
    outdir.mkdir(parents=True, exist_ok=True)
    if hasattr(rig, "set_load"):
        rig.set_load(ORDER.index(pos) / 2 if pos in ORDER else 0.5)

    results = []
    for sign in (+1, -1):
        for k in range(REPEATS):
            u = sign * LOAD_STEP_PWM
            rest(rig)
            log = run_experiment(rig, OpenLoop(), signals.step(u, t0=T0), T0 + config.ID_STEP_HOLD,
                                 f"load_{pos}_u{u:+d}_{k + 1}")
            log.save_csv(outdir)
            r = analyse_step(log, u)
            r["moved"] = bool(abs(r["omega_ss"]) > 0.3)
            results.append(r)
    rest(rig)
    (outdir / f"{pos}.json").write_text(json.dumps(results, indent=2, default=lambda o: o.item()))
    build_report(outdir)


def build_report(outdir):
    rep = Report.__new__(Report)                 # reuse Report but write into the fixed load_test folder
    rep.outdir, rep.lines = outdir, ["# Lab I.1 D - load potentiometer on the second motor\n"]
    positions = [p for p in ORDER if (outdir / f"{p}.json").exists()]
    positions += sorted(f.stem for f in outdir.glob("*.json") if f.stem not in ORDER)

    rows = []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for i, pos in enumerate(positions):
        res = json.loads((outdir / f"{pos}.json").read_text())
        for sign, ax in ((+1, axes[0]), (-1, axes[1])):
            moved = [r for r in res if np.sign(r["u"]) == sign and r["moved"]]
            if moved:
                w = float(np.mean([r["omega_ss"] for r in moved]))
                tau = float(np.mean([r["tau"] for r in moved]))
                Td = float(np.mean([r["Td"] for r in moved]))
                rows.append([pos, int(sign * LOAD_STEP_PWM), w, w / (sign * LOAD_STEP_PWM), tau, 1 / tau, Td,
                             f"{len(moved)}/{REPEATS}"])
            else:
                rows.append([pos, int(sign * LOAD_STEP_PWM), "did not move", "", "", "", "", f"0/{REPEATS}"])
            csv = outdir / f"load_{pos}_u{sign * LOAD_STEP_PWM:+d}_1.csv"
            if csv.exists():
                d = np.genfromtxt(csv, delimiter=",", names=True)
                ax.plot(d["t"] - T0, d["omega"], color=COLORS[i % len(COLORS)], label=pos)
    for ax, name in zip(axes, ("u = +", "u = -")):
        ax.set_title(f"Step {name}{LOAD_STEP_PWM} PWM"), ax.set_xlabel("time after step [s]"), ax.legend(title="load")
    axes[0].set_ylabel("omega [rad/s]")
    rep.table(["load", "u [PWM]", "omega_ss [rad/s]", "gain omega_ss/u", "tau [s]", "a = 1/tau", "Td [s]", "moved"],
              rows)
    rep.figure(fig, "load_variation")
    rep.text("More electrical load on the generator (lower resistance) = more braking torque: expect lower "
             "steady-state speed (smaller gain) and a faster pole a. The dead time / breakaway may also change.")

    # is the effect of the potentiometer larger than the repeat-to-repeat scatter?
    rep.h2("Significance check")
    lines = []
    for sign in (+1, -1):
        means, spreads = {}, []
        for pos in positions:
            w = [r["omega_ss"] for r in json.loads((outdir / f"{pos}.json").read_text())
                 if np.sign(r["u"]) == sign and r["moved"]]
            if len(w) >= 2:
                means[pos] = float(np.mean(w))
                spreads.append(float(np.std(w, ddof=1)))
        if len(means) >= 2 and spreads:
            between = max(means.values()) - min(means.values())
            within = float(np.mean(spreads))
            # significant = clearly above the repeat scatter AND above slow drifts (warm-up ~ 2 %)
            relative = between / max(abs(m) for m in means.values())
            significant = between > 3 * within and relative > 0.05
            verdict = ("SIGNIFICANT - the load changes the speed" if significant
                       else "NOT significant - no load effect beyond scatter / warm-up drift (< 5 %)")
            slowest = min(means, key=lambda p: abs(means[p]))
            lines.append(f"- u = {sign * LOAD_STEP_PWM:+d}: spread between positions {between:.3f} rad/s, "
                         f"({100 * relative:.0f} %), repeat scatter {within:.3f} rad/s -> **{verdict}**"
                         + (f" (most braking = `{slowest}`)" if significant else ""))
    rep.text("\n".join(lines) + "\n\nIf not significant: check that the second motor's terminals are actually "
             "connected through the potentiometer (an open circuit gives no braking) and that its resistance range "
             "is low enough compared with the motor's armature resistance to draw a noticeable current.")
    rep.save()
