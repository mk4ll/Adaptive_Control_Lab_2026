"""
Lab I.1 - Modelling and identification of the coupled DC motors.

Model:  tau * d(omega)/dt = -omega + K*(u(t - Td) - u0)     (first order + dead time + dead zone)

Steps (all automatic except D, which needs you to turn the load potentiometer):
  A. Open-loop steps of +/- ID_PWM_LEVELS from rest
       -> table (u, omega_ss)  -> gain K, dead zone u0 and breakaway PWM ub (separately for u>0 and u<0)
       -> table (u, Td, tau, rise time 10-90%)  -> dead time Td and pole a = 1/tau
     + a slow (quasi-static) PWM triangle -> stick-slip hysteresis, stop threshold us
  B. Model validation with step, slow sinusoid and ramp (triangle) inputs -> fit %
  C. P and PI controllers designed from the identified model, tested on reference steps
  D. Step responses for several load-potentiometer positions -> K and tau vs load
The identified model is saved to results/<rig|sim>/model.json for Labs I.2 - I.6.
"""
import numpy as np

from lab import config, signals
from lab.analysis import COLORS, Report, plot_tracking, plt, rms
from lab.controllers import OpenLoop, PController, PIController
from lab.model import MotorModel, save_model
from lab.runner import rest, run_experiment

T0 = 0.5    # every identification step starts at t = T0 (first T0 seconds at u = 0)


def analyse_step(log, u):
    """Steady-state velocity, dead time (5 %), time constant (63.2 % minus dead time), 10-90 % rise time."""
    t, w = log["t"] - T0, log["omega"]
    after = t >= 0
    tail = t > t[-1] - 1.0                                  # last second = steady state
    w_ss = float(np.mean(w[tail]))
    w0 = float(np.mean(w[~after])) if np.any(~after) else 0.0
    # settled? compare the last two 0.5 s windows
    prev = (t > t[-1] - 1.5) & (t <= t[-1] - 0.5)
    settled = abs(np.mean(w[prev]) - w_ss) < 0.03 * abs(w_ss) + 0.02

    def crossing(frac):
        target = w0 + frac * (w_ss - w0)
        idx = np.where(after & (np.sign(w_ss - w0) * (w - target) >= 0))[0]
        return float(t[idx[0]]) if len(idx) else float("nan")

    Td = crossing(0.05)
    tau = crossing(0.632) - Td
    tr = crossing(0.9) - crossing(0.1)
    return {"u": u, "omega_ss": w_ss, "Td": Td, "tau": tau, "rise_10_90": tr, "settled": settled}


def fit_gain(rows, sign):
    """Least squares  omega_ss = K*u + c  on the steps that actually moved  ->  K, u0 = -c/K."""
    w_max = max(abs(r["omega_ss"]) for r in rows)
    pts = [(r["u"], r["omega_ss"]) for r in rows if np.sign(r["u"]) == sign and abs(r["omega_ss"]) > 0.05 * w_max]
    if len(pts) < 2:
        raise RuntimeError("Too few moving steps to fit the gain - increase ID_PWM_LEVELS.")
    u, w = np.array(pts).T
    K, c = np.polyfit(u, w, 1)
    zero = -c / K                                   # PWM where the fitted line crosses omega = 0
    return float(K), float(max(sign * zero, 0.0))   # dead zone (kinetic) >= 0


def breakaway(rows, sign):
    """Midpoint between the largest step that did not move the shaft and the smallest that did."""
    w_max = max(abs(r["omega_ss"]) for r in rows)
    still = [abs(r["u"]) for r in rows if np.sign(r["u"]) == sign and abs(r["omega_ss"]) <= 0.05 * w_max]
    moved = [abs(r["u"]) for r in rows if np.sign(r["u"]) == sign and abs(r["omega_ss"]) > 0.05 * w_max]
    if not still:
        return 0.0
    return 0.5 * (max(still) + min(moved))


def quasi_static(rig, rep, model):
    """Slow PWM triangle: omega vs u shows the stick-slip hysteresis -> breakaway and stop thresholds."""
    rest(rig)
    period = 40.0
    log = run_experiment(rig, OpenLoop(), signals.triangle(config.U_MAX, period), period, "quasi_static")
    rep.save_log(log)
    u, w = log["u"], log["omega"]
    moving = np.abs(w) > 0.05 * model.omega_max
    starts = np.where(~moving[:-1] & moving[1:])[0] + 1
    stops = np.where(moving[:-1] & ~moving[1:])[0] + 1
    delay = int(round(model.Td / config.TS))                 # motion reacts Td after the input
    u_start = u[np.clip(starts - delay, 0, None)]
    u_stop = u[np.clip(stops - delay, 0, None)]
    th = {}
    for name, vals in (("ub", u_start), ("us", u_stop)):
        for sign, label in ((+1, "pos"), (-1, "neg")):
            sel = np.abs(vals[np.sign(vals) == sign])
            th[f"{name}_{label}"] = float(np.median(sel)) if len(sel) else float("nan")
    # kinetic characteristic: least squares on all moving samples (input shifted by the dead time)
    u_lag = np.concatenate([np.full(delay, u[0]), u])[:len(u)]
    for sign, label in ((+1, "pos"), (-1, "neg")):
        sel = moving & (np.sign(w) == sign) & (np.sign(u_lag) == sign)
        if sel.sum() > 20:
            K, c = np.polyfit(u_lag[sel], w[sel], 1)
            th[f"K_{label}"], th[f"u0_{label}"] = float(K), float(max(sign * (-c / K), 0.0))

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(u, w, color=COLORS[0], lw=1.2, label="measured (slow triangle)")
    grid = np.linspace(-config.U_MAX, config.U_MAX, 300)
    ax.plot(grid, model.steady_state(grid), color=COLORS[1], ls="--", label="kinetic line K(u - u0)")
    ax.set_xlabel("u [PWM]"), ax.set_ylabel("omega [rad/s]"), ax.legend()
    ax.set_title("Stick-slip hysteresis")
    rep.figure(fig, "hysteresis")
    return th


def identification(rig, rep):
    rep.h2("A. Step tests: steady-state gain and time constant")
    rows, logs = [], []
    for sign in (+1, -1):
        for level in config.ID_PWM_LEVELS:
            u = sign * level
            rest(rig)
            log = run_experiment(rig, OpenLoop(), signals.step(u, t0=T0), T0 + config.ID_STEP_HOLD, f"step_u{u:+d}")
            rep.save_log(log)
            rows.append(analyse_step(log, u))
            logs.append(log)

    K_pos, u0_pos = fit_gain(rows, +1)
    K_neg, u0_neg = fit_gain(rows, -1)
    moving = [r for r in rows if abs(r["omega_ss"]) > 0.2 * max(abs(x["omega_ss"]) for x in rows)]
    tau_pos = float(np.nanmedian([r["tau"] for r in moving if r["u"] > 0]))
    tau_neg = float(np.nanmedian([r["tau"] for r in moving if r["u"] < 0]))
    Td = float(np.nanmedian([r["Td"] for r in moving]))
    model = MotorModel(K_pos, K_neg, u0_pos, u0_neg, tau_pos, tau_neg, Td,
                       ub_pos=breakaway(rows, +1), ub_neg=breakaway(rows, -1))
    th = quasi_static(rig, rep, model)
    # the slow triangle has thousands of moving samples -> preferred source for the kinetic line
    for label in ("pos", "neg"):
        if f"K_{label}" in th:
            setattr(model, f"K_{label}", th[f"K_{label}"])
            setattr(model, f"u0_{label}", th[f"u0_{label}"])
    model.us_pos = th["us_pos"] if np.isfinite(th["us_pos"]) else model.u0_pos
    model.us_neg = th["us_neg"] if np.isfinite(th["us_neg"]) else model.u0_neg

    rep.table(["u [PWM]", "omega_ss [rad/s]", "model omega_ss", "dead time Td [s]", "tau (63%) - Td [s]",
               "rise 10-90% [s]", "settled?"],
              [[r["u"], r["omega_ss"], float(model.steady_state(r["u"])), r["Td"], r["tau"], r["rise_10_90"],
                "yes" if r["settled"] else "NO - increase ID_STEP_HOLD"] for r in rows])
    rep.text("Identified parameters. Kinetic line omega = K(u - u0) from all moving samples of the slow triangle; "
             "tau and Td = medians over the moving steps (rise_10_90 ~ 2.2*tau is a consistency check). "
             "ub > us means stick-slip hysteresis: the shaft needs more PWM to start than to keep moving. "
             "Breakaway varies from one start to the next (shaft position, gearbox), compare the two ub rows.")
    rep.table(["", "u > 0", "u < 0", "average (used for design)"],
              [["gain K, slow triangle (used) [rad/s/PWM]", model.K_pos, model.K_neg, model.K],
               ["gain K, steps (cross-check)", K_pos, K_neg, ""],
               ["dead zone u0 of the kinetic line [PWM]", model.u0_pos, model.u0_neg, ""],
               ["breakaway from rest ub (steps) [PWM]", model.ub_pos, model.ub_neg, ""],
               ["breakaway from rest (slow triangle) [PWM]", th["ub_pos"], th["ub_neg"], ""],
               ["stop threshold us (slow triangle) [PWM]", model.us_pos, model.us_neg, ""],
               ["time constant tau [s]", tau_pos, tau_neg, model.tau],
               ["pole a = 1/tau [1/s]", 1 / tau_pos, 1 / tau_neg, model.a],
               ["dead time Td [s]", "", "", model.Td],
               ["b = a*K", "", "", model.b],
               ["omega_max [rad/s]", "", "", model.omega_max]])

    # static characteristic
    fig, ax = plt.subplots(figsize=(6.5, 4))
    u_grid = np.linspace(-config.U_MAX, config.U_MAX, 300)
    ax.plot(u_grid, model.steady_state(u_grid), color=COLORS[1], label="fitted model")
    ax.plot([r["u"] for r in rows], [r["omega_ss"] for r in rows], "o", color=COLORS[0], ms=6, label="measured")
    ax.set_xlabel("u [PWM]"), ax.set_ylabel("steady-state omega [rad/s]"), ax.legend()
    for ub, us, s in ((model.ub_pos, model.us_pos, 1), (model.ub_neg, model.us_neg, -1)):
        ax.axvline(s * ub, color=COLORS[2], lw=1.0, ls=":")
        ax.axvline(s * us, color=COLORS[3], lw=1.0, ls=":")
    ax.plot([], [], color=COLORS[2], ls=":", label="breakaway ub"), ax.plot([], [], color=COLORS[3], ls=":", label="stop us")
    ax.legend()
    ax.set_title("Static characteristic (gain, dead zone, stick-slip)")
    rep.figure(fig, "static_characteristic")

    # all step responses
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for log in logs:
        u = log["u"][-1]
        ax = axes[0] if u > 0 else axes[1]
        ax.plot(log["t"] - T0, log["omega"], lw=1.2, label=f"{u:+.0f}")
    for ax, name in zip(axes, ("u > 0", "u < 0")):
        ax.set_title(f"Step responses, {name}"), ax.set_xlabel("time after step [s]")
        ax.legend(title="PWM", ncol=2)
    axes[0].set_ylabel("omega [rad/s]")
    rep.figure(fig, "step_responses")
    return model


def validation(rig, rep, model):
    rep.h2("B. Model validation")
    rep.text("Model = first order + dead time + stick-slip. "
             "fit % = 100 * (1 - ||omega - omega_model|| / ||omega - mean(omega)||); above ~80 % is good.")
    tests = {
        "val_step": (signals.step(0.6 * config.U_MAX, t0=1.0), 8.0),
        "val_sine": (signals.sine(0.7 * config.U_MAX, 10.0), 25.0),
        "val_ramp": (signals.triangle(0.8 * config.U_MAX, 12.0), 25.0),
    }
    rows = []
    for name, (u_sig, T) in tests.items():
        rest(rig)
        log = run_experiment(rig, OpenLoop(), u_sig, T, name)
        rep.save_log(log)
        w_model = model.simulate(log["t"], log["u"], log["omega"][0])
        fit = 100 * (1 - np.linalg.norm(log["omega"] - w_model) / np.linalg.norm(log["omega"] - log["omega"].mean()))
        both = (np.abs(log["omega"]) > 0.05 * model.omega_max) & (np.abs(w_model) > 0.05 * model.omega_max)
        y, ym = log["omega"][both], w_model[both]
        informative = both.sum() > 10 and np.std(y) > 0.1 * np.mean(np.abs(y))   # undefined for a constant speed
        fit_mov = 100 * (1 - np.linalg.norm(y - ym) / np.linalg.norm(y - y.mean())) if informative else "n/a"
        rows.append([name, fit, fit_mov, rms(log["omega"] - w_model)])

        fig, axes = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
        axes[0].plot(log["t"], log["omega"], color=COLORS[0], label="measured")
        axes[0].plot(log["t"], w_model, color=COLORS[1], label="model")
        axes[0].set_ylabel("omega [rad/s]"), axes[0].legend(), axes[0].set_title(f"{name}: fit {fit:.1f} %")
        axes[1].plot(log["t"], log["u"], color=COLORS[0]), axes[1].set_ylabel("u [PWM]")
        axes[1].set_xlabel("time [s]")
        rep.figure(fig, name)
    rep.table(["input", "fit %", "fit % while both moving", "RMS error [rad/s]"], rows)
    rep.text("*fit while moving* judges the dynamic model (gain, tau, Td) without the random breakaway instants.")


def classical_control(rig, rep, model):
    rep.h2("C. P and PI velocity control designed from the model")
    K, tau, Td = model.K, model.tau, model.Td
    # lambda (IMC) tuning for a first-order-plus-dead-time plant: the closed-loop time constant
    # lambda cannot be made much faster than the dead time, so lambda = max(tau/speedup, 2*Td)
    lam = max(tau / config.PI_SPEEDUP, 2 * Td)
    Kp_pi = tau / (K * (lam + Td))
    Ki_pi = Kp_pi / tau                       # integral time = tau (zero cancels the motor pole)
    lam_p = max(tau / config.P_SPEEDUP, 2 * Td)
    Kp = tau / (K * (lam_p + Td))
    dc_gain = K * Kp / (1 + K * Kp)
    rep.text(f"Plant: K = {K:.4g} rad/s/PWM, tau = {tau:.3g} s, dead time Td = {Td:.3g} s. "
             f"Lambda tuning: lambda = max(tau/speedup, 2*Td).\n\n"
             f"- P:  Kp = tau/(K(lambda+Td)) = **{Kp:.4g}** (lambda = {lam_p:.3g} s), "
             f"predicted steady-state ratio omega/r = K Kp/(1 + K Kp) = {dc_gain:.3f}\n"
             f"- PI: Kp = tau/(K(lambda+Td)) = **{Kp_pi:.4g}**, Ki = Kp/tau = **{Ki_pi:.4g}** (lambda = {lam:.3g} s), "
             f"zero steady-state error\n\n"
             f"Small references sit inside the stick-slip band, so expect stick-slip cycling there: the controller "
             f"must build up ~ub PWM to break away, then the shaft overshoots and sticks again.")
    levels = [f * model.omega_max for f in (0.3, 0.6, -0.3, -0.6, 0.0)]
    ref = signals.staircase(levels, 4.0)
    rows = []
    for name, ctrl in (("P_control", PController(Kp)), ("PI_control", PIController(Kp_pi, Ki_pi))):
        rest(rig)
        log = run_experiment(rig, ctrl, ref, 20.0, name)
        rep.save_log(log)
        rep.figure(plot_tracking(log, name), name)
        # steady-state ratio at the end of each level
        ratios = []
        for i, lv in enumerate(levels[:-1]):
            m = (log["t"] > 4 * i + 3.0) & (log["t"] < 4 * (i + 1))
            ratios.append(float(np.mean(log["omega"][m]) / lv))
        rows.append([name, float(np.mean(ratios)), rms(log["r"] - log["omega"])])
    rep.table(["controller", "measured omega/r at steady state", "RMS error [rad/s]"], rows)
    rep.text(f"(Predicted ratio: P = {dc_gain:.3f}, PI = 1.000. If the P output K_p*e stays below the breakaway "
             f"PWM ub, the shaft never starts (ratio 0): P control alone cannot overcome stick-slip, the PI integrator "
             f"builds up the missing PWM, which shows as a short stall at every sign change.)")


def load_variation(rig, rep):
    rep.h2("D. Effect of the load potentiometer on the second motor")
    rows = []
    fig, ax = plt.subplots(figsize=(8, 4))
    n = len(config.ID_LOAD_POSITIONS)
    u = 0.6 * config.U_MAX
    for i, pos in enumerate(config.ID_LOAD_POSITIONS):
        rig.ask_user(f"Set the load potentiometer of the second motor to: {pos.upper()}")
        if hasattr(rig, "set_load"):
            rig.set_load(i / max(n - 1, 1))
        rest(rig)
        log = run_experiment(rig, OpenLoop(), signals.step(u, t0=T0), T0 + config.ID_STEP_HOLD, f"load_{pos}")
        rep.save_log(log)
        r = analyse_step(log, u)
        rows.append([pos, r["omega_ss"], r["omega_ss"] / u, r["tau"], 1 / r["tau"]])
        ax.plot(log["t"] - T0, log["omega"], color=COLORS[i % len(COLORS)], label=pos)
    ax.set_xlabel("time after step [s]"), ax.set_ylabel("omega [rad/s]"), ax.legend(title="load")
    ax.set_title(f"Step u = {u:.0f} PWM for different loads")
    rep.figure(fig, "load_variation")
    rep.table(["load", "omega_ss [rad/s]", "omega_ss/u", "tau [s]", "a = 1/tau"], rows)
    rep.text("More electrical load on the generator = more braking torque: expect lower speed and a faster pole.")


def main(rig, sim, args):
    rep = Report("lab1_identification", sim)
    model = identification(rig, rep)
    path = save_model(model, sim)
    rep.text(f"Model saved to `{path}`")
    validation(rig, rep, model)
    classical_control(rig, rep, model)
    if not args.skip_load:
        load_variation(rig, rep)
        if hasattr(rig, "set_load"):
            rig.set_load(0.0)
    rest(rig)
    rep.save()
