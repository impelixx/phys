"""Pendulum physics: the rod model, swing integration and theoretical references."""

from .rod import GRAVITY, Rod
from .swing import SwingResult, simulate_swing, swing_period
from .theory import damped_period, exact_period, linear_angle, small_angle_period

__all__ = [
    "GRAVITY",
    "Rod",
    "SwingResult",
    "damped_period",
    "exact_period",
    "linear_angle",
    "simulate_swing",
    "small_angle_period",
    "swing_period",
]
