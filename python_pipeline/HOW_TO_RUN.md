# How to run everything

This guide covers every script in this folder: what it does, how to start it, how long it takes, and where its
results go. Background and theory are in [README.md](README.md). The report of both sessions is
[Lab_Report_PartI_DC_Motors.pdf](Lab_Report_PartI_DC_Motors.pdf).

---

## 0. Folder layout

| Path | What it is |
|---|---|
| `run.py` | **The only entry point.** `python run.py <command> [options]` |
| `lab/config.py` | Every tunable setting: gains, reference levels, durations, safety limits |
| `lab/rig.py` | `Rig` (real Arduino over USB) and `SimRig` (simulator tuned to the real bench) |
| `lab/runner.py` | The real-time loop (read → controller → write), safety checks, CSV logging |
| `lab/controllers.py` | OpenLoop, P, PI, MIT rule, scalar MRAC, ADI, robust modifications, vector MRAC |
| `lab/signals.py` | Reference signals: step, staircase, square, sine, triangle, potentiometer, disturbance |
| `lab/model.py` | Identified motor model (first order + dead time + stick-slip), saved as `model.json` |
| `lab/analysis.py` | Metrics (RMS error, PE level, parameter drift), plots, `summary.md` reports |
| `experiments/*.py` | One file per lab, called by `run.py` |
| `firmware/motor_io/motor_io.ino` | Arduino sketch (thin I/O layer, flash once) |
| `tools/build_report.py` | Rebuilds the PDF report from the results |
| `results/rig/` | All hardware results from 2026-10-14 and 2026-10-21 (one folder per run) |

---

## 1. One-time setup

### 1.1 Python
```bash
pip install -r requirements.txt      # pyserial, numpy, matplotlib
```
Python 3.10 or newer. On Linux your user must be in the `dialout` group to open the serial port
(`groups` shows it; if not: `sudo usermod -aG dialout $USER`, then log out and back in).

### 1.2 Flash the Arduino (only once, or after someone else re-flashed the board)
The firmware is **already configured for the lab bench**: an Arduino Mega 2560, a two-PWM motor driver
(pin 4 for u > 0, pin 5 for u < 0), and an encoder on pins 18/19 with 2150 counts/rev, decoded x4 to 8600.

**With the Arduino IDE:** open `firmware/motor_io/motor_io.ino`, select *Arduino Mega or Mega 2560* and the
port, and click Upload. Close the Serial Monitor afterwards.

**From the command line** (Arduino IDE 1.8 snap on Linux):
```bash
S=/snap/arduino/current; T=$S/hardware/tools/avr; B=/tmp/motor_io_build; mkdir -p $B
$S/arduino-builder -compile -hardware $S/hardware -tools $S/tools-builder -tools $T \
  -built-in-libraries $S/libraries -fqbn arduino:avr:mega:cpu=atmega2560 -build-path $B \
  firmware/motor_io/motor_io.ino
$T/bin/avrdude -C $T/etc/avrdude.conf -p atmega2560 -c wiring -P /dev/ttyACM0 -b 115200 -D \
  -U flash:w:$B/motor_io.ino.hex:i
```
On a different bench, edit only the `CONFIGURATION` block at the top of the sketch (driver type, pins,
encoder counts). `MOTOR_SIGN` / `ENC_SIGN` flip the directions if `check` reports a wrong sign.

### 1.3 Serial port
`PORT = "auto"` in `lab/config.py` finds the Arduino automatically. If it picks the wrong port, set it
explicitly, e.g. `PORT = "/dev/ttyACM0"` (Windows: `"COM3"`). Baud rate 115200, sample period 10 ms.
Both must match the firmware.

---

## 2. Commands

Every command runs all of its experiments automatically and stops the motor between them. **Ctrl+C stops the
motor at any time.** Each run creates `results/rig/<lab>_<date>_<time>/` with `summary.md` (tables and
verdicts), one CSV per experiment and the plots.

| Command | What it runs | Needs | Time on the rig |
|---|---|---|---|
| `python run.py check` | idle 1.5 s + ±128 PWM spins: sample rate, noise, sign of u → ω | flashed board | 10 s |
| `python run.py lab1 --skip-load` | Lab I.1: 16 open-loop steps, slow PWM triangle (hysteresis), validation (step/sine/ramp), P and PI control. **Writes `results/rig/model.json`** | `check` PASS | 5 min |
| `python run.py load --position <name>` | Lab I.1 load test: ±180 PWM steps (2× each) at one potentiometer position; rebuilds `results/rig/load_test/summary.md` with a significance check | lab1 | 25 s per position |
| `python run.py lab2` | Lab I.2 MIT rule: steps, slow sine, fast sine + 15-run γ × amplitude stability map | model.json | 9 min |
| `python run.py lab3` | Lab I.3 scalar MRAC: steps, slow sine, fast sine, 10 min constant step | model.json | 13 min |
| `python run.py lab4` | Lab I.4 scalar ADI: same set as lab3 | model.json | 13 min |
| `python run.py lab5` | Lab I.5 robust MRAC and ADI × {none, deadzone, σ-mod, e-mod, projection} × {steps, sine, 5 min step} | model.json | 65 min |
| `python run.py lab6` | Lab I.6 angle control (vector MRAC) × 5 robust methods × {steps, sine} + 2 long steps | model.json, encoder | 17 min |
| `python run.py all` | check + lab1 … lab6 back to back (no load test) | | ~2 h |
| `python run.py extras --part <p>` | Follow-up experiments: `lab6rest` (missing Lab I.6 runs + σ-mod toward nominal), `mitfine` / `mitlow` (MIT maps at γ = 40–85 / 5–30), `lab5dz` (Lab I.5 deadzone with e0 = 0.06), `mraclong` (long MRAC run), `all` | model.json | 1–30 min per part |

### Options
| Option | Effect |
|---|---|
| `--sim` | Use the simulator instead of the Arduino. Runs faster than real time; results go to `results/sim/`. Run `lab1 --sim` first so the simulator has its own `model.json` |
| `--quick` | Shorter runs (fewer identification levels, 20 s tracking runs, 60 s long runs) |
| `--long SECONDS` | Duration of the long constant-step runs (labs 3–6) |
| `--disturbance PWM` | Adds a bounded random input disturbance (labs 3–6), which makes parameter drift show up faster |
| `--skip-load` | lab1: skip the interactive load-potentiometer part (use the `load` command instead) |
| `--position NAME` | load: name of the potentiometer position, e.g. `minimum`, `middle`, `maximum` |
| `--skip a,b` | extras `lab6rest`: run names already measured (they are not repeated) |
| `--mrac-long SECONDS` | extras `mraclong`: duration (default 1800 s) |

### Load test workflow (needs someone at the bench)
```bash
python run.py load --position minimum    # turn the pot fully to one end first
python run.py load --position middle
python run.py load --position maximum
```
If you are not sure which end is which, use any name (e.g. `end_A`) and rename afterwards: the end that
lowers the speed by roughly 75 % is the maximum load.

---

## 3. Recommended order for a session
```bash
python run.py check                  # must PASS (both directions)
python run.py lab1 --skip-load       # identification -> model.json (repeat if the motor was changed)
python run.py lab2                   # ... then lab3, lab4, lab5, lab6
```
Labs 2–6 read the model from `results/rig/model.json`, so they always use the latest identification.
Long labs can run unattended. To chain two labs, just run them one after the other in the same shell:
`python run.py lab5 && python run.py lab6`.

---

## 4. Reading the results
Every adaptive experiment gets one row in `summary.md`:

| Column | Meaning |
|---|---|
| verdict | `OK`, `poor tracking` (RMS error in the last 25 % > 5 % of ω_max), or `ABORTED …` |
| RMS e (norm) | tracking error y − y_m relative to ω_max (0.05 = 5 %) |
| PE level | worst λ_min/λ_max of the windowed regressor covariance (≈ 0: no persistent excitation) |
| param drift | largest parameter change in the 2nd half (large on a constant step = drift) |
| final params (ideal) | estimates next to the values the *linear* model predicts |

On this rig "poor tracking" is almost always stick-slip at zero crossings, not instability. Check the plots.

---

## 5. Safety (automatic)
The runner aborts the experiment and switches the motor off when:
- |ω| > `OMEGA_LIMIT` (20 rad/s),
- an adaptive parameter exceeds `PARAM_LIMIT` (20, normalised) or becomes NaN,
- the command stays at ≥ 95 % PWM for `STALL_TIME` (2 s) with **no measured motion**: stalled motor, driver
  without power, or lost encoder. The lab then stops with a message to check the hardware.

The firmware also switches the motor off if Python stops sending commands for 200 ms.

---

## 6. Simulator and tuning
`SimRig` in `lab/rig.py` reproduces the bench measured on 2026-10-14: τ ≈ 0.12 s, dead time ≈ 0.1 s,
≈ 4.7 rad/s at full PWM, asymmetric breakaway 110/65 PWM, stop threshold 35 PWM, and encoder quantisation.
All gains in `lab/config.py` were tuned on it before running on the motors. Typical workflow when changing
a controller:
```bash
python run.py lab1 --sim --skip-load     # once, gives results/sim/model.json
python run.py lab3 --sim --long 120      # try the change in ~10 s
python run.py lab3                       # then on the real motors
```

---

## 7. Rebuilding the PDF report
```bash
python -m venv .venv && .venv/bin/pip install reportlab pypdf pillow
.venv/bin/python tools/build_report.py
```
It reads the result folders listed at the top of `tools/build_report.py`. Update those paths after new runs.

---

## 8. Status (2026-10-21)
- Labs I.1–I.6 done (I.1–I.5 on 14 Oct, I.6 and follow-up experiments on 21 Oct with the repaired motor).
  Everything is summarised in the PDF report.
- The Lab I.6 projection hold (5 min) always ends in windup against stiction and is stopped by the stall
  watchdog after about a minute; that behaviour is the result (see the report, Figure 14).
- Runs invalidated by motor stops are listed in `NOTE_INVALID_RUNS.md` inside the affected result folders.
- The motor (or its driver) stops responding after a few minutes of high current, typically at reversals or
  at full PWM at standstill, and recovers after a short pause. If `check` fails, wait a minute and try again.
