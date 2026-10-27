"""
Closed-form references.

- small-angle period T₀ = 2π √(2L / 3g);
- exact frictionless period T = 4 K(m) / ω₀ with m = sin²(φ₀/2);
- linearised damped motion φ̈ + 2γω₀ φ̇ + ω₀² φ = 0 in all three regimes.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import ellipk

from .rod import Rod

_CRITICAL_BAND = 10 ** (-9)


def small_angle_period(rod: Rod) -> float:
    return 2 * math.pi / rod.natural_frequency


def exact_period(rod: Rod, amplitude_degrees: float) -> float:
    """Frictionless period at any amplitude below 180°, via the elliptic integral K."""
    parameter = math.sin(math.radians(amplitude_degrees) / 2) ** 2
    return float(4 * ellipk(parameter) / rod.natural_frequency)


def damped_period(rod: Rod) -> float | None:
    """2π / ω_d with ω_d = ω₀ √(1 - γ²); None when the rod does not oscillate."""
    gamma = rod.damping_ratio
    if gamma >= 1:
        return None
    return 2 * math.pi / (rod.natural_frequency * math.sqrt(1 - gamma**2))


def linear_angle(rod: Rod, amplitude_degrees: float, times: np.ndarray) -> np.ndarray:
    """φ(t) of the linearised equation for release at rest from the amplitude, rad."""
    angle = math.radians(amplitude_degrees)
    omega = rod.natural_frequency
    gamma = rod.damping_ratio
    decay = gamma * omega

    if abs(gamma - 1) < _CRITICAL_BAND:
        return angle * (1 + decay * times) * np.exp(-decay * times)
    if gamma < 1:
        damped = omega * math.sqrt(1 - gamma**2)
        return (
            angle
            * np.exp(-decay * times)
            * (np.cos(damped * times) + decay / damped * np.sin(damped * times))
        )
    spread = omega * math.sqrt(gamma**2 - 1)
    slow, fast = -decay + spread, -decay - spread
    return angle * (fast * np.exp(slow * times) - slow * np.exp(fast * times)) / (fast - slow)
