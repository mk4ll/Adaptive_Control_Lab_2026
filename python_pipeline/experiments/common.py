"""
Shared pieces of the adaptive-control labs (I.2 - I.6):
reference model design from the identified model, standard reference signals,
and a run -> save -> plot -> table-row helper.
"""
from lab import config, signals
from lab.analysis import ADAPTIVE_HEADERS, adaptive_summary_row, plot_tracking
from lab.model import load_model
from lab.runner import rest, run_experiment


class Design:
    """Everything derived from the identified model (normalised units, y = omega/omega_max)."""

    def __init__(self, sim):
        self.model = m = load_model(sim)
        self.a = m.a                       # motor pole [1/s]
        self.b_n = m.b_n                   # normalised input gain
        self.ys = m.omega_max              # velocity scale [rad/s]
        # reference model  dym/dt = -am*ym + bm*r : REF_SPEEDUP x faster than the motor, but never faster
        # than the dead time allows (a loop with dead time Td cannot track faster than ~3*Td)
        self.am = min(config.REF_SPEEDUP * m.a, 1.0 / (3 * m.Td)) if m.Td > 0 else config.REF_SPEEDUP * m.a
        self.bm = self.am                  # unit DC gain

    def describe(self, rep):
        m = self.model
        rep.text(f"Identified model: tau = {m.tau:.3g} s (a = {self.a:.3g} 1/s), K = {m.K:.3g} rad/s/PWM, "
                 f"dead zone ~ {0.5 * (m.u0_pos + m.u0_neg):.0f} PWM, omega_max = {self.ys:.1f} rad/s.\n\n"
                 f"Normalised plant: dy/dt = -{self.a:.3g} y + {self.b_n:.3g} u_n   "
                 f"(y = omega/{self.ys:.1f}, u_n = u/{config.U_MAX}).\n\n"
                 f"Reference model: dym/dt = -{self.am:.3g} ym + {self.bm:.3g} r  "
                 f"(time constant {1 / self.am:.3g} s; open loop {m.tau:.3g} s, dead time {m.Td:.3g} s).")

    def references(self, long_run=None, fast_sine=False):
        """Standard test references in physical units: name -> (r(t), duration)."""
        refs = {
            "steps": (signals.staircase([lv * self.ys for lv in config.REF_LEVELS], config.REF_HOLD),
                      config.RUN_TIME),
            "sine": (signals.sine(config.SINE_AMP * self.ys, config.SINE_PERIOD), config.RUN_TIME),
        }
        if fast_sine:
            refs["sine_fast"] = (signals.sine(config.SINE_AMP * self.ys, config.FAST_SINE_PERIOD), config.RUN_TIME)
        if long_run:
            refs["long_step"] = (signals.constant(0.5 * self.ys), long_run)
        return refs


def disturbance_from_args(args):
    amp = getattr(args, "disturbance", None) or config.DISTURBANCE_PWM
    return signals.random_disturbance(amp) if amp > 0 else None


def run_adaptive(rig, rep, controller, reference, duration, name, ideal=None, disturbance=None,
                 y_key="omega", y_label="omega [rad/s]"):
    """Run one adaptive experiment from rest, save CSV + plot, return its summary-table row."""
    rest(rig)
    log = run_experiment(rig, controller, reference, duration, name, disturbance)
    rep.save_log(log)
    rep.figure(plot_tracking(log, name, ideal, y_key, y_label), name)
    if "no measured motion" in log.status:
        rep.text(f"\n**LAB STOPPED - hardware fault:** {name}: {log.status}. Runs after this one were not done.")
        rep.save()                       # keep the report of everything measured so far
        raise RuntimeError(f"{name}: {log.status}. Stopping the lab - fix the hardware and re-run.")
    return adaptive_summary_row(log, ideal), log


def long_run_time(args):
    return args.long if args.long else (60.0 if args.quick else config.LONG_RUN_TIME)


HEADERS = ADAPTIVE_HEADERS

INTERPRETATION = (
    "**How to read the table.** *RMS e* is the normalised tracking error y - ym (0.01 = 1 % of omega_max). "
    "*PE level* = worst-case lambda_min/lambda_max of the windowed regressor covariance "
    "(≈0: not persistently exciting -> parameters need not converge to the ideal values; "
    "> ~0.01: PE holds -> parameters should approach the dashed ideal lines). "
    "*param drift* = largest parameter change during the second half of the run "
    "(large on a constant reference = parameter drift, the precursor of bursting/instability)."
)
