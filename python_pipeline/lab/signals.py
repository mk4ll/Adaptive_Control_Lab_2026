"""
Reference / input signals. Every signal is a function  f(t, sample) -> value.
The sample argument is only used by from_pot (reference from the potentiometer).
"""
import numpy as np


def constant(value):
    return lambda t, s=None: value


def step(level, t0=1.0, base=0.0):
    """base until t0, then level."""
    return lambda t, s=None: level if t >= t0 else base


def staircase(levels, hold):
    """Cycle through `levels`, holding each for `hold` seconds."""
    return lambda t, s=None: levels[int(t // hold) % len(levels)]


def square(amp, period, offset=0.0):
    return lambda t, s=None: offset + (amp if (t % period) < period / 2 else -amp)


def sine(amp, period, offset=0.0):
    return lambda t, s=None: offset + amp * np.sin(2 * np.pi * t / period)


def triangle(amp, period):
    """Ramps up and down between -amp and +amp (used to verify the model with ramps)."""
    def f(t, s=None):
        x = (t / period) % 1.0
        return amp * (4 * x - 1 if x < 0.5 else 3 - 4 * x)
    return f


def from_pot(low, high):
    """Reference set by hand with the command potentiometer on the Arduino (pin A1)."""
    return lambda t, s: low + (high - low) * s.pot


def random_disturbance(amp, seed=0, hold=0.5):
    """Piecewise-constant random disturbance in [-amp, amp], new value every `hold` s."""
    values = np.random.default_rng(seed).uniform(-amp, amp, 100000)
    return lambda t: values[int(t // hold) % len(values)]
