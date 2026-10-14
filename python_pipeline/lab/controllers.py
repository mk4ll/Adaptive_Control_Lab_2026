"""
Controllers. Every controller has the same interface:

    u = controller.update(sample, r, dt)    # PWM command
    controller.log                          # dict of internal signals recorded every sample
    controller.diverged()                   # True -> the runner aborts the experiment

Classical controllers (OpenLoop, P, PI) work in physical units (rad/s, PWM).

Adaptive controllers work internally with NORMALISED signals
    y = omega / y_scale,   r = r / y_scale,   u_n = u / U_MAX
so their gains are dimensionless. With y_scale = omega_max the normalised plant is
    dy/dt = -a*y + b_n*u_n          (b_n ~ a)
Logged signals ending in "_n" are normalised, "ym" is converted back to physical units.

Notation follows Ioannou & Sun / Astrom & Wittenmark:
    e = y - ym       tracking error w.r.t. the reference model
    theta            vector of adaptive parameters    (logged as p_<name>)
    w                regressor vector                 (logged as w_<name>)
"""
import numpy as np

from lab import config


class Controller:
    def __init__(self):
        self.log = {}

    def update(self, s, r, dt):
        raise NotImplementedError

    def diverged(self):
        return False


# =============================== classical =================================

class OpenLoop(Controller):
    """The reference IS the PWM input (used for identification)."""

    def update(self, s, r, dt):
        return r


class PController(Controller):
    """u = Kp * (r - omega)"""

    def __init__(self, Kp):
        super().__init__()
        self.Kp = Kp

    def update(self, s, r, dt):
        return self.Kp * (r - s.omega)


class PIController(Controller):
    """u = Kp*e + Ki*integral(e), with anti-windup (integration stops while saturated)."""

    def __init__(self, Kp, Ki):
        super().__init__()
        self.Kp, self.Ki = Kp, Ki
        self.integral = 0.0

    def update(self, s, r, dt):
        e = r - s.omega
        u = self.Kp * e + self.Ki * self.integral
        if abs(u) < config.U_MAX or np.sign(e) != np.sign(u):
            self.integral += e * dt
        self.log = {"integral": self.integral}
        return u


# ======================= robust adaptive-law modifications ==================

class Robust:
    """
    Modifies the nominal adaptive law  theta_dot = f  to keep parameters bounded
    in the presence of noise, disturbances and unmodelled dynamics.

      none        theta_dot = f
      deadzone    theta_dot = f        if |e| > e0,  else 0
      sigma       theta_dot = f - sigma*gamma*(theta - theta0)        (sigma-modification)
      emod        theta_dot = f - sigma*gamma*|e|*(theta - theta0)    (e-modification)
      projection  theta_dot = f, but theta is kept in the box |theta_i| <= bound

    theta0 is the initial (nominal) estimate; theta0 = 0 gives the textbook leakage.
    """

    def __init__(self, method="none", e0=config.DEADZONE_E0, sigma=config.SIGMA, bound=config.PROJ_BOUND):
        assert method in config.ROBUST_METHODS, method
        self.method, self.e0, self.sigma, self.bound = method, e0, sigma, bound

    def theta_dot(self, f, theta, theta0, gamma, e):
        if self.method == "deadzone" and abs(e) < self.e0:
            return np.zeros_like(f)
        if self.method == "sigma":
            return f - self.sigma * gamma * (theta - theta0)
        if self.method == "emod":
            return f - self.sigma * gamma * abs(e) * (theta - theta0)
        if self.method == "projection":
            pushing_out = ((theta >= self.bound) & (f > 0)) | ((theta <= -self.bound) & (f < 0))
            return np.where(pushing_out, 0.0, f)
        return f

    def clip(self, theta):
        if self.method == "projection":
            return np.clip(theta, -self.bound, self.bound)
        return theta


class AdaptiveController(Controller):
    """Common bookkeeping: normalisation, Euler integration of theta, logging, divergence check."""

    def __init__(self, y_scale, theta0, gamma, param_names, robust=None, freeze_when_saturated=True):
        super().__init__()
        self.ys = y_scale
        self.theta0 = np.array(theta0, dtype=float)
        self.theta = self.theta0.copy()
        self.gamma = np.broadcast_to(np.asarray(gamma, dtype=float), self.theta.shape).copy()
        self.param_names = param_names
        self.robust = robust or Robust("none")
        self.freeze_when_saturated = freeze_when_saturated   # avoids wind-up of the estimates
        self.param_limit = config.PARAM_LIMIT                 # |theta| above this = divergence -> abort

    def adapt(self, f, e, dt, u_n, u_of):
        """
        One Euler step of theta_dot = f (nominal law), passed through the robust modification.
        u_of(theta) gives the control the new parameters would produce: while the input is
        saturated, updates that would push it further into saturation are skipped (anti-windup).
        """
        theta_dot = self.robust.theta_dot(f, self.theta, self.theta0, self.gamma, e)
        theta_new = self.robust.clip(self.theta + dt * theta_dot)
        if self.freeze_when_saturated and abs(u_n) >= 1.0 and abs(u_of(theta_new)) > abs(u_n):
            return
        self.theta = theta_new

    def record(self, ym, e, w, w_names, u_n):
        self.log = {"ym": ym * self.ys, "e_n": e, "u_n": u_n}
        self.log.update({f"p_{n}": v for n, v in zip(self.param_names, self.theta)})
        self.log.update({f"w_{n}": v for n, v in zip(w_names, w)})

    def diverged(self):
        return not np.all(np.isfinite(self.theta)) or np.max(np.abs(self.theta)) > self.param_limit


def friction_basis(y, v0=config.FRICTION_V0):
    """Linearly parameterised uncertainty model: [offset, Coulomb friction ~ sign(velocity)]."""
    return np.array([1.0, np.tanh(y / v0)])


def friction_velocity(y, ym):
    """Velocity that drives the friction basis: desired (ym, works at standstill) or measured (y)."""
    return ym if config.FRICTION_FROM_REFERENCE else y


# ================================ Lab I.2 =================================

class MITController(AdaptiveController):
    """
    MIT rule (Astrom & Wittenmark, Example 5.2), first-order plant and reference model
        reference model:  dym/dt = -am*ym + bm*r
        control law:      u = th1*r - th2*y
        MIT rule:         dth1/dt = -gamma * [am/(s+am) r] * e
                          dth2/dt = +gamma * [am/(s+am) y] * e
    The filtered signals approximate the sensitivity derivatives de/dth.
    Ideal parameters: th1* = bm/b_n, th2* = (am - a)/b_n.
    """

    def __init__(self, am, bm, gamma, y_scale, theta0=(0.0, 0.0)):
        super().__init__(y_scale, theta0, gamma, ["th1", "th2"], freeze_when_saturated=False)
        self.am, self.bm = am, bm
        self.ym = self.rf = self.yf = 0.0

    def update(self, s, r, dt):
        y, r = s.omega / self.ys, r / self.ys
        e = y - self.ym
        th1, th2 = self.theta
        u_n = th1 * r - th2 * y
        self.adapt(self.gamma * np.array([-self.rf * e, self.yf * e]), e, dt, u_n,
                   lambda th: th[0] * r - th[1] * y)
        self.record(self.ym, e, [self.rf, self.yf], ["rf", "yf"], u_n)
        # propagate reference model and sensitivity filters
        self.ym += dt * (-self.am * self.ym + self.bm * r)
        self.rf += dt * self.am * (r - self.rf)
        self.yf += dt * self.am * (y - self.yf)
        return u_n * config.U_MAX


# ================================ Lab I.3 / I.5 ===========================

class MRACScalar(AdaptiveController):
    """
    Direct scalar MRAC, Lyapunov design (Ioannou & Sun, sec. 6.2), sign(b) = +1 known.
        plant:            dy/dt = -a*y + b*(u + uncertainty)
        reference model:  dym/dt = -am*ym + bm*r
        control law:      u = theta^T w,   w = [y, (1, tanh(y/v0)), r]
        adaptive law:     dtheta/dt = -Gamma * w * e
    Without the friction basis ("extended=False") the ideal parameters are
        k* = (a - am)/b_n,   l* = bm/b_n.
    """

    def __init__(self, am, bm, gamma, y_scale, theta0=None, extended=False, robust=None):
        self.w_names = ["y", "one", "fric", "r"] if extended else ["y", "r"]
        names = ["k", "d0", "dc", "l"] if extended else ["k", "l"]
        theta0 = np.zeros(len(names)) if theta0 is None else theta0
        super().__init__(y_scale, theta0, gamma, names, robust)
        self.am, self.bm, self.extended = am, bm, extended
        self.ym = 0.0

    def regressor(self, y, r):
        if self.extended:
            return np.concatenate([[y], friction_basis(friction_velocity(y, self.ym)), [r]])
        return np.array([y, r])

    def update(self, s, r, dt):
        y, r = s.omega / self.ys, r / self.ys
        e = y - self.ym
        w = self.regressor(y, r)
        u_n = self.theta @ w
        self.adapt(-self.gamma * w * e, e, dt, u_n, lambda th: th @ w)
        self.record(self.ym, e, w, self.w_names, u_n)
        self.ym += dt * (-self.am * self.ym + self.bm * r)
        return u_n * config.U_MAX


# ================================ Lab I.4 / I.5 ===========================

class ADIScalar(AdaptiveController):
    """
    Adaptive Dynamic Inversion (indirect / certainty-equivalence), scalar case.
        plant model:      dy/dt = theta_f^T phi(y) + b*u,   phi = [y, (1, tanh(y/v0))]
        reference model:  dym/dt = -am*ym + bm*r
        desired rate:     nu = dym/dt - ke*e
        control law:      u = (nu - theta_f^T phi) / b_hat         (inverts the estimated dynamics)
        adaptive laws:    dtheta_f/dt = Gamma * phi * e
                          db_hat/dt   = gamma_b * u * e,   b_hat >= b_min (always projected)
    Lyapunov V = e^2/2 + theta_err^T Gamma^-1 theta_err/2  ->  dV/dt = -ke*e^2.
    Ideal parameters (normalised, extended=False): theta_f* = -a,  b* = b_n.
    """

    def __init__(self, am, bm, ke, gamma, y_scale, theta0, b_min, extended=False, robust=None):
        names = ["a_hat", "d0_hat", "dc_hat", "b_hat"] if extended else ["a_hat", "b_hat"]
        super().__init__(y_scale, theta0, gamma, names, robust)
        self.w_names = ["y", "one", "fric", "u"] if extended else ["y", "u"]
        self.am, self.bm, self.ke, self.b_min, self.extended = am, bm, ke, b_min, extended
        self.ym = 0.0

    def phi(self, y):
        if self.extended:
            return np.concatenate([[y], friction_basis(friction_velocity(y, self.ym))])
        return np.array([y])

    def update(self, s, r, dt):
        y, r = s.omega / self.ys, r / self.ys
        e = y - self.ym
        phi = self.phi(y)
        theta_f, b_hat = self.theta[:-1], self.theta[-1]
        ym_dot = -self.am * self.ym + self.bm * r
        nu = ym_dot - self.ke * e
        u_n = (nu - theta_f @ phi) / b_hat
        u_applied = float(np.clip(u_n, -1, 1))
        w = np.concatenate([phi, [u_applied]])
        self.adapt(self.gamma * w * e, e, dt, u_n, lambda th: (nu - th[:-1] @ phi) / max(th[-1], self.b_min))
        self.theta[-1] = max(self.theta[-1], self.b_min)
        self.record(self.ym, e, w, self.w_names, u_n)
        self.ym += dt * ym_dot
        return u_n * config.U_MAX


# ================================ Lab I.6 =================================

class MRACVector(AdaptiveController):
    """
    Direct state-feedback MRAC for the angle (vector case), x = [theta, omega] / y_scale.
        plant:            dx/dt = A x + B (u + uncertainty),   A = [[0,1],[0,-a]],  B = [0, b_n]
        reference model:  dxm/dt = Am xm + Bm r,  Am = [[0,1],[-wn^2,-2 zeta wn]],  Bm = [0, wn^2]
        control law:      u = theta^T w,   w = [theta, omega, 1, (tanh(omega/v0)), r]
                          ("1" models a constant load torque / bias; the Coulomb-friction term
                           tanh(omega/v0) is optional because near standstill it acts like a relay)
        adaptive law:     dtheta/dt = -Gamma * w * (e^T P B0),   B0 = [0, 1]  (sign(b) = +1)
                          with Am^T P + P Am = -Q
    Ideal (no uncertainty): k1* = -wn^2/b_n, k2* = (a - 2 zeta wn)/b_n, l* = wn^2/b_n.

    u0 > 0 adds a dead-zone inverse at the output:  u_pwm = u + u0*tanh(u/2)
    (near standstill the angle loop asks for a few PWM only, which the motor dead zone would swallow).
    """

    def __init__(self, wn, zeta, gamma, y_scale, theta0=None, friction=False, robust=None, Q=None, u0=0.0):
        self.w_names = ["th", "om", "one", "fric", "r"] if friction else ["th", "om", "one", "r"]
        names = ["k1", "k2", "d0", "dc", "l"] if friction else ["k1", "k2", "d0", "l"]
        theta0 = np.zeros(len(names)) if theta0 is None else theta0
        super().__init__(y_scale, theta0, gamma, names, robust)
        self.Am = np.array([[0.0, 1.0], [-wn**2, -2 * zeta * wn]])
        self.Bm = np.array([0.0, wn**2])
        self.P = lyapunov(self.Am, np.eye(2) if Q is None else Q)
        self.friction = friction
        self.u0 = u0
        self.xm = np.zeros(2)

    def update(self, s, r, dt):
        x = np.array([s.theta, s.omega]) / self.ys
        r = r / self.ys
        e = x - self.xm
        s_err = e @ self.P[:, 1]            # e^T P B0
        basis = friction_basis(x[1]) if self.friction else [1.0]
        w = np.concatenate([x, basis, [r]])
        u_n = self.theta @ w
        self.adapt(-self.gamma * w * s_err, s_err, dt, u_n, lambda th: th @ w)
        self.record(self.xm[0], s_err, w, self.w_names, u_n)
        self.log.update({"e_theta": (x[0] - self.xm[0]) * self.ys, "omega_m": self.xm[1] * self.ys})
        self.xm = self.xm + dt * (self.Am @ self.xm + self.Bm * r)
        u = u_n * config.U_MAX
        return u + self.u0 * np.tanh(u / 2.0)


def lyapunov(A, Q):
    """Solve A^T P + P A = -Q for P."""
    n = A.shape[0]
    M = np.kron(np.eye(n), A.T) + np.kron(A.T, np.eye(n))
    P = np.linalg.solve(M, -Q.reshape(-1)).reshape(n, n)
    return 0.5 * (P + P.T)
