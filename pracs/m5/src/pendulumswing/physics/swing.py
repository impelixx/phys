"""
Swing integration.

The equation of motion φ̈ = f(φ, φ̇) is integrated as a first-order system
with a high-order adaptive Runge–Kutta solver (no small-angle approximation).
Turning points are located exactly as events φ̇ = 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .rod import Rod

DEFAULT_SAMPLES_PER_SECOND = 200
_RELATIVE_TOLERANCE = 10 ** (-10)
_ABSOLUTE_TOLERANCE = 10 ** (-12)


@dataclass(frozen=True, slots=True)
class SwingResult:
    """Sampled swing plus the exact turning-point times."""

    rod: Rod
    times: np.ndarray
    angle: np.ndarray
    angular_velocity: np.ndarray
    turning_times: np.ndarray
    turning_angles: np.ndarray

    @property
    def amplitude(self) -> float:
        return float(abs(self.angle[0]))

    @property
    def potential_energy(self) -> np.ndarray:
        return self.rod.potential_energy(self.angle)

    @property
    def kinetic_energy(self) -> np.ndarray:
        return self.rod.kinetic_energy(self.angular_velocity)

    @property
    def total_energy(self) -> np.ndarray:
        return self.potential_energy + self.kinetic_energy

    @property
    def period(self) -> float | None:
        """Mean period over all half-swings, s; None before the first full swing."""
        if self.turning_times.size < 3:
            return None
        half_swings = self.turning_times.size - 1
        return float(2 * (self.turning_times[-1] - self.turning_times[0]) / half_swings)

    @property
    def energy_drift(self) -> float:
        """Largest relative deviation of the total energy from its initial value."""
        initial = self.total_energy[0]
        if initial == 0:
            return 0.0
        return float(np.max(np.abs(self.total_energy - initial)) / initial)


def _rhs(rod: Rod):  # noqa: ANN202 (solver callback)
    def rhs(_time: float, state: np.ndarray) -> tuple[float, float]:
        return state[1], rod.angular_acceleration(state[0], state[1])

    return rhs


def simulate_swing(
    rod: Rod,
    amplitude_degrees: float,
    duration: float,
    samples_per_second: int = DEFAULT_SAMPLES_PER_SECOND,
) -> SwingResult:
    """Release the rod at rest from `amplitude_degrees` and follow it for `duration` s."""

    def turns(_time: float, state: np.ndarray) -> float:
        return state[1]

    solution = solve_ivp(
        _rhs(rod),
        (0.0, duration),
        (math.radians(amplitude_degrees), 0.0),
        method="DOP853",
        rtol=_RELATIVE_TOLERANCE,
        atol=_ABSOLUTE_TOLERANCE,
        events=turns,
        dense_output=True,
    )
    if not solution.success:
        message = f"swing integration failed: {solution.message}"
        raise RuntimeError(message)

    # The release itself is a turning point; the solver may or may not report
    # it, so drop near-zero events and prepend the release explicitly.
    events = solution.t_events[0]
    turning_times = np.concatenate(([0.0], events[events > 10 ** (-9)]))
    turning_angles = solution.sol(turning_times)[0]

    count = max(2, round(duration * samples_per_second) + 1)
    times = np.linspace(0.0, duration, count)
    angle, angular_velocity = solution.sol(times)

    return SwingResult(
        rod=rod,
        times=times,
        angle=angle,
        angular_velocity=angular_velocity,
        turning_times=turning_times,
        turning_angles=turning_angles,
    )


def swing_period(rod: Rod, amplitude_degrees: float) -> float:
    """Frictionless period at a given amplitude: twice the time to the far turning point."""
    free = Rod(mass=rod.mass, length=rod.length)

    def far_turn(_time: float, state: np.ndarray) -> float:
        return state[1]

    far_turn.terminal = True  # type: ignore[attr-defined]
    far_turn.direction = 1  # type: ignore[attr-defined]

    # Near 180° the period grows without bound; 40 small-angle periods is ample.
    horizon = 40 * 2 * math.pi / free.natural_frequency
    solution = solve_ivp(
        _rhs(free),
        (0.0, horizon),
        (math.radians(amplitude_degrees), 0.0),
        method="DOP853",
        rtol=_RELATIVE_TOLERANCE,
        atol=_ABSOLUTE_TOLERANCE,
        events=far_turn,
    )
    if not solution.t_events[0].size:
        message = f"no turning point within {horizon:.1f} s"
        raise RuntimeError(message)
    return float(2 * solution.t_events[0][0])
