"""
Physical pendulum: a uniform rod hung by one end.

Viscous friction acts on every rod element: dF = -β ω r dr, so the friction
torque is M = -β φ̇ L³ / 3 (β is the resistance per unit rod length).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

GRAVITY = 9.81


@dataclass(frozen=True, slots=True)
class Rod:
    """Uniform rod of `mass` kg and `length` m, pivoted at one end."""

    mass: float
    length: float
    friction: float = 0.0

    @property
    def moment_of_inertia(self) -> float:
        """I = m L² / 3 about the pivot, kg·m²."""
        return self.mass * self.length**2 / 3

    @property
    def natural_frequency(self) -> float:
        """ω₀ = √(m g L / 2I) = √(3g / 2L), rad/s."""
        return math.sqrt(self.mass * GRAVITY * self.length / (2 * self.moment_of_inertia))

    @property
    def damping_rate(self) -> float:
        """2γω₀ = β L³ / 3I = β L / m, 1/s."""
        return self.friction * self.length**3 / (3 * self.moment_of_inertia)

    @property
    def damping_ratio(self) -> float:
        """γ: below one the rod still oscillates, above it creeps to rest."""
        return self.damping_rate / (2 * self.natural_frequency)

    def angular_acceleration(self, angle: float, angular_velocity: float) -> float:
        """φ̈ from the torques of gravity and friction about the pivot, rad/s²."""
        gravity_torque = -self.mass * GRAVITY * self.length / 2 * math.sin(angle)
        friction_torque = -self.friction * self.length**3 / 3 * angular_velocity
        return (gravity_torque + friction_torque) / self.moment_of_inertia

    def potential_energy(self, angle: np.ndarray) -> np.ndarray:
        """Centre of mass lift: m g L/2 (1 - cos φ), J."""
        return self.mass * GRAVITY * self.length / 2 * (1 - np.cos(angle))

    def kinetic_energy(self, angular_velocity: np.ndarray) -> np.ndarray:
        """Rotation about the pivot: I φ̇² / 2, J."""
        return self.moment_of_inertia * angular_velocity**2 / 2
