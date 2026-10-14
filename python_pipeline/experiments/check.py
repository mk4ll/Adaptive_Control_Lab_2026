"""
Rig sanity check - run this first, every lab session (takes ~10 s).

Verifies: data arrives at the right rate, sensor noise at rest, and that a positive PWM
gives a positive velocity and an increasing angle (all adaptive laws assume sign(b) = +1).
"""
import numpy as np

from lab import config, signals
from lab.analysis import Report, plot_tracking
from lab.controllers import OpenLoop
from lab.runner import rest, run_experiment


def main(rig, sim, args):
    rep = Report("check", sim)
    checks = []

    rest(rig)
    idle = run_experiment(rig, OpenLoop(), signals.constant(0), 1.5, "idle")
    dts = np.diff(idle["t"])
    ts_ok = abs(np.mean(dts) - config.TS) < 0.1 * config.TS and np.max(dts) < 3 * config.TS
    checks.append(["sample period", f"mean {1e3 * np.mean(dts):.2f} ms, max {1e3 * np.max(dts):.2f} ms",
                   "PASS" if ts_ok else "FAIL - check TS in firmware and lab/config.py"])
    noise = float(np.std(idle["omega"]))
    checks.append(["velocity noise at rest", f"std {noise:.3f} rad/s", "info"])
    checks.append(["potentiometer", f"{np.mean(idle['pot']):.3f} (0..1)", "info - turn it and rerun to verify"])

    for sign in (+1, -1):
        rest(rig)
        u = sign * 0.5 * config.U_MAX
        log = run_experiment(rig, OpenLoop(), signals.step(u, t0=0.2), 2.5, f"spin_{'pos' if sign > 0 else 'neg'}")
        rep.save_log(log)
        rep.figure(plot_tracking(log, f"open loop u = {u:+.0f} PWM", show_ref=False), log.name)
        w_end = float(np.mean(log["omega"][-50:]))
        d_theta = float(log["theta"][-1] - log["theta"][0])
        moving = abs(w_end) > 5 * noise + 0.1
        good = moving and np.sign(w_end) == sign and np.sign(d_theta) == sign
        hint = "PASS" if good else (
            "FAIL - motor did not move (power supply? driver wiring? PIN_PWM?)" if not moving else
            "FAIL - wrong sign: set MOTOR_SIGN = -1 (or ENC_SIGN/TACHO_SIGN) in motor_io.ino and re-flash")
        checks.append([f"u = {u:+.0f} PWM", f"omega = {w_end:+.1f} rad/s, d(theta) = {d_theta:+.1f} rad", hint])
    rest(rig)

    rep.h2("Checks")
    rep.table(["check", "measured", "result"], checks)
    rep.save()
    print()
    for c in checks:
        print(f"  {c[0]:<24s} {c[1]:<45s} {c[2]}")
