"""
Connection to the motor rig.

Two interchangeable classes with the same methods:
    Rig      - the real Arduino over USB serial
    SimRig   - a simulated motor pair, used for dry runs (python run.py lab3 --sim)

Usage pattern (done for you by lab.runner.run_experiment):
    rig.start()                 # Arduino starts streaming samples, angle reset to 0
    s = rig.read()              # blocks until the next sample (every TS seconds)
    rig.write(u)                # PWM command, applied immediately
    rig.stop()                  # motor off, streaming stops
"""
import time
from dataclasses import dataclass

import numpy as np

from lab import config


@dataclass
class Sample:
    t: float       # time since rig.start() [s]
    theta: float   # angle [rad]
    omega: float   # angular velocity [rad/s]
    pot: float     # command potentiometer, 0..1
    u: float       # PWM the Arduino is currently applying


class Rig:
    """The real hardware (Arduino running firmware/motor_io)."""

    def __init__(self, port=config.PORT, baud=config.BAUD):
        import serial
        if port == "auto":
            port = find_arduino_port()
        print(f"[rig] connecting to {port} @ {baud} baud")
        self.ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(2.0)                    # most Arduinos reboot when the port opens
        self.ser.reset_input_buffer()
        self.late_samples = 0              # samples that were already waiting -> PC fell behind

    def start(self):
        self.ser.write(b"B\n")
        self.ser.reset_input_buffer()
        self.late_samples = 0
        self._t_offset = 0.0
        self._t_last_raw = 0

    def read(self) -> Sample:
        for _ in range(50):                # skip partial / garbage lines
            line = self.ser.readline().decode(errors="ignore").strip()
            parts = line.split(",")
            if len(parts) != 5:
                if line == "":
                    raise TimeoutError("No data from Arduino. Is motor_io.ino flashed and the baud rate right?")
                continue
            try:
                t_us, theta, omega, pot, u = (float(p) for p in parts)
            except ValueError:
                continue
            if t_us < self._t_last_raw:   # micros() wrapped around (every ~71 min)
                self._t_offset += 2**32 * 1e-6
            self._t_last_raw = t_us
            if self.ser.in_waiting > 40:   # more than ~one line queued: we are running late
                self.late_samples += 1
            return Sample(t_us * 1e-6 + self._t_offset, theta, omega, pot, u)
        raise RuntimeError("Could not parse data from Arduino")

    def write(self, u):
        self.ser.write(f"{int(round(u))}\n".encode())

    def stop(self):
        self.ser.write(b"0\nE\n")
        self.ser.flush()

    def ask_user(self, message):
        """Manual step (e.g. turn the load potentiometer). Blocks until Enter."""
        input(f"\n>>> {message}\n    Press Enter when ready... ")

    def close(self):
        self.stop()
        self.ser.close()


def find_arduino_port():
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    for p in ports:
        text = f"{p.device} {p.description} {p.manufacturer}".lower()
        if any(k in text for k in ("arduino", "acm", "usbserial", "ch340", "usb serial", "wch")):
            return p.device
    names = [p.device for p in ports]
    raise RuntimeError(f"No Arduino found (ports: {names}). Set PORT in lab/config.py.")


class SimRig:
    """
    Simulated coupled motors, tuned to the lab bench measured on 2026-10-14 (Lab I.1):
      - first-order mechanics  d(omega)/dt = -a*omega + a*K*u   (tau ~ 0.12 s, ~4.7 rad/s at full PWM)
      - dead time ~0.1 s (gear/coupling backlash), small actuator lag
      - stick-slip friction: from rest the shaft starts only above the breakaway PWM,
        a moving shaft sticks again below the stop PWM (asymmetric, like the real rig)
      - encoder quantisation (8600 counts/rev) + the same velocity filter as the firmware
    `load` (0..1) mimics the potentiometer on the second motor: more load, more damping.
    """

    def __init__(self, a=8.0, K=0.0185, K_neg=0.0195, breakaway=(110.0, 65.0), stop=(35.0, 35.0),
                 dead_time=0.10, tau_e=0.02, counts_per_rev=8600, seed=0):
        self.a0, self.K, self.K_neg, self.tau_e = a, K, K_neg, tau_e
        self.ub, self.us = breakaway, stop
        self.delay = int(round(dead_time / config.TS))
        self.q = 2 * np.pi / counts_per_rev
        self.rng = np.random.default_rng(seed)
        self.load = 0.0
        self.late_samples = 0
        self.omega = 0.0
        self.v = 0.0
        self.moving = False
        self.pot = 0.5
        self._reset()

    def _reset(self):
        self.t = 0.0
        self.theta = 0.0
        self.theta_meas_prev = 0.0
        self.omega_f = 0.0
        self.u = 0.0
        self.u_queue = [0.0] * self.delay      # commands in flight (dead time)

    def start(self):
        self._reset()

    def read(self) -> Sample:
        self.u_queue.append(self.u)
        u = self.u_queue.pop(0)                # command applied Td ago
        if not self.moving:
            self.moving = u > self.ub[0] or u < -self.ub[1]
        elif -self.us[1] < u < self.us[0] and abs(self.omega) < 0.3:
            self.moving = False
        a = self.a0 * (1 + 1.5 * self.load)                    # load adds damping
        gain = (self.K if u >= 0 else self.K_neg) / (1 + 0.5 * self.load)
        n = 10
        h = config.TS / n
        for _ in range(n):
            self.v += h * (u - self.v) / self.tau_e
            if self.moving:
                self.omega += h * a * (gain * self.v - self.omega) + np.sqrt(h) * 0.02 * self.rng.standard_normal()
            else:
                self.omega = 0.0
            self.theta += h * self.omega
        self.t += config.TS
        theta_meas = np.round(self.theta / self.q) * self.q
        omega_raw = (theta_meas - self.theta_meas_prev) / config.TS
        self.theta_meas_prev = theta_meas
        self.omega_f += 0.5 * (omega_raw - self.omega_f)
        return Sample(self.t, theta_meas, self.omega_f, self.pot, self.u)

    def write(self, u):
        self.u = float(np.clip(round(u), -config.U_MAX, config.U_MAX))

    def stop(self):
        self.u = 0.0

    def ask_user(self, message):
        """In simulation the 'manual' steps are automatic. Load positions map to 0, 0.5, 1."""
        print(f"[sim] (would ask: {message})")

    def set_load(self, fraction):
        self.load = fraction

    def close(self):
        pass


def open_rig(sim=False):
    return SimRig() if sim else Rig()
