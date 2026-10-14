"""
The real-time loop shared by every experiment.

    log = run_experiment(rig, controller, reference, duration=30, name="mrac_step")

Each sample:  read sensors -> reference r(t) -> controller u -> send u -> record everything.
Safety checks run every sample; on any problem the motor is stopped and log.status says why.
"""
import csv
from collections import defaultdict

import numpy as np

from lab import config


class Log:
    """Recorded signals of one experiment: log["t"], log["omega"], log["u"], ..."""

    def __init__(self, name, data, status):
        self.name = name
        self.data = {k: np.asarray(v, dtype=float) for k, v in data.items()}
        self.status = status

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def keys(self):
        return self.data.keys()

    @property
    def ok(self):
        return self.status == "ok"

    def save_csv(self, outdir):
        path = outdir / f"{self.name}.csv"
        keys = list(self.data)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(keys)
            w.writerows(zip(*(self.data[k] for k in keys)))
        return path


def run_experiment(rig, controller, reference, duration, name, disturbance=None):
    """
    rig         Rig or SimRig
    controller  object with update(sample, r, dt) -> PWM  (see lab/controllers.py)
    reference   function r(t, sample)                     (see lab/signals.py)
    duration    seconds
    disturbance optional function d(t) added to the PWM (to test robustness)
    """
    data = defaultdict(list)
    status = "ok"
    t_prev = None
    stalled = 0.0           # time spent at (almost) full PWM without any measured motion
    rig.start()
    try:
        while True:
            s = rig.read()
            if s.t >= duration:
                break
            dt = config.TS if t_prev is None else float(np.clip(s.t - t_prev, 0.2 * config.TS, 5 * config.TS))
            t_prev = s.t

            r = reference(s.t, s)
            u = controller.update(s, r, dt)
            if disturbance is not None:
                u += disturbance(s.t)
            u = float(np.clip(u, -config.U_MAX, config.U_MAX)) if np.isfinite(u) else 0.0
            rig.write(u)

            data["t"].append(s.t)
            data["theta"].append(s.theta)
            data["omega"].append(s.omega)
            data["pot"].append(s.pot)
            data["r"].append(r)
            data["u"].append(u)
            for k, v in controller.log.items():
                data[k].append(v)

            if abs(s.omega) > config.OMEGA_LIMIT:
                status = f"ABORTED: |omega| > {config.OMEGA_LIMIT} rad/s at t={s.t:.1f}s"
                break
            if controller.diverged():
                status = f"ABORTED: adaptive parameters diverged at t={s.t:.1f}s"
                break
            stalled = stalled + dt if abs(u) >= 0.95 * config.U_MAX and abs(s.omega) < 0.05 else 0.0
            if stalled > config.STALL_TIME:
                status = (f"ABORTED: full PWM but no measured motion for {config.STALL_TIME:.0f}s at t={s.t:.1f}s "
                          f"- check motor power, driver and encoder wiring")
                break
    except KeyboardInterrupt:
        rig.stop()
        raise
    finally:
        rig.stop()

    late = getattr(rig, "late_samples", 0)
    n = max(len(data["t"]), 1)
    if late > 0.05 * n:
        print(f"[warn] {name}: the PC was late on {100 * late / n:.0f}% of samples (close other programs)")
    log = Log(name, data, status)
    print(f"[run] {name:<28s} {duration:6.1f}s  {status}")
    return log


def rest(rig, max_time=config.REST_TIME, threshold=0.05):
    """Motor off until it has (almost) stopped, so every experiment starts from rest."""
    rig.start()
    still = 0
    t = 0.0
    while t < max_time:
        s = rig.read()
        rig.write(0)
        t = s.t
        still = still + 1 if abs(s.omega) < threshold else 0
        if still * config.TS > 0.3:
            break
    rig.stop()
