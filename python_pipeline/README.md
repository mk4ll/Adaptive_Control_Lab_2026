# Adaptive Control Lab, Part I: Coupled DC Motors

An automated pipeline for Labs I.1 to I.6 of the *Laboratory Manual* (Adaptive Control & RL, ECE UPatras).
You flash the Arduino **once**, then run one command per lab. Each run does all of its experiments on its own,
stops the motor between them, and writes a report (`summary.md`) with tables, plots and the CSV of every run.
Your job is to read the report and judge whether the results make sense.

**Step-by-step instructions for every script: [HOW_TO_RUN.md](HOW_TO_RUN.md).**
**Results (sessions 2026-10-14 and 2026-10-21): [Lab_Report_PartI_DC_Motors.pdf](Lab_Report_PartI_DC_Motors.pdf)** and `results/rig/`.

```
 Arduino (motor_io.ino)                 PC (Python)
 ───────────────────────                ─────────────────────────────────────────────
 every 10 ms:                           run.py lab3
   read encoder / tacho / pot  ──────▶    runner: r(t) → controller → u
   send "t,theta,omega,pot,u"             (lab/controllers.py: P, PI, MIT, MRAC, ADI, robust, vector MRAC)
   apply PWM  ◀──────────────────────     send u
 watchdog: no command for 200 ms → motor off
                                        → results/rig/lab3_mrac_<time>/summary.md + *.png + *.csv
```

The Arduino is only an I/O device. All control laws live in Python, so changing a controller or a gain
never means re-flashing.

---

## 1. One-time setup

### 1.1 Flash the Arduino
The sketch `firmware/motor_io/motor_io.ino` is configured for the lab bench: Arduino Mega 2560, a two-PWM
driver (pin 4 for u > 0, pin 5 for u < 0), and an encoder on pins 18/19 (2150 counts/rev, decoded x4).
These values were read out of the lab's original sketch. Upload it with the Arduino IDE, or from the command
line (see HOW_TO_RUN.md), and close the Serial Monitor afterwards. On a different bench, edit only the
`CONFIGURATION` block (driver type, pins, encoder counts, or a tachogenerator instead of an encoder).

### 1.2 Python
```bash
pip install -r requirements.txt        # pyserial, numpy, matplotlib
```
The serial port is auto-detected. If detection fails, set `PORT` in `lab/config.py`.

### 1.3 Dry run (no hardware needed)
```bash
python run.py all --sim                # whole pipeline on a simulated motor pair, ~2 minutes
```
The simulator (`SimRig`) mimics the identified bench (dead time, stick-slip friction), so a dry run behaves
much like the real motors.

---

## 2. Every lab session

```bash
python run.py check        # ~10 s: sample rate, noise, and the sign of u → omega (must PASS)
python run.py lab1         # identification. Writes results/rig/model.json, which all later labs use
python run.py lab2         # ... lab6
```

| Command | What runs automatically | Manual steps | Time on the rig |
|---|---|---|---|
| `check` | idle + ±50 % PWM spin | none | 10 s |
| `lab1` | 16 open-loop steps (±8 levels) and a slow PWM triangle → gain, dead zone, stick-slip thresholds, dead time and τ; validation with step, slow sine and ramp; P and PI control | `--skip-load` skips the interactive load part; use `run.py load --position …` instead | ~5 min |
| `load` | load-potentiometer test at one position (`--position minimum/middle/maximum`) | **set the pot** before each call | 25 s |
| `lab2` | MIT rule on steps, slow sine, fast sine; **γ × amplitude stability map** (15 runs) | none | ~9 min |
| `lab3` | scalar MRAC on steps, slow sine, fast sine, **10 min constant step** | none | ~12 min |
| `lab4` | scalar ADI on the same references | none | ~12 min |
| `lab5` | MRAC and ADI × {none, deadzone, σ-mod, e-mod, projection} × {steps, sine, 5 min step} | none | ~65 min |
| `lab6` | angle vector MRAC × 5 robust methods × {steps, sine} + 2 long steps | none | ~17 min |

Options: `--quick` (shorter runs, good for checking that everything works), `--long 1800` (length of the long runs),
`--disturbance 15` (adds a bounded random input disturbance of ±15 PWM, which makes parameter drift show up sooner in labs 3 to 6).

**Ctrl+C stops the motor at any time.** Every experiment also aborts on its own (motor off, status recorded) when
|ω| > `OMEGA_LIMIT` or an adaptive parameter diverges. The firmware watchdog switches the motor off if Python stops responding.

---

## 3. Checking the results

Open `results/rig/<lab>_<time>/summary.md` in VS Code (Markdown preview) or on GitHub. Each adaptive experiment has one table row:

| column | meaning | what you want |
|---|---|---|
| verdict | OK / poor tracking / UNSTABLE-ABORTED | OK |
| RMS e (norm) | tracking error y − y_m relative to ω_max | a few % |
| RMS e last 25 % | the same, after adaptation | smaller than the whole-run value |
| PE level | worst λ_min/λ_max of the windowed regressor covariance | ≈0 for steps, higher for the fast sine |
| param drift | largest parameter change in the 2nd half | small; large on a constant step means drift |
| final params (ideal) | estimates next to the values the Lab I.1 model predicts | close only when PE holds |

Sanity checks worth doing:
- **check**: both spin directions PASS. If the sign is wrong, flip `MOTOR_SIGN` (or `ENC_SIGN`) and re-flash. All adaptive laws assume sign(b) = +1.
- **lab1**: every step should say "settled? yes" (if not, increase `ID_STEP_HOLD`), validation fit should be above ~80 %, and rise(10–90 %) ≈ 2.2·τ.
- **labs 2–6**: parameters converge toward the dashed ideal lines mainly on `sine_fast`. On steps they only need to give good tracking.

---

## 4. Code map

```
firmware/motor_io/motor_io.ino   Arduino I/O layer (flash once)
run.py                           entry point: python run.py <check|lab1..lab6|all> [--sim]
lab/config.py                    ALL tunable settings (gains, levels, durations, safety)
lab/rig.py                       Rig (serial) and SimRig (simulator), same interface
lab/runner.py                    real-time loop + safety + Log (CSV)
lab/signals.py                   step, staircase, sine, triangle, from_pot, disturbance
lab/model.py                     identified first-order model (save/load model.json)
lab/controllers.py               OpenLoop, P, PI, MIT, MRACScalar, ADIScalar, MRACVector, Robust
lab/analysis.py                  metrics (RMS, PE level, drift), plots, Markdown report
experiments/check.py, lab1_identification.py, lab2_mit.py, lab3_mrac.py,
experiments/lab4_adi.py, lab5_robust.py, lab6_angle.py, common.py
```

To use the potentiometer as the reference instead of a programmed signal, pass
`signals.from_pot(low, high)` as the reference in any experiment.

---

## 5. Theory summary (what each controller implements)

**Model (Lab I.1).** First order plus dead time with stick-slip: τ ω̇ = −ω + K(u(t − T_d) − u₀) while the shaft
moves; from rest it only starts above the breakaway PWM u_b, and it sticks again below the stop PWM u_s.
K and u₀ come from a least-squares fit over the moving samples of a slow PWM triangle (separately for u > 0 and
u < 0); T_d (5 % time) and τ (63 % time − T_d) are medians over the step tests; u_b comes from the steps and u_s
from the triangle.
P/PI control: lambda (IMC) tuning for a plant with dead time, λ = max(τ/s, 2T_d), Kp = τ/(K(λ + T_d)), Ti = τ.

**Normalisation (Labs I.2–I.6).** y = ω/ω_max and u_n = u/255, which give ẏ = −a y + b_n u_n with b_n ≈ a. Because of this,
the adaptation gains in `config.py` are dimensionless and carry over between the simulator and the rig.
Reference model: ẏ_m = −a_m y_m + b_m r with a_m = b_m = min(2a, 1/(3T_d)). A loop with dead time cannot follow
anything faster.

**MIT rule (I.2).** u = θ₁r − θ₂y, θ̇₁ = −γ[a_m/(s+a_m) r]e, θ̇₂ = γ[a_m/(s+a_m) y]e.
Ideal values: θ₁* = b_m/b_n and θ₂* = (a_m − a)/b_n.
For the ideal first-order plant the linearised loop is 2nd order and always stable. Unmodelled dynamics
(velocity filter, driver, sampling and serial delay, inductance) make it 3rd order, and then it is stable only
for γ·r₀² < c. The stability map measures this boundary.

**Scalar MRAC (I.3).** u = k y + l r, k̇ = −γ y e, l̇ = −γ r e. With V = e²/2 + |θ̃|²/(2γ) this gives V̇ = −a_m e².
Ideal values: k* = (a − a_m)/b_n and l* = b_m/b_n. PE needs one sinusoid that is fast enough relative to a_m.

**ADI, adaptive dynamic inversion (I.4).** Plant estimate ẏ = â y + b̂ u. The control inverts it:
u = (ẏ_m − k_e e − â y)/b̂, with adaptation â̇ = γ y e and b̂̇ = γ u e, and b̂ ≥ b_min enforced by projection.
This gives ė = −k_e e + θ̃ᵀw and V̇ = −k_e e². It is the indirect counterpart of MRAC: it estimates the plant, not the controller.

**Robust (I.5).** The regressor is extended with [1, tanh(v/v₀)] for offset and Coulomb friction, where v is the
reference-model velocity y_m (`FRICTION_FROM_REFERENCE`). Because y_m is non-zero at standstill, this also helps the
shaft break free. The friction term starts at the stop threshold measured in Lab I.1, and these terms adapt
0.3× slower (`FRICTION_GAMMA_SCALE`). Modifications of θ̇ = f:
dead zone (θ̇ = 0 when |e| < e₀), σ-mod (−σΓ(θ−θ₀)), e-mod (−σ|e|Γ(θ−θ₀)), and box projection (|θᵢ| ≤ bound).
θ₀ is the nominal Lab I.1 value. Leaking toward 0 makes l → 0, a large steady bias.

**Vector MRAC, angle (I.6).** x = [θ, ω], A_m = [[0,1],[−ω_n², −2ζω_n]].
Control u = k₁θ + k₂ω + d₀ + l r, adaptation θ̇ = −Γ w (eᵀP B₀), with A_mᵀP + PA_m = −I.
Ideal values: k₁* = −ω_n²/b_n, k₂* = (a − 2ζω_n)/b_n, l* = ω_n²/b_n.
ω_n = 1.5 rad/s (`ANGLE_WN`), slow enough for the motor's top speed and dead time. A dead-zone inverse equal to
the measured stop threshold u_s is added at the output, because near standstill the ideal gains ask for only
a few PWM. The Coulomb-friction basis is optional (`ANGLE_FRICTION_BASIS`): near standstill it acts like a
relay and can cause a limit cycle, which is worth a run of its own.

---

## 6. Tuning knobs (all in `lab/config.py`)

| Symptom | Knob |
|---|---|
| steps not settled in lab1 | `ID_STEP_HOLD` |
| tracking too slow or too aggressive | `REF_SPEEDUP`, `ANGLE_WN` |
| parameters adapt too slowly or oscillate | `MIT_GAMMA`, `MRAC_GAMMA`, `ADI_GAMMA`, `ANGLE_GAMMA` |
| MIT map shows no instability | extend `MIT_GAMMA_SWEEP` / `MIT_AMP_SWEEP` |
| σ-mod bias too large / deadzone too coarse | `SIGMA`, `DEADZONE_E0` |
| experiments abort on speed | `OMEGA_LIMIT` (set it ~20 % above ω_max from lab1) |
