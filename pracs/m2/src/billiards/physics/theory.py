"""
Closed-form references.

- Conservation laws: for smooth balls the impulse acts along the line of centres
  n, so momentum and kinetic energy fix the outgoing velocities
  v₁′ = v₁ - 2m₂/(m₁+m₂) ((v₁-v₂)·n) n,  v₂′ = v₂ + 2m₁/(m₁+m₂) ((v₁-v₂)·n) n.
  A wall is the limit m₂ → ∞: the ball is mirrored, v′ = v - 2(v·n) n.
- Contact dynamics of F = k δⁿ for the relative coordinate with reduced mass μ
  and approach speed v: the energy integral μv²/2 = k δₘⁿ⁺¹/(n+1) gives the
  deepest compression, and the contact lasts
  τ = 2 ∫₀^δₘ dδ / √(v² - 2kδⁿ⁺¹/(μ(n+1))) = 2δₘ/v · B(1/(n+1), 1/2) / (n+1).
  For Hooke's law (n = 1) this is the half period π √(μ/k).
"""

from __future__ import annotations

import numpy as np
from scipy.special import beta

from .contact import ContactModel


def reduced_mass(mass1: float, mass2: float) -> float:
    return mass1 * mass2 / (mass1 + mass2)


def elastic_velocities(
    mass1: float,
    mass2: float,
    velocity1: np.ndarray,
    velocity2: np.ndarray,
    normal: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Outgoing velocities of an instantaneous elastic impact along unit `normal`."""
    approach = float(np.dot(velocity1 - velocity2, normal))
    total = mass1 + mass2
    return (
        velocity1 - 2 * mass2 / total * approach * normal,
        velocity2 + 2 * mass1 / total * approach * normal,
    )


def wall_reflection(velocity: np.ndarray, normal: np.ndarray) -> np.ndarray:
    """Mirror reflection off a rigid wall with unit `normal`."""
    return velocity - 2 * float(np.dot(velocity, normal)) * normal


def max_compression(contact: ContactModel, mass: float, speed: float) -> float:
    """Deepest mutual compression δₘ for reduced mass `mass` and approach `speed`, m."""
    power = contact.exponent + 1
    return (power * mass * speed**2 / (2 * contact.stiffness)) ** (1 / power)


def contact_duration(contact: ContactModel, mass: float, speed: float) -> float:
    """Time the balls stay in contact, s."""
    power = contact.exponent + 1
    return 2 * max_compression(contact, mass, speed) / speed * beta(1 / power, 0.5) / power
