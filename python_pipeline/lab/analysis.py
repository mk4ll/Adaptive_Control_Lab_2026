"""
Metrics, plots and the Markdown report (summary.md) written for every lab run.
"""
import datetime

import matplotlib

matplotlib.use("Agg")                     # no windows: everything is saved to files
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

from lab import config                   # noqa: E402

# categorical colours in fixed order (blue, orange, aqua, yellow, magenta, green)
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
REF_GRAY = "#8a8a85"

plt.rcParams.update({
    "figure.dpi": 110, "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "axes.titlesize": 11, "axes.labelsize": 9, "legend.fontsize": 8, "legend.frameon": False,
})


# ================================ report ===================================

class Report:
    """Collects text, tables and figures; save() writes <outdir>/summary.md."""

    def __init__(self, lab, sim):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.outdir = config.RESULTS_DIR / ("sim" if sim else "rig") / f"{lab}_{stamp}"
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.lines = [f"# {lab} - {'SIMULATION' if sim else 'HARDWARE'} run {stamp}\n"]

    def h2(self, text):
        self.lines.append(f"\n## {text}\n")

    def text(self, text):
        self.lines.append(text + "\n")

    def table(self, headers, rows):
        self.lines.append("| " + " | ".join(headers) + " |")
        self.lines.append("|" + "---|" * len(headers))
        for row in rows:
            self.lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
        self.lines.append("")

    def figure(self, fig, name):
        fig.savefig(self.outdir / f"{name}.png", bbox_inches="tight")
        plt.close(fig)
        self.lines.append(f"![{name}]({name}.png)\n")

    def save_log(self, log):
        log.save_csv(self.outdir)

    def save(self):
        path = self.outdir / "summary.md"
        path.write_text("\n".join(self.lines))
        print(f"\n[report] {path}")
        return path


def fmt(v):
    if isinstance(v, (float, np.floating)):
        return f"{v:.3g}" if abs(v) < 1e4 else f"{v:.3e}"
    return str(v)


# ================================ metrics ==================================

def rms(x):
    x = np.asarray(x)
    return float(np.sqrt(np.mean(x**2))) if len(x) else float("nan")


def tracking_metrics(log):
    """RMS normalised tracking error over the whole run and over the last 25 %."""
    e = log["e_n"]
    n = len(e)
    return {"rms_e": rms(e), "rms_e_end": rms(e[3 * n // 4:])}


def pe_level(log, window=config.SINE_PERIOD):
    """
    Persistent-excitation check of the regressor w(t):
        for each window of `window` seconds compute R = mean(w w^T)
        level = lambda_min(R) / lambda_max(R)   (0 = not exciting, 1 = perfectly exciting)
    Returns the worst (minimum) level over all complete windows.
    """
    keys = [k for k in log.keys() if k.startswith("w_")]
    if not keys:
        return float("nan")
    W = np.column_stack([log[k] for k in keys])
    n_win = max(int(round(window / config.TS)), 1)
    levels = []
    for i in range(0, len(W) - n_win + 1, n_win):
        R = W[i:i + n_win].T @ W[i:i + n_win] / n_win
        eig = np.linalg.eigvalsh(R)
        levels.append(eig[0] / eig[-1] if eig[-1] > 1e-12 else 0.0)
    return float(min(levels)) if levels else float("nan")


def param_drift(log):
    """Max change of any parameter over the last half of the run (drift indicator)."""
    keys = [k for k in log.keys() if k.startswith("p_")]
    n = len(log["t"])
    return max(float(np.ptp(log[k][n // 2:])) for k in keys) if keys and n > 2 else float("nan")


def final_params(log):
    return {k[2:]: float(log[k][-1]) for k in log.keys() if k.startswith("p_")}


def adaptive_summary_row(log, ideal=None):
    """One table row: name, status, rms errors, PE level, drift, final parameters (ideal)."""
    m = tracking_metrics(log)
    params = final_params(log)
    ideal = ideal or {}
    ptxt = ", ".join(f"{k}={v:.3g}" + (f" ({ideal[k]:.3g})" if k in ideal else "") for k, v in params.items())
    verdict = "OK" if log.ok and m["rms_e_end"] < 0.05 else ("UNSTABLE/ABORTED" if not log.ok else "poor tracking")
    return [log.name, log.status if not log.ok else verdict, m["rms_e"], m["rms_e_end"],
            pe_level(log), param_drift(log), ptxt]


ADAPTIVE_HEADERS = ["experiment", "verdict", "RMS e (norm)", "RMS e last 25%", "PE level",
                    "param drift (2nd half)", "final params (ideal)"]


# ================================ plots ====================================

def plot_tracking(log, title, ideal=None, y_key="omega", y_label="omega [rad/s]", show_ref=True):
    """Response vs reference (and reference model), control input, adaptive parameters."""
    params = [k for k in log.keys() if k.startswith("p_")]
    n_rows = 3 if params else 2
    fig, axes = plt.subplots(n_rows, 1, figsize=(9, 2.4 * n_rows + 0.6), sharex=True)
    t = log["t"]

    ax = axes[0]
    if show_ref:
        ax.plot(t, log["r"], color=REF_GRAY, lw=1.2, ls="--", label="reference r")
    if "ym" in log:
        ax.plot(t, log["ym"], color=COLORS[1], label="reference model ym")
    ax.plot(t, log[y_key], color=COLORS[0], label="measured")
    ax.set_ylabel(y_label)
    ax.legend(loc="best", ncol=3)
    ax.set_title(f"{title}   [{log.status}]")

    axes[1].plot(t, log["u"], color=COLORS[0])
    axes[1].axhline(config.U_MAX, color=REF_GRAY, lw=0.8, ls=":")
    axes[1].axhline(-config.U_MAX, color=REF_GRAY, lw=0.8, ls=":")
    axes[1].set_ylabel("u [PWM]")

    if params:
        ax = axes[2]
        for i, k in enumerate(params):
            c = COLORS[i % len(COLORS)]
            ax.plot(t, log[k], color=c, label=k[2:])
            if ideal and k[2:] in ideal:
                ax.axhline(ideal[k[2:]], color=c, lw=1.0, ls="--")
        ax.set_ylabel("parameters\n(dashed = ideal)")
        ax.legend(loc="best", ncol=len(params))
    axes[-1].set_xlabel("time [s]")
    fig.tight_layout()
    return fig
