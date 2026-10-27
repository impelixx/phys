"""
Contact force models.

Balls are smooth, so the only force between them is the elastic repulsion
along the line of centres. It depends on the mutual compression
δ = 2R - |r₁ - r₂| > 0 as F = k δⁿ: Hooke's law (n = 1) or Hertz's law (n = 3/2).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ContactModel:
    """Elastic repulsion F = k δⁿ with potential energy U = k δⁿ⁺¹ / (n + 1)."""

    stiffness: float

    @property
    def exponent(self) -> float:
        raise NotImplementedError

    def force(self, compression: np.ndarray) -> np.ndarray:
        """Repulsion at a given compression, N; zero when the balls do not touch."""
        # Clamp: the Hertz power of a negative compression is not a real number.
        return self.stiffness * np.maximum(compression, 0.0) ** self.exponent

    def energy(self, compression: np.ndarray) -> np.ndarray:
        """Elastic energy stored at a given compression, J."""
        power = self.exponent + 1
        return self.stiffness * np.maximum(compression, 0.0) ** power / power


@dataclass(frozen=True, slots=True)
class HookeContact(ContactModel):
    """Linear spring F = k δ, k in N/m."""

    @property
    def exponent(self) -> float:
        return 1.0

    @staticmethod
    def label() -> str:
        return "закон Гука (F ∼ δ)"

    @staticmethod
    def stiffness_unit() -> str:
        return "Н/м"


@dataclass(frozen=True, slots=True)
class HertzContact(ContactModel):
    """Hertzian contact of two spheres F = k δ^{3/2}, k in N/m^{3/2}."""

    @property
    def exponent(self) -> float:
        return 1.5

    @staticmethod
    def label() -> str:
        return "закон Герца (F ∼ δ³ᐟ²)"

    @staticmethod
    def stiffness_unit() -> str:
        return "Н/м³ᐟ²"
