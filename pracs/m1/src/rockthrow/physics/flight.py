"""
Ballistic flight integration.

The flight is a first-order ODE for the velocity vector integrated with an
adaptive Runge–Kutta solver, positions follow by quadrature. Integration stops
at ground contact (y = 0, descending).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .drag import GRAVITY, DragModel, total_acceleration

DEFAULT_SAMPLES_PER_SECOND = 256
_MAX_SOLVER_STEP = 0.05
_RELATIVE_TOLERANCE = 10 ** (-9)
_ABSOLUTE_TOLERANCE = 10 ** (-12)


@dataclass(frozen=True, slots=True)
class FlightResult:
    """Sampled flight: positions and velocities at evenly spaced times."""

    times: np.ndarray
    x: np.ndarray
    y: np.ndarray
    vx: np.ndarray
    vy: np.ndarray

    @property
    def flight_time(self) -> float:
        return float(self.times[-1])

    @property
    def flight_distance(self) -> float:
        return float(self.x[-1])

    @property
    def max_height(self) -> float:
        return float(self.y.max())

    @property
    def apex_index(self) -> int:
        return int(np.argmax(self.y))

    @property
    def speed(self) -> np.ndarray:
        return np.hypot(self.vx, self.vy)


def simulate_flight(
    velocity: float,
    angle_degrees: float,
    drag: DragModel,
    samples_per_second: int = DEFAULT_SAMPLES_PER_SECOND,
) -> FlightResult:
    """Simulate a stone launched with `velocity` m/s at `angle_degrees` above horizon."""
    angle = np.radians(angle_degrees)
    v0x = velocity * np.cos(angle)
    v0y = velocity * np.sin(angle)

    def rhs(_time: float, state: np.ndarray) -> tuple[float, float, float, float]:
        ax, ay = total_acceleration(drag, state[2:])
        return state[2], state[3], float(ax), float(ay)

    def hits_ground(_time: float, state: np.ndarray) -> float:
        return state[1]

    hits_ground.terminal = True  # type: ignore[attr-defined]
    hits_ground.direction = -1  # type: ignore[attr-defined]

    # Generous window: the no-drag flight time plus a wide margin for drag cases.
    horizon = 2 * v0y / GRAVITY + 5.0
    solution = solve_ivp(
        rhs,
        (0.0, horizon),
        (0.0, 0.0, v0x, v0y),
        method="RK45",
        rtol=_RELATIVE_TOLERANCE,
        atol=_ABSOLUTE_TOLERANCE,
        max_step=_MAX_SOLVER_STEP,
        events=hits_ground,
        dense_output=True,
    )
    if not solution.success:
        message = f"flight integration failed: {solution.message}"
        raise RuntimeError(message)

    if solution.t_events[0].size:
        landing_time = float(solution.t_events[0][0])
    else:  # pragma: no cover - the ground event always fires for upward launches
        landing_time = float(solution.t[-1])

    count = max(2, round(landing_time * samples_per_second) + 1)
    times = np.linspace(0.0, landing_time, count)
    states = solution.sol(times)
    # Dense-output interpolation leaves the landing sample a hair below zero;
    # y is non-negative analytically over [0, landing_time], so clamp the dust.
    y = np.maximum(states[1], 0.0)

    return FlightResult(
        times=times,
        x=states[0],
        y=y,
        vx=states[2],
        vy=states[3],
    )
