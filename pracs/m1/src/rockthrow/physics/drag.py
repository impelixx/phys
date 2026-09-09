"""
Air resistance models.

Each model returns the drag part of the acceleration; gravity is added by the
integrator. The `c` coefficient is the drag-to-mass ratio k/m from the lab
statement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

GRAVITY = 9.81


class DragModel(Protocol):
    """Velocity-dependent part of the acceleration."""

    def acceleration(self, velocity: np.ndarray) -> np.ndarray:
        """Return drag acceleration for a velocity vector, m/s^2."""
        ...


@dataclass(frozen=True, slots=True)
class LinearDrag:
    """Viscous resistance F ~ v."""

    c: float

    @staticmethod
    def label() -> str:
        return "вязкое (F ∼ v)"

    def acceleration(self, velocity: np.ndarray) -> np.ndarray:
        return -self.c * velocity


@dataclass(frozen=True, slots=True)
class QuadraticDrag:
    """Frontal resistance F ~ v^2, directed against the motion."""

    c: float

    @staticmethod
    def label() -> str:
        return "лобовое (F ∼ v²)"

    def acceleration(self, velocity: np.ndarray) -> np.ndarray:
        return -self.c * velocity * np.abs(velocity)


def total_acceleration(drag: DragModel, velocity: np.ndarray) -> np.ndarray:
    """Drag acceleration plus gravity, per axis: (a_x, a_y), m/s^2."""
    return drag.acceleration(velocity) + np.array([0.0, -GRAVITY])
