"""
All tunable settings in one place.

Hardware settings (pins, encoder resolution, ...) live in firmware/motor_io/motor_io.ino.
Everything here can be changed without re-flashing the Arduino.
"""
from pathlib import Path

# ---------------- serial link (must match the firmware) ----------------
PORT = "auto"          # "auto" picks the first Arduino-like port, or set e.g. "/dev/ttyACM0" / "COM3"
BAUD = 115200
TS = 0.01              # sample period [s] (firmware TS_US = 10000)
U_MAX = 255            # PWM limit

# ---------------- safety ----------------
OMEGA_LIMIT = 20.0     # |omega| above this [rad/s] aborts the experiment (lab motor: ~5 rad/s at full PWM)
PARAM_LIMIT = 20.0     # |adaptive parameter| (normalised, useful values ~1) above this = divergence -> abort
REST_TIME = 2.0        # max seconds to wait for the motor to stop between experiments
STALL_TIME = 2.0       # |u| >= 95 % PWM for this long with zero measured speed -> abort (stall / sensor loss)

# ---------------- results ----------------
ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"         # results/rig/... for hardware, results/sim/... for simulation

# ---------------- Lab I.1: identification ----------------
ID_PWM_LEVELS = [30, 50, 75, 100, 130, 160, 200, 255]   # step amplitudes, used with both signs
ID_STEP_HOLD = 5.0       # seconds each identification step is held (must be >> time constant)
ID_LOAD_POSITIONS = ["minimum", "middle", "maximum"]    # load potentiometer settings to test (manual)

# P / PI design: closed loop should be this many times faster than the open-loop motor
P_SPEEDUP = 3.0
PI_SPEEDUP = 3.0

# ---------------- Labs I.2 - I.6: adaptive control ----------------
# Adaptive controllers work with NORMALISED signals:
#   y_n = omega / omega_max,   u_n = u / U_MAX
# so the adaptation gains below are dimensionless and transfer from simulation to the rig.
REF_SPEEDUP = 2.0        # reference model pole  a_m = REF_SPEEDUP * a  (a = identified motor pole)
REF_LEVELS = [0.3, 0.6, -0.3, -0.6]   # normalised step levels (fraction of omega_max)
REF_HOLD = 5.0           # seconds per step level
SINE_AMP = 0.5           # normalised amplitude of the slow sinusoid
SINE_PERIOD = 10.0       # [s] slow sinusoid (the one the manual asks for)
FAST_SINE_PERIOD = 3.0   # [s] faster sinusoid, for comparison of the PE level
RUN_TIME = 40.0          # duration of a normal tracking experiment [s]
LONG_RUN_TIME = 600.0    # duration of the "leave it running" constant-step experiment [s]

# adaptation gains (normalised units)
MIT_GAMMA = 5.0
MIT_GAMMA_SWEEP = [1.0, 3.0, 10.0, 30.0, 100.0]      # Lab I.2 stability map
MIT_MAP_PARAM_LIMIT = 10.0   # map runs abort (= unstable) once |theta| exceeds this, to spare the gearbox
MIT_AMP_SWEEP = [0.2, 0.4, 0.7]
MRAC_GAMMA = 3.0
ADI_GAMMA = 3.0
ADI_KE = 2.0             # error feedback gain of the dynamic inversion controller [1/s]

# robust adaptive control (Labs I.5, I.6)
ROBUST_METHODS = ["none", "deadzone", "sigma", "emod", "projection"]
DEADZONE_E0 = 0.02       # no adaptation while |e| < e0 (normalised)
SIGMA = 0.01             # leakage of sigma / e-modification
PROJ_BOUND = 5.0         # projection keeps every |parameter| <= this
FRICTION_V0 = 0.1        # smoothing of the Coulomb-friction basis tanh(y / v0) (normalised velocity)
FRICTION_GAMMA_SCALE = 0.3   # offset/friction parameters adapt this much slower than the others
FRICTION_FROM_REFERENCE = True  # friction basis tanh(ym/v0) (desired velocity) instead of tanh(y/v0):
                                # non-zero at standstill, so it also helps the shaft break free
DISTURBANCE_PWM = 0.0    # amplitude of an optional random input disturbance (to provoke drift)

# Lab I.6: angle control (angle normalised by ANGLE_SCALE)
ANGLE_SCALE = 6.283185307    # 1 revolution
ANGLE_LEVELS = [3.1416, 6.2832, 0.0, -3.1416]   # [rad]
ANGLE_SINE_AMP = 3.1416      # [rad]
ANGLE_ZETA = 1.0             # reference model damping
ANGLE_WN = 1.5               # reference model natural frequency [rad/s]: slow enough that a pi step needs
                             # < omega_max (peak speed ~0.37*wn*step) and wn*Td << 1 (dead time)
ANGLE_GAMMA = 5.0            # adaptation gain of the vector MRAC
ANGLE_FRICTION_BASIS = False # also adapt a Coulomb-friction term tanh(omega/v0) (can limit-cycle, try it!)
ANGLE_DEADZONE_COMP = True   # add a dead-zone inverse (= measured stop threshold us) at the controller output
