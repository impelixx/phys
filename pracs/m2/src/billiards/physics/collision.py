"""
Collision of a smooth ball with another ball or with a rigid wall on a frictionless table.

Before and after the impact the balls fly freely, so only the contact phase is
integrated: Newton's second law for both balls under the contact force, with
an adaptive Runge–Kutta solver, from the first touch until the balls separate
(event δ = 0, decreasing).

Geometry: the touch happens at t = 0 with ball 2 centred at the origin. The
impact parameter b is measured across the relative velocity v₁ - v₂ in units
of the touching distance 2R: b = 0 is a head-on impact, b → 1 a grazing one.

A wall is an infinitely heavy plane through the origin; ball 1 touches it at
t = 0 and b = sin α is the sine of the angle of incidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .contact import ContactModel
from .theory import (
    contact_duration,
    elastic_velocities,
    max_compression,
    reduced_mass,
    wall_reflection,
)

CONTACT_SAMPLES = 400
FREE_SAMPLES = 120
FREE_FLIGHT_DIAMETERS = 3.0
_RELATIVE_TOLERANCE = 10 ** (-11)
_SOLVER_STEPS_PER_CONTACT = 200
_HORIZON_CONTACTS = 20


@dataclass(frozen=True, slots=True)
class CollisionSetup:
    """Masses, common radius, incoming velocities and the impact parameter; or a wall."""

    mass1: float
    mass2: float
    radius: float
    velocity1: np.ndarray
    velocity2: np.ndarray
    impact: float = 0.0
    wall: bool = False

    @property
    def relative_velocity(self) -> np.ndarray:
        if self.wall:
            return np.asarray(self.velocity1, dtype=float)
        return np.asarray(self.velocity1, dtype=float) - np.asarray(self.velocity2, dtype=float)

    @property
    def touch_normal(self) -> np.ndarray:
        """Unit vector from ball 2 (or the wall) to ball 1 at the first touch."""
        relative = self.relative_velocity
        along = relative / np.linalg.norm(relative)
        across = np.array([-along[1], along[0]])
        return -math.sqrt(1 - self.impact**2) * along + self.impact * across

    @property
    def approach_speed(self) -> float:
        """Normal component of the relative velocity at the first touch, m/s."""
        return float(-np.dot(self.relative_velocity, self.touch_normal))

    @property
    def touch_distance(self) -> float:
        """Centre-to-centre (or centre-to-wall) distance at the first touch, m."""
        return self.radius if self.wall else 2 * self.radius

    @property
    def effective_mass(self) -> float:
        """Mass of the relative motion: the reduced mass, or ball 1 against a wall."""
        return self.mass1 if self.wall else reduced_mass(self.mass1, self.mass2)

    def conservation_velocities(self) -> tuple[np.ndarray, np.ndarray]:
        """Outgoing velocities of an instantaneous elastic impact."""
        velocity1 = np.asarray(self.velocity1, dtype=float)
        if self.wall:
            return wall_reflection(velocity1, self.touch_normal), np.zeros(2)
        velocity2 = np.asarray(self.velocity2, dtype=float)
        return elastic_velocities(self.mass1, self.mass2, velocity1, velocity2, self.touch_normal)


@dataclass(frozen=True, slots=True)
class CollisionResult:
    """
    Contact phase in detail plus the whole run for drawing.

    `times`, `position1`, `position2` cover the free approach, the contact and
    the free departure; `contact_*` arrays sample the contact phase only.
    """

    setup: CollisionSetup
    contact: ContactModel
    times: np.ndarray
    position1: np.ndarray
    position2: np.ndarray
    contact_times: np.ndarray
    compression: np.ndarray
    force: np.ndarray
    kinetic_energy: np.ndarray
    elastic_energy: np.ndarray
    momentum: np.ndarray
    velocity1_after: np.ndarray
    velocity2_after: np.ndarray

    @property
    def contact_duration(self) -> float:
        return float(self.contact_times[-1])

    @property
    def max_compression(self) -> float:
        return float(self.compression.max())

    @property
    def max_force(self) -> float:
        return float(self.force.max())

    @property
    def total_energy(self) -> np.ndarray:
        return self.kinetic_energy + self.elastic_energy

    @property
    def separation_angle(self) -> float | None:
        """Angle between outgoing velocities, degrees; None if a ball stops."""
        first = np.linalg.norm(self.velocity1_after)
        second = np.linalg.norm(self.velocity2_after)
        scale = max(first, second)
        if min(first, second) < 10 ** (-6) * scale:
            return None
        cosine = np.dot(self.velocity1_after, self.velocity2_after) / (first * second)
        return math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))


def simulate_collision(setup: CollisionSetup, contact: ContactModel) -> CollisionResult:
    """Integrate the impact; raises ValueError if the bodies never meet."""
    velocity1 = np.asarray(setup.velocity1, dtype=float)
    velocity2 = np.asarray(setup.velocity2, dtype=float)
    if setup.wall and np.any(velocity2 != 0):
        message = "a wall cannot move"
        raise ValueError(message)
    if np.linalg.norm(setup.relative_velocity) == 0:
        message = "balls move together and never collide"
        raise ValueError(message)
    if not 0 <= setup.impact < 1:
        message = "impact parameter must be in [0, 1) for the balls to touch"
        raise ValueError(message)

    reach = setup.touch_distance
    normal = setup.touch_normal
    mass = setup.effective_mass
    speed = setup.approach_speed
    if max_compression(contact, mass, speed) >= setup.radius:
        message = "contact is too soft: the balls would squash past half a radius"
        raise ValueError(message)

    # A wall never moves: zero inverse mass keeps it in place.
    inverse_masses = np.array(
        [1 / setup.mass1, 1 / setup.mass1] + [0.0 if setup.wall else 1 / setup.mass2] * 2,
    )

    def depth_and_direction(state: np.ndarray) -> tuple[float, np.ndarray]:
        if setup.wall:
            return reach - float(np.dot(state[0:2], normal)), normal
        offset = state[0:2] - state[2:4]
        distance = math.hypot(offset[0], offset[1])
        return reach - distance, offset / distance

    def rhs(_time: float, state: np.ndarray) -> np.ndarray:
        depth, direction = depth_and_direction(state)
        push = contact.force(depth) * direction
        forces = np.concatenate((push, -push))
        return np.concatenate((state[4:8], forces * inverse_masses))

    def separates(_time: float, state: np.ndarray) -> float:
        return depth_and_direction(state)[0]

    separates.terminal = True  # type: ignore[attr-defined]
    separates.direction = -1  # type: ignore[attr-defined]

    expected = contact_duration(contact, mass, speed)
    start = np.concatenate((reach * normal, (0.0, 0.0), velocity1, velocity2))
    solution = solve_ivp(
        rhs,
        (0.0, _HORIZON_CONTACTS * expected),
        start,
        method="DOP853",
        rtol=_RELATIVE_TOLERANCE,
        atol=_RELATIVE_TOLERANCE * reach * 10 ** (-3),
        max_step=expected / _SOLVER_STEPS_PER_CONTACT,
        events=separates,
        dense_output=True,
    )
    if not solution.success or not solution.t_events[0].size:
        message = f"contact integration failed: {solution.message}"
        raise RuntimeError(message)

    duration = float(solution.t_events[0][0])
    end = solution.y_events[0][0]
    contact_times = np.linspace(0.0, duration, CONTACT_SAMPLES)
    states = solution.sol(contact_times)
    states[:, -1] = end

    if setup.wall:
        distance = normal[0] * states[0] + normal[1] * states[1]
    else:
        distance = np.hypot(states[0] - states[2], states[1] - states[3])
    compression = np.maximum(reach - distance, 0.0)
    kinetic = (
        setup.mass1 * (states[4] ** 2 + states[5] ** 2)
        + setup.mass2 * (states[6] ** 2 + states[7] ** 2)
    ) / 2
    momentum = np.stack(
        (
            setup.mass1 * states[4] + setup.mass2 * states[6],
            setup.mass1 * states[5] + setup.mass2 * states[7],
        ),
        axis=1,
    )

    velocity1_after = end[4:6]
    velocity2_after = end[6:8]
    fastest = max(
        np.linalg.norm(velocity1),
        np.linalg.norm(velocity2),
        np.linalg.norm(velocity1_after),
        np.linalg.norm(velocity2_after),
    )
    free_time = FREE_FLIGHT_DIAMETERS * 2 * setup.radius / fastest

    before = np.linspace(-free_time, 0.0, FREE_SAMPLES, endpoint=False)
    after = np.linspace(0.0, free_time, FREE_SAMPLES + 1)[1:]
    times = np.concatenate((before, contact_times, duration + after))
    position1 = np.concatenate(
        (
            start[0:2] + np.outer(before, velocity1),
            states[0:2].T,
            end[0:2] + np.outer(after, velocity1_after),
        )
    )
    position2 = np.concatenate(
        (
            start[2:4] + np.outer(before, velocity2),
            states[2:4].T,
            end[2:4] + np.outer(after, velocity2_after),
        )
    )

    return CollisionResult(
        setup=setup,
        contact=contact,
        times=times,
        position1=position1,
        position2=position2,
        contact_times=contact_times,
        compression=compression,
        force=contact.force(compression),
        kinetic_energy=kinetic,
        elastic_energy=contact.energy(compression),
        momentum=momentum,
        velocity1_after=velocity1_after,
        velocity2_after=velocity2_after,
    )
