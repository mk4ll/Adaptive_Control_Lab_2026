"""
Identified first-order-plus-dead-time model of the motor pair (Lab I.1, used by all later labs):

    tau * d(omega)/dt = -omega + K * (u(t - Td) - u0)     (u outside the dead zone [-u0, u0])
or  d(omega)/dt = -a*omega + b*u    with  a = 1/tau,  b = a*K

plus stick-slip friction: from standstill the shaft only starts when |u| > ub (breakaway),
and a moving shaft sticks again when |u| < us (stop threshold), so ub > us gives hysteresis.

Saved as results/<rig|sim>/model.json.
"""
import json
from dataclasses import asdict, dataclass

import numpy as np

from lab import config


@dataclass
class MotorModel:
    K_pos: float     # steady-state gain for u > 0   [rad/s per PWM]
    K_neg: float     # steady-state gain for u < 0
    u0_pos: float    # dead zone for u > 0  [PWM]
    u0_neg: float    # dead zone for u < 0  (positive number)
    tau_pos: float   # time constant for u > 0  [s]
    tau_neg: float   # time constant for u < 0
    Td: float = 0.0  # dead time (backlash + static friction) [s]
    ub_pos: float = 0.0   # breakaway PWM from standstill, u > 0
    ub_neg: float = 0.0   # breakaway PWM from standstill, u < 0 (positive number)
    us_pos: float = 0.0   # a moving shaft sticks when u drops below this, u > 0
    us_neg: float = 0.0   # same for u < 0 (positive number)

    # ----- averaged linear model used for control design -----
    @property
    def K(self):
        return 0.5 * (self.K_pos + self.K_neg)

    @property
    def tau(self):
        return 0.5 * (self.tau_pos + self.tau_neg)

    @property
    def a(self):
        return 1.0 / self.tau

    @property
    def b(self):
        return self.a * self.K

    @property
    def omega_max(self):
        """Largest reachable speed: the scale used to normalise signals in the adaptive labs."""
        return min(self.K_pos * (config.U_MAX - self.u0_pos), self.K_neg * (config.U_MAX - self.u0_neg))

    @property
    def b_n(self):
        """Input gain of the normalised plant  dy/dt = -a*y + b_n*u_n  (y = omega/omega_max, u_n = u/U_MAX)."""
        return self.b * config.U_MAX / self.omega_max

    def steady_state(self, u):
        """omega_ss for a constant PWM u (with dead zone)."""
        u = np.asarray(u, dtype=float)
        pos = self.K_pos * np.maximum(u - self.u0_pos, 0)
        neg = self.K_neg * np.minimum(u + self.u0_neg, 0)
        return pos + neg

    def simulate(self, t, u, omega0=0.0):
        """Model response to a recorded input sequence u(t), with dead time and stick-slip."""
        omega = np.zeros(len(t))
        omega[0] = omega0
        delay = int(round(self.Td / config.TS))
        u_d = np.concatenate([np.full(delay, u[0]), u])[:len(u)]     # u(t - Td)
        moving = abs(omega0) > 0
        for k in range(1, len(t)):
            uk = u_d[k - 1]
            if not moving:
                moving = uk > self.ub_pos or uk < -self.ub_neg          # break away
            elif -self.us_neg < uk < self.us_pos and abs(omega[k - 1]) < 0.1 * self.omega_max:
                moving = False                                          # stick
            if not moving:
                omega[k] = 0.0
                continue
            tau = self.tau_pos if uk >= 0 else self.tau_neg
            omega[k] = omega[k - 1] + (t[k] - t[k - 1]) * (self.steady_state(uk) - omega[k - 1]) / tau
        return omega


def model_path(sim):
    return config.RESULTS_DIR / ("sim" if sim else "rig") / "model.json"


def save_model(model, sim):
    path = model_path(sim)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(model), indent=2))
    return path


def load_model(sim):
    path = model_path(sim)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run Lab I.1 first:  python run.py lab1{' --sim' if sim else ''}")
    return MotorModel(**json.loads(path.read_text()))
