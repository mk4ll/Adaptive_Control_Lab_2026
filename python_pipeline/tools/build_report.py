"""Builds the Part I lab report PDF from the results of 2026-10-14."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.lib.fonts import addMapping

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "results" / "rig"
OUT = ROOT / "Lab_Report_PartI_DC_Motors.pdf"

L1 = R / "lab1_identification_20261014_142130"
LT = R / "load_test"
L2 = R / "lab2_mit_20261014_143203"
L3 = R / "lab3_mrac_20261014_144115"
L4 = R / "lab4_adi_20261014_145549"
L5 = R / "lab5_robust_20261014_151220"
L6 = R / "lab6_angle_20261021_134413"          # session 2: 9 of 12 runs
L1B = R / "lab1_identification_20261021_133847"  # session 2: re-identification of the repaired motor
X6 = R / "extras_lab6rest_20261021_141759"       # session 2: projection/sine, long steps
X6S = R / "extras_lab6rest_20261021_142835"      # session 2: sigma-mod toward nominal values
XMIT = R / "extras_mitlow_20261021_143740"       # session 2: MIT maps on the repaired motor
XDZ = R / "extras_lab5dz_20261021_144555"        # session 2: Lab I.5 deadzone with e0 = 0.06
XMR = R / "extras_mraclong_20261021_145241"      # session 2: 10 min MRAC on the repaired motor

# ---------------- fonts / styles ----------------
F = "/usr/share/fonts/truetype/dejavu/"          # DejaVu covers all symbols used (Greek, ≈, →, −, ≤, ⁻¹)
pdfmetrics.registerFont(TTFont("Noto", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Noto-Bold", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Noto-Italic", F + "DejaVuSans.ttf"))   # no oblique installed
pdfmetrics.registerFont(TTFont("Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
addMapping("Noto", 0, 0, "Noto")
addMapping("Noto", 1, 0, "Noto-Bold")
addMapping("Noto", 0, 1, "Noto-Italic")
addMapping("Noto", 1, 1, "Noto-Bold")

ss = getSampleStyleSheet()
INK, MUTED, ACCENT, RULE, HEAD_BG = (colors.HexColor(c) for c in ("#1f1f1d", "#5f5e5a", "#2a78d6", "#d9d8d3", "#eef3fa"))
body = ParagraphStyle("body", parent=ss["Normal"], fontName="Noto", fontSize=9.5, leading=13.5, textColor=INK,
                      spaceAfter=5)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=MUTED)
cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Noto-Bold")
h1 = ParagraphStyle("h1", parent=body, fontName="Noto-Bold", fontSize=15, leading=19, spaceBefore=6, spaceAfter=8,
                    textColor=INK)
h2 = ParagraphStyle("h2", parent=body, fontName="Noto-Bold", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=5,
                    textColor=ACCENT)
title = ParagraphStyle("title", parent=h1, fontSize=22, leading=27, alignment=TA_CENTER, spaceAfter=4)
subtitle = ParagraphStyle("subtitle", parent=body, fontSize=11, alignment=TA_CENTER, textColor=MUTED)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=3)
caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER, spaceAfter=10)

story = []
P = lambda t, s=body: story.append(Paragraph(t, s))
H1 = lambda t: story.append(Paragraph(t, h1))
H2 = lambda t: story.append(Paragraph(t, h2))


def B(items):
    for t in items:
        story.append(Paragraph(t, bullet, bulletText="•"))


def T(rows, widths, header=True, bold_first_col=False):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(str(c), cellb if (header and i == 0) or (bold_first_col and j == 0) else cell)
                     for j, c in enumerate(r)])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), HEAD_BG))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 6))


def FIG(path, cap, width=16.0):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    img = Image(str(path), width=width * cm, height=width * cm * h / w)
    story.append(KeepTogether([img, Paragraph(cap, caption)]))


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFont("Noto", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, "Adaptive Control Lab, Part I: coupled DC motors | sessions 2026-10-14 and 2026-10-21")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"page {doc.page}")
    canvas.restoreState()


# ======================================================================
story.append(Spacer(1, 2.5 * cm))
P("Adaptive Control Laboratory, Part I", title)
P("Coupled DC motors: identification, MIT rule, MRAC, ADI, robust and angle control", subtitle)
story.append(Spacer(1, 0.4 * cm))
P("Experimental report, sessions of 14 and 21 October 2026", subtitle)
story.append(Spacer(1, 1.2 * cm))

H2("Status at a glance")
T([["Lab", "Status", "Main result"],
   ["I.1 Identification", "Done",
    "FOPDT model + stick-slip: K ≈ 0.020 rad/s/PWM, τ = 0.128 s, Td = 0.115 s; breakaway 115–200 PWM, stop "
    "60–75 PWM; PI tracks with zero error, P cannot overcome stiction; load pot max end: −75 % speed"],
   ["I.2 MIT rule", "Done",
    "Original motor: stable for γ·r0² < c, c between 14.7 and 16. Repaired motor: boundary between γ = 30 and 40, "
    "nearly independent of r0"],
   ["I.3 Scalar MRAC", "Done", "Stable 10 min, but linear parameter drift (no PE on a constant reference); "
    "reproduced on the repaired motor"],
   ["I.4 Scalar ADI", "Done", "Stable; stiction blocks the slow-sine half-periods; slower drift than MRAC"],
   ["I.5 Robust MRAC/ADI", "Done",
    "Friction-aware models halve the error (MRAC sine 9.9 → 4.6 %, ADI 29 → 6.3 %); σ-mod and a deadzone wider "
    "than the noise (e0 = 0.06) stop the drift"],
   ["I.6 Angle (vector MRAC)", "Done",
    "All 5 methods on steps and sine: stable, 0.20–0.49 rad RMS; σ-mod toward nominal best. 5 min hold stable "
    "(0.002 rad). Projection hold: windup against stiction to full PWM (stopped at 51 s / 74 s)"]],
  [3.6, 1.6, 11.8])

P("All numbers come from the automatically generated reports in <font name='Mono' size='8'>results/rig/</font> "
  "(one folder per lab with summary.md, a CSV of every run and the plots). Velocities are in rad/s at the motor "
  "shaft, inputs in PWM counts (±255). In Labs I.2–I.6 the adaptive laws work with normalised signals "
  "y = ω/ω<sub>max</sub> and u<sub>n</sub> = u/255. “e” is the normalised tracking error y − y<sub>m</sub>, "
  "so 0.05 means 5 % of ω<sub>max</sub> ≈ 0.24 rad/s.", small)
story.append(PageBreak())

# ======================================================================
H1("1. Setup and experiment pipeline")
H2("Hardware (as found on the bench)")
B(["Arduino Mega 2560 on /dev/ttyACM0, 115200 baud. The lab's original sketch was backed up "
   "(firmware/backup/original_lab_sketch.hex) and its wiring decoded from the binary: two-PWM motor driver "
   "(pin 4 = positive, pin 5 = negative direction), quadrature encoder on pins 18/19, 2150 counts/rev (x1).",
   "Our firmware (firmware/motor_io/motor_io.ino) is a thin real-time I/O layer: every 10 ms it sends "
   "time, angle, velocity, potentiometer and applied PWM; it applies the PWM sent back by Python and switches the "
   "motor off if no command arrives for 200 ms. Encoder decoded x4 (8600 counts/rev), velocity low-pass "
   "filtered (α = 0.5). Measured sample period: 10.00 ms, max 10.01 ms.",
   "The motor is a slow geared motor: about 4.7 rad/s (≈ 45 rpm) at full PWM."])
H2("Software")
B(["All controllers run in Python (lab/controllers.py) in a hardware-in-the-loop configuration; one command per "
   "lab (python run.py lab1 … lab6) runs all experiments automatically and writes a report.",
   "A simulator (lab/rig.py, SimRig) reproduces the identified rig (dead time, stick-slip, quantisation); every "
   "controller was tuned on it before running on the motors.",
   "Safety: abort on |ω| > 20 rad/s, on adaptive parameter divergence (|θ| > 20 normalised), and, added after the "
   "Lab I.6 fault, on full PWM without measured motion for 2 s."])

# ======================================================================
H1("2. Lab I.1: modelling and identification")
P("<b>Model.</b> First-order plus dead time with stick-slip friction:  τ dω/dt = −ω + K(u(t − Td) − u0), "
  "valid while the shaft moves; from rest the shaft only starts when |u| exceeds the breakaway PWM ub, and a moving "
  "shaft sticks again when |u| drops below the stop threshold us.")
H2("Step tests (open loop, from rest)")
rows = [["u [PWM]", "ω_ss [rad/s]", "Td [s]", "τ [s]", "rise 10–90 % [s]"]]
for line in (L1 / "summary.md").read_text().splitlines():
    p = [c.strip() for c in line.strip("|").split("|")]
    if len(p) == 7 and p[0].lstrip("-").isdigit():
        moved = p[1] != "0"
        rows.append([p[0], p[1], p[3] if moved else "–", p[4] if moved else "–", p[5] if moved else "–"])
half = (len(rows) - 1) // 2
left, right = rows[:1] + rows[1:1 + half], rows[:1] + rows[1 + half:]
t = Table([[Table([[Paragraph(c, cellb if i == 0 else cell) for c in r] for i, r in enumerate(left)],
                  colWidths=[1.4 * cm, 1.8 * cm, 1.2 * cm, 1.2 * cm, 2.0 * cm]),
            Table([[Paragraph(c, cellb if i == 0 else cell) for c in r] for i, r in enumerate(right)],
                  colWidths=[1.4 * cm, 1.8 * cm, 1.2 * cm, 1.2 * cm, 2.0 * cm])]])
for sub in t._cellvalues[0]:
    sub.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, RULE), ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
story.append(t)
P("Steps of |u| ≤ 100 PWM (up to 100 for u &lt; 0) did not break the static friction: ω_ss = 0.", small)

m = json.loads((R / "model_2026-10-14.json").read_text())   # session-1 model (model.json is the latest)
H2("Identified parameters")
T([["", "u > 0", "u < 0", "used for design"],
   ["gain K (kinetic line, slow ramp) [rad/s/PWM]", f"{m['K_pos']:.4f}", f"{m['K_neg']:.4f}",
    f"{0.5 * (m['K_pos'] + m['K_neg']):.4f}"],
   ["gain K from steps (cross-check)", "0.0178", "0.0149", ""],
   ["dead zone of the kinetic line u0 [PWM]", f"{m['u0_pos']:.0f}", f"{m['u0_neg']:.0f}", ""],
   ["breakaway from rest ub: steps / slow ramp [PWM]", "115 / 153", "115 / 181", "varies per start: 87–200"],
   ["stop threshold us [PWM]", f"{m['us_pos']:.0f}", f"{m['us_neg']:.0f}", ""],
   ["time constant τ [s]", f"{m['tau_pos']:.3f}", f"{m['tau_neg']:.3f}", "0.128 (a = 7.84 s⁻¹)"],
   ["dead time Td [s]", "", "", f"{m['Td']:.3f}"],
   ["ω_max [rad/s]", "", "", "4.74"]], [7.2, 2.4, 2.4, 5.0], bold_first_col=True)
P("The parameters were repeatable across three identification runs (τ 0.127–0.13 s, Td 0.105–0.115 s, K "
  "0.017–0.020). The breakaway PWM is not: it changed between 87 and 200 PWM from one start to the next "
  "(depends on shaft/gear position). rise(10–90 %) ≈ 0.27–0.38 s vs 2.2·τ = 0.28 s is consistent with first order.")
FIG(L1 / "step_responses.png", "Figure 1: open-loop step responses (all levels).", 15.5)
FIG(L1 / "hysteresis.png", "Figure 2: slow PWM triangle: stick-slip hysteresis. The shaft needs much more PWM "
    "to start than to keep moving; the moving branches define the kinetic line K(u − u0).", 11.5)

H2("Model validation")
T([["input", "fit % (all samples)", "fit % while moving", "RMS error [rad/s]"],
   ["step 153 PWM", "74.8", "n/a (constant speed)", "0.27"],
   ["slow sine ±179 PWM, 10 s", "51.4", "85.1", "1.09"],
   ["ramp/triangle ±204 PWM, 12 s", "71.1", "83.2", "0.65"]], [5.2, 3.6, 4.0, 4.2])
P("While the shaft moves, the model reproduces the response well (83–85 %). The overall fit is lower because "
  "the breakaway instants are random and cannot be predicted by any deterministic model (Figure 3).")
FIG(L1 / "val_sine.png", "Figure 3: validation with a slow sinusoidal PWM (measured vs model).", 14)

H2("P and PI control from the model")
P("Because of the dead time the closed loop cannot be made much faster than Td, so the controllers were tuned with "
  "the lambda (IMC) rule for a FOPDT plant: λ = max(τ/3, 2·Td) = 0.23 s, Kp = τ/(K(λ + Td)), Ti = τ. "
  "(A first design that ignored the dead time, Kp = 158, produced a stick-slip limit cycle.)")
T([["controller", "gains", "predicted ω/r", "measured ω/r", "RMS error [rad/s]"],
   ["P", "Kp = 18.7", "0.27", "0 (shaft never started)", "2.01"],
   ["PI", "Kp = 18.7, Ki = 146.5", "1", "0.998", "0.58"]], [2.0, 4.0, 2.6, 4.2, 3.2])
P("The P controller never moves the shaft: Kp·e stays far below the breakaway PWM. The PI integrator builds up "
  "the missing PWM and tracks every level with zero steady-state error; at each sign change the shaft stalls "
  "for ~0.6 s while the integrator crosses the stiction band (Figure 4).")
FIG(L1 / "PI_control.png", "Figure 4: PI velocity control on reference steps.", 14)

H2("Effect of the load potentiometer on the second motor")
loads = []
for pos in ("minimum", "middle", "maximum"):
    res = json.loads((LT / f"{pos}.json").read_text())
    for s in (1, -1):
        sel = [r for r in res if (r["u"] > 0) == (s > 0)]
        w = sum(r["omega_ss"] for r in sel) / len(sel)
        tau = sum(r["tau"] for r in sel) / len(sel)
        loads.append([pos, f"{s * 180:+d}", f"{w:.2f}", f"{w / (s * 180):.4f}", f"{tau:.3f}", f"{1 / tau:.1f}"])
T([["load", "u [PWM]", "ω_ss [rad/s]", "gain ω/u", "τ [s]", "a = 1/τ [s⁻¹]"]] + loads, [2.6, 2.0, 2.8, 2.8, 2.4, 3.0])
P("Maximum load cuts the steady-state gain by ≈ 4× (−75 to −78 %) and makes the pole ≈ 3.5× faster: the "
  "generator's braking torque (∝ speed) adds damping. The repeat scatter is ±0.02 rad/s, so this is > 100× the "
  "noise. Between the minimum end and the middle the effect is ≤ 2 % (not significant): braking current "
  "∝ 1/(R<sub>armature</sub> + R<sub>pot</sub>) only becomes large when R<sub>pot</sub> approaches the armature "
  "resistance, near the maximum end. The pot was initially not connected (no effect at any position); two runs "
  "affected by a wrong pot position and a loose contact were excluded (results/rig/load_test/excluded/). "
  "The identification above was done at minimum/middle load.")
FIG(LT / "load_variation.png", "Figure 5: step responses for minimum, middle and maximum load.", 15)

# ======================================================================
story.append(PageBreak())
H1("3. Adaptive control: common design (Labs I.2–I.6)")
B(["Normalised plant: dy/dt = −a·y + b<sub>n</sub>·u<sub>n</sub>, a = 7.84 s⁻¹, b<sub>n</sub> = 8.35.",
   "Reference model: dy<sub>m</sub>/dt = −a<sub>m</sub>y<sub>m</sub> + b<sub>m</sub>r with "
   "a<sub>m</sub> = b<sub>m</sub> = min(2a, 1/(3·Td)) = 2.9 s⁻¹ (time constant 0.35 s). The dead time makes a "
   "faster model impossible to follow.",
   "References: steps of ±0.3 and ±0.6 ω<sub>max</sub> (5 s each), slow sine (amplitude 0.5, period 10 s, as in "
   "the manual), a faster sine (period 3 s) for comparing persistent excitation (PE), and a long constant step at "
   "0.5 ω<sub>max</sub>.",
   "PE level = worst λ<sub>min</sub>/λ<sub>max</sub> of the windowed regressor covariance (0 = no excitation).",
   "The “ideal” parameter values printed in the tables follow from the <i>linear</i> model; with stiction the "
   "controllers settle elsewhere, because the real plant has less gain at low speed.",
   "The verdict “poor tracking” in the reports means RMS error in the last 25 % above 5 % of ω<sub>max</sub>; on "
   "this rig it is almost always caused by stick-slip at zero crossings, not by instability."])

H1("4. Lab I.2: MIT rule")
P("u = θ<sub>1</sub>r − θ<sub>2</sub>y,  dθ<sub>1</sub>/dt = −γ[a<sub>m</sub>/(s+a<sub>m</sub>) r]e,  "
  "dθ<sub>2</sub>/dt = γ[a<sub>m</sub>/(s+a<sub>m</sub>) y]e,  γ = 5 for the tracking runs.")
T([["experiment", "RMS e", "RMS e last 25 %", "PE level", "final θ1, θ2 (linear ideal 0.347, −0.592)"],
   ["steps", "0.127", "0.071", "0.004", "1.32, 0.44"],
   ["slow sine", "0.122", "0.103", "0.006", "1.41, 0.10"],
   ["fast sine", "0.137", "0.124", "0.073", "0.92, −0.06"]], [2.4, 1.6, 2.6, 1.8, 8.6])
H2("Stability map (γ × reference amplitude r0, square wave, 24 s per run)")
T([["γ \\ r0", "0.2", "0.4", "0.7"],
   ["1", "stuck (stiction), γr0² = 0.04", "stable (0.16)", "stable (0.49)"],
   ["3", "stable (0.12)", "stable (0.48)", "stable (1.47)"],
   ["10", "stable (0.4)", "stable (1.6)", "stable (4.9)"],
   ["30", "stable (1.2)", "stable (4.8)", "stable (14.7), larger oscillation"],
   ["100", "stable (4)", "UNSTABLE (16), aborted at 10 s", "UNSTABLE (49), aborted at 0.9 s"]],
  [1.6, 4.6, 5.2, 5.6], bold_first_col=True)
P("<b>Experimental stability condition:</b> every stable run has γ·r0² ≤ 14.7 and every unstable run γ·r0² ≥ 16, "
  "i.e. the MIT loop is stable for γ·r0² &lt; c with c ≈ 15. For the ideal first-order model the linearised MIT loop "
  "is second order and always stable; the dead time (≈ 0.12 s) is the unmodelled dynamics that creates the bound, "
  "and the bound scales with the square of the signal level, as predicted. The boundary rests on one row "
  "(γ = 100); a finer sweep between γ = 30 and 100 would locate c more precisely.")
FIG(L2 / "mit_stability_map.png", "Figure 6: MIT rule stability map; dashed line γ·r0² = 15.3.", 10.5)
FIG(L2 / "mit_steps.png", "Figure 7: MIT rule on reference steps (γ = 5).", 14)

# ======================================================================
H1("5. Lab I.3: scalar MRAC")
P("u = k·y + l·r,  dk/dt = −γ·y·e,  dl/dt = −γ·r·e,  γ = 3 (γ ≥ 20 was unstable in simulation). Initial estimates 0.")
T([["experiment", "RMS e", "RMS e last 25 %", "PE level", "drift (2nd half)", "final k, l (linear ideal 0.592, 0.347)"],
   ["steps", "0.154", "0.070", "0.015", "1.11", "−0.89, 1.74"],
   ["slow sine", "0.124", "0.099", "0.015", "0.31", "−0.22, 1.27"],
   ["fast sine", "0.139", "0.118", "0.073", "0.17", "−0.24, 1.10"],
   ["constant step, 10 min", "0.027", "0.015", "0.0002", "0.12", "−0.21, 1.22"]], [3.0, 1.4, 2.4, 1.6, 2.2, 6.4])
B(["<b>Long run:</b> no instability in 10 min (speed held at 2.4 rad/s, 1.5 % RMS error, input flat at ≈ 135 PWM), "
   "but k and l drift linearly in opposite directions (l 1.0 → 1.23, k 0.0 → −0.21) without saturating. On a "
   "constant reference y ≈ r, so only the combination k·y + l·r is identifiable (it stays constant); noise moves "
   "the parameters along the unidentifiable direction. This is the parameter drift that the robust modifications "
   "of Lab I.5 address.",
   "<b>Stiction:</b> at the small level (1.4 rad/s) the shaft sticks and the adaptive law integrates the error, so l "
   "winds up to 2.2 until the shaft breaks free, followed by an overshoot to 4.4 rad/s.",
   "<b>PE:</b> the slow sine (manual) is weakly exciting (0.015); the fast sine raises it to 0.073."])
FIG(L3 / "mrac_long_step.png", "Figure 8: MRAC, 10 min constant step: stable tracking, linear parameter drift.", 14)

H1("6. Lab I.4: scalar adaptive dynamic inversion (ADI)")
P("Plant estimate dy/dt = â·y + b̂·u; control u = (dy<sub>m</sub>/dt − k<sub>e</sub>e − â·y)/b̂; "
  "dâ/dt = γ·y·e, db̂/dt = γ·u·e, b̂ ≥ 0.1 b<sub>n</sub>; γ = 3, k<sub>e</sub> = 2 s⁻¹ (k<sub>e</sub> ≲ 1/(3 Td)). "
  "Initial estimates 50 % of the model values. (“ADI” was interpreted as adaptive dynamic inversion, the "
  "indirect counterpart of MRAC.)")
T([["experiment", "RMS e", "RMS e last 25 %", "PE level", "drift", "final â, b̂ (linear ideal −7.84, 8.35)"],
   ["steps", "0.234", "0.105", "0.052", "1.13", "−1.54, 1.90"],
   ["slow sine", "0.255", "0.292", "0.037", "2.16", "−1.52, 1.58"],
   ["fast sine", "0.154", "0.143", "0.093", "0.40", "−3.19, 3.33"],
   ["constant step, 10 min", "0.055", "0.020", "0.0003", "0.21", "−2.10, 2.09"]], [3.0, 1.4, 2.4, 1.6, 1.4, 7.2])
B(["On the slow sine most positive half-periods never break free: the ADI output peaks at 70–130 PWM, below the "
   "breakaway PWM; ADI has no integrator-like term to build the missing PWM (MRAC's l effectively did that).",
   "Long run: stable (2 % error); â and b̂ drift together (−2.5 → −2.1 and 2.5 → 2.1 in 10 min) along the "
   "unidentifiable direction â·y + b̂·u = const, slightly slower than MRAC.",
   "The estimates settle far below the linear model (b̂ 1.6–3.3 vs 8.35): with stiction the motor responds less "
   "to small inputs, and a smaller b̂ makes the inversion more aggressive."])
FIG(L4 / "adi_sine.png", "Figure 9: ADI on the slow sine: stuck positive half-periods.", 14)

# ======================================================================
H1("7. Lab I.5: robust adaptive control (scalar MRAC and ADI)")
P("Uncertainty model: offset + Coulomb friction, basis [1, tanh(v/v0)]. Design choices made after simulation "
  "tests (a naive version was worse than plain MRAC): (i) friction term seeded with the measured stop threshold "
  "(≈ 67 PWM) instead of 0; (ii) basis driven by the <i>reference-model</i> velocity y<sub>m</sub>, so it is "
  "non-zero at standstill and helps break stiction (known signal, Lyapunov analysis unchanged); (iii) offset/friction "
  "terms adapt 0.3× slower; (iv) σ/e-mod leak toward the nominal Lab I.1 values. Robust settings: deadzone "
  "e0 = 0.02, σ = 0.01, projection |θi| ≤ 5. Each method: steps 40 s, slow sine 40 s, constant step 5 min.")
T([["controller", "steps, e last 25 %", "slow sine, e last 25 %", "long step"],
   ["MRAC (I.3)", "7.0 %", "9.9 %", "l drift +0.23 / 10 min"],
   ["MRAC + friction model, no modification (I.5)", "4.3 %", "4.6 %", "practically no drift"],
   ["ADI (I.4)", "10.5 %", "29 %", "slow drift"],
   ["ADI + friction model, no modification (I.5)", "3.8 %", "6.3 %", "steady drift (Fig. 11)"]],
  [7.2, 3.0, 3.4, 3.4], bold_first_col=True)
T([["method", "MRAC steps", "MRAC sine", "MRAC long", "ADI steps", "ADI sine", "ADI long"],
   ["none", "4.3 %", "4.6 %", "1.2 %", "3.8 %", "6.3 %", "2.6 %"],
   ["deadzone", "4.0 %", "4.7 %", "1.6 %", "4.4 %", "6.9 %", "2.5 %"],
   ["σ-modification", "5.3 %", "6.2 %", "2.4 %", "4.4 %", "9.0 %", "4.0 %"],
   ["e-modification", "3.9 %", "4.8 %", "1.2 %", "4.7 %", "7.3 %", "2.6 %"],
   ["projection", "3.6 %", "4.8 %", "1.2 %", "4.2 %", "6.9 %", "2.3 %"]],
  [3.0, 2.3, 2.3, 2.3, 2.3, 2.3, 2.3], bold_first_col=True)
P("(RMS normalised error over the last 25 % of each run.)", small)
B(["With friction modelled, the friction estimate settles at a consistent level (MRAC dc ≈ 0.26–0.31, i.e. "
   "≈ 70 PWM, matching the measured stop threshold) and the MRAC feedforward gain lands near the linear-model value "
   "(l ≈ 0.35–0.39 vs 0.347), instead of 1.2–1.7 in Lab I.3.",
   "<b>Drift (long constant step):</b> ADI without modification, and with deadzone, e-mod or projection, shows a "
   "steady linear decrease of ‖θ‖ (5.8 → 5.5 in 5 min). Only σ-modification stops it (plateau at 5.74), at the cost "
   "of a larger error (4.0 % vs 2.5 %): the classical leakage trade-off.",
   "The deadzone did not stop the drift because e0 = 0.02 is smaller than the velocity noise on this rig "
   "(|e| ≈ 0.03–0.05): adaptation never switches off. e0 ≈ 0.06 would be appropriate.",
   "Projection never activated: the parameters stayed well inside the bound |θi| ≤ 5.",
   "MRAC barely drifted with any method; σ-mod moved it to a new biased equilibrium (‖θ‖ 0.45 → 0.6, error ≈ 2×).",
   "PE on the slow sine is very low (0.001–0.004) for these 4-parameter models: the slow sine is not sufficiently "
   "rich to identify them."])
FIG(L5 / "mrac_long_comparison.png", "Figure 10: MRAC, 5 min constant step: parameter norm and |e| per method.", 14)
FIG(L5 / "adi_long_comparison.png", "Figure 11: ADI, 5 min constant step: drift for all methods except σ-mod.", 14)

# ======================================================================
H1("8. Session 2 (21 Oct): re-identification of the repaired motor")
P("The motor was repaired between the sessions. Before Lab I.6 the identification of Lab I.1 was repeated "
  "(steps and slow triangle), because Lab I.6 uses the model for its reference model and stiction compensation.")
m2 = json.loads((R / "model.json").read_text())
T([["", "14 Oct (original motor)", "21 Oct (repaired motor)"],
   ["gain K (avg) [rad/s/PWM]", f"{0.5 * (m['K_pos'] + m['K_neg']):.4f}", f"{0.5 * (m2['K_pos'] + m2['K_neg']):.4f}"],
   ["time constant τ (avg) [s]", f"{0.5 * (m['tau_pos'] + m['tau_neg']):.3f}", f"{0.5 * (m2['tau_pos'] + m2['tau_neg']):.3f}"],
   ["dead time Td [s]", f"{m['Td']:.3f}", f"{m2['Td']:.3f}"],
   ["breakaway ub (+ / −) [PWM]", f"{m['ub_pos']:.0f} / {m['ub_neg']:.0f}", f"{m2['ub_pos']:.1f} / {m2['ub_neg']:.1f}"],
   ["stop threshold us (+ / −) [PWM]", f"{m['us_pos']:.0f} / {m['us_neg']:.0f}", f"{m2['us_pos']:.0f} / {m2['us_neg']:.0f}"],
   ["ω_max [rad/s]", "4.74", "4.55"],
   ["validation fit while moving (slow sine)", "85.1 %", "85.1 %"]], [6.0, 5.0, 5.0], bold_first_col=True)
P("The repaired motor is very close to the original (gain −7 %, τ +4 %, slightly lower stiction). The repair did "
  "not hold reliably: the motor stopped responding after ≈ 3 min of operation (validation ramp, P/PI runs of this "
  "identification are invalid, see NOTE_INVALID_RUNS.md), was fixed again, and failed once more after ≈ 6 min "
  "during Lab I.6. The stall watchdog cut the power within 2–3 s each time.")

H1("9. Lab I.6: robust adaptive angle control")
P("x = [θ, ω]; reference model θ<sub>m</sub>'' + 2ζω<sub>n</sub>θ<sub>m</sub>' + ω<sub>n</sub>²θ<sub>m</sub> = "
  "ω<sub>n</sub>²r with ω<sub>n</sub> = 1.5 rad/s, ζ = 1 (limited by ω<sub>max</sub> and the dead time); "
  "u = k1θ + k2ω + d0 + l·r plus a stiction compensation at the output equal to the measured stop threshold "
  "(62 PWM, 21 Oct model); dθ/dt = −Γw(eᵀPB0), A<sub>m</sub>ᵀP + PA<sub>m</sub> = −I; γ = 5; estimates start at 0 "
  "(except “σ-mod toward nominal”). References: angle steps π → 2π → 0 → −π (5 s each), a slow sine ±π "
  "(period 10 s), and a 5 min hold at π. All runs on 21 Oct (repaired motor).")
T([["method", "steps: RMS angle error vs θm, last 25 %", "sine: RMS angle error, last 25 %",
    "5 min hold at π", "param drift (steps / sine)"],
   ["none", "0.27 rad", "0.33 rad", "stable, error 0.002 rad, drift 0.04", "0.58 / 0.42"],
   ["deadzone", "0.42 rad", "0.43 rad", "–", "0.61 / 0.32"],
   ["σ-mod (toward 0)", "0.49 rad", "0.31 rad", "–", "0.57 / 0.32"],
   ["σ-mod (toward nominal)", "<b>0.20 rad</b>", "0.30 rad", "–", "0.23 / 0.37"],
   ["e-modification", "0.34 rad", "0.31 rad", "–", "0.62 / 0.37"],
   ["projection", "0.33 rad", "0.31 rad", "windup to full PWM, aborted at 51 s and 74 s", "0.50 / 0.36"]],
  [3.4, 3.4, 3.0, 4.6, 2.6], bold_first_col=True)
B(["<b>All tracking runs are stable</b>: the angle follows the reference model through steps of π and 2π, with the "
   "largest errors at the start of each step (the shaft must break away) and hold errors of 0.09–0.31 rad at the end "
   "of the steps (stiction band).",
   "<b>σ-modification depends on where it leaks to.</b> Starting at 0 and leaking toward 0 pulls the feedforward gain "
   "down (l = 0.03 at the end of the sine run vs 0.40 ideal) and gives the worst step error (0.49 rad). Starting at and "
   "leaking toward the nominal model values keeps l at 0.35–0.47 and gives the <b>best</b> step error of all methods "
   "(0.20 rad), the same lesson as in Lab I.5.",
   "<b>No modification, e-mod and projection</b> behave almost the same (projection is inactive: the parameters stay "
   "well inside |θi| ≤ 5). <b>Deadzone</b> stops adaptation for |e| &lt; e0, so small residual errors are no longer "
   "corrected (0.42 rad on steps).",
   "<b>Long hold (“leave it running”):</b> without modification the controller reached π almost exactly and held it "
   "for 5 min (error 0.002 rad, negligible drift): no instability. With projection the shaft stopped 0.2 rad short of "
   "the target inside the stiction band; the adaptive law then integrated that standing error (d0 and l grew steadily) "
   "and ramped the PWM from ≈ 115 to 255 within 10–18 s while the shaft stayed stuck. Both attempts were stopped by the "
   "stall watchdog (at 51 s and 74 s). This is parameter windup caused by stick-slip, a drift-type instability that "
   "projection does not prevent because the parameters stay inside its bound; a deadzone wider than the stiction band "
   "is the matching remedy.",
   "PE is low on both references (0.001–0.007), so the parameters do not converge to the linear-model values.",
   "Session 1 (14 Oct, original motor) gave consistent results for the three runs completed before its motor "
   "failure (0.35 / 0.43 / 0.47 rad for none-steps, none-sine, deadzone-steps)."])
FIG(L6 / "angle_none_steps.png", "Figure 12: vector MRAC angle control on steps, no modification.", 12)
FIG(X6S / "angle_sigma_nominal_steps.png", "Figure 13: σ-modification leaking toward the nominal values: the best "
    "step tracking of all methods, l stays near its ideal value.", 12)
FIG(X6 / "angle_projection_long_step.png", "Figure 14: projection, hold at π: the shaft sticks short of the target and "
    "the adaptive law winds the PWM up to saturation (stopped by the watchdog).", 12)

H1("10. Follow-up experiments (21 Oct, repaired motor)")
H2("Lab I.2: MIT stability map on the repaired motor")
P("A finer sweep (γ = 40–85) and a low-γ sweep (γ = 5–30), each for r0 = 0.4–0.7, 24 s per run, same "
  "classification as Lab I.2 (40 runs).")
FIG(XMIT / "mit_map_combined.png", "Figure 15: MIT stability map of the repaired motor (both sweeps).", 11)
B(["Every run with γ ≤ 30 is stable (γ·r0² up to 14.7); 19 of 20 runs with γ ≥ 40 are unstable, down to "
   "γ·r0² = 6.4 (the one stable point, γ = 50 / r0 = 0.5, is borderline). On this motor the boundary is therefore "
   "<b>30 &lt; γ &lt; 40, almost independent of the amplitude</b> in the tested range, rather than a constant γ·r0².",
   "Compared with the original motor (stable up to γ·r0² = 14.7, unstable from 16): the repaired motor has a shorter "
   "dead time, so the reference model is faster (a<sub>m</sub> = 3.7 vs 2.9 s⁻¹), and the stick-slip at small "
   "amplitudes is different. Both shift the boundary; the classical γ·r0² scaling comes from a linearisation and holds "
   "only approximately with this much friction.",
   "Practical conclusion for the rig: keep γ ≤ 30 (the tracking runs used γ = 5)."])
H2("Lab I.5: deadzone wider than the noise (e0 = 0.06)")
T([["", "MRAC steps / sine", "MRAC long step: drift", "ADI steps / sine", "ADI long step: drift"],
   ["e0 = 0.02 (14 Oct, 5 min step)", "4.0 % / 4.7 %", "0.081", "4.4 % / 6.9 %", "0.221"],
   ["e0 = 0.06 (21 Oct, 2 min step)", "3.6 % / 4.8 %", "<b>0</b>", "4.0 % / 7.1 %", "<b>0.002</b>"]],
  [4.4, 3.0, 3.2, 3.0, 3.2], bold_first_col=True)
P("(RMS error in the last 25 %; drift = largest parameter change in the second half of the long step.) With e0 "
  "above the velocity noise, adaptation really switches off once the error is small and the drift on the constant "
  "step disappears, with no loss of tracking accuracy. The runs were on different motors and the long step was 2 min "
  "instead of 5, but the drift rate dropped by two orders of magnitude.")
H2("Lab I.3: 10 min MRAC on the repaired motor")
T([["time", "1 min", "2 min", "5 min", "7.5 min", "10 min"],
   ["k", "0.065", "0.050", "−0.016", "−0.077", "−0.127"],
   ["l", "0.865", "0.904", "0.980", "1.019", "1.057"],
   ["k + l", "0.930", "0.953", "0.964", "0.942", "0.930"]], [2.4, 2.4, 2.4, 2.4, 2.4, 2.4], bold_first_col=True)
P("Stable tracking (1.4 % RMS error at the end) and the same linear drift as on the original motor (l +0.19 in "
  "9 min vs +0.23 in 10 min): k and l move in opposite directions while k + l (the only identifiable combination when "
  "y ≈ r) stays constant. The drift result of Lab I.3 is reproducible across two motors. A longer run would not "
  "add information: at this drift rate l would only reach ≈ 1.7 after 30 min, far from any instability.")

H2("Hardware faults")
P("<b>14 Oct:</b> at ≈ 16:21 (18.9 s into deadzone/sine) the motor stopped responding at a moderate command "
  "(≈ 100 PWM); the controller then saturated at +255 PWM for ≈ 12 min because the safety checks did not yet cover "
  "this case. A stall/sensor-loss watchdog (full PWM without measured motion for 2 s → motor off, lab stopped) was "
  "added. <b>21 Oct:</b> the repaired motor stopped responding several times, after between 15 s and ≈ 6 min of "
  "operation, typically at moments of high current (direction reversals, or full PWM at standstill); each time it "
  "worked again after a short pause, and the watchdog cut the power within 3 s. This pattern is consistent with the "
  "motor driver's current-limit / over-temperature protection (or a connection that opens when warm) rather than a "
  "permanently broken motor. The last 25 min of experiments ran without a failure.")

# ======================================================================
H1("11. Files")
B(["Reports, plots and CSV data: <font name='Mono' size='8'>results/rig/&lt;lab&gt;_&lt;time&gt;/</font>; identified "
   "model: <font name='Mono' size='8'>results/rig/model.json</font>; load test: "
   "<font name='Mono' size='8'>results/rig/load_test/</font>. "
   "Code: <font name='Mono' size='8'>run.py</font>, <font name='Mono' size='8'>lab/</font>, "
   "<font name='Mono' size='8'>experiments/</font>, firmware in <font name='Mono' size='8'>firmware/motor_io/</font>; "
   "all settings in <font name='Mono' size='8'>lab/config.py</font>."])

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                        bottomMargin=2 * cm, title="Adaptive Control Lab Part I: Report",
                        author="Adaptive Control Lab")
doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
print(OUT)
