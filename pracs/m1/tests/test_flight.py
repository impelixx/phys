"""Oracle tests: closed-form references from the lab statement."""

import numpy as np
import pytest

from rockthrow.physics import FlightResult, LinearDrag, QuadraticDrag, simulate_flight

RELATIVE_ERROR = 10 ** (-3)  # 0.1%

NO_DRAG_CASES = [
    (42, 42, 5.73, 178.83),
    (69, 69, 13.13, 324.74),
    (228, 28, 21.82, 4393.13),
]

LINEAR_DRAG_CASES = [
    (42, 42, 4.2, 0.42, 5.27, 127.83),
    (69, 69, 6.9, 0.69, 11.12, 165.91),
    (228, 28, 2.28, 0.28, 16.56, 1424.79),
]


def assert_flight(result: FlightResult, expected_time: float, expected_distance: float) -> None:
    assert result.flight_time == pytest.approx(expected_time, rel=RELATIVE_ERROR)
    assert result.flight_distance == pytest.approx(expected_distance, rel=RELATIVE_ERROR)


@pytest.mark.parametrize("drag", [LinearDrag(0.0), QuadraticDrag(0.0)])
@pytest.mark.parametrize(
    ("velocity", "angle", "expected_time", "expected_distance"),
    NO_DRAG_CASES,
)
def test_no_drag(velocity, angle, expected_time, expected_distance, drag) -> None:
    """Both models degenerate to free flight when the drag rate is zero."""
    result = simulate_flight(velocity, angle, drag)
    assert_flight(result, expected_time, expected_distance)
    assert result.y.min() >= 0
    assert result.y[-1] == pytest.approx(0.0, abs=10 ** (-6))


@pytest.mark.parametrize(
    ("velocity", "angle", "mass", "rate", "expected_time", "expected_distance"),
    LINEAR_DRAG_CASES,
)
def test_linear_drag(velocity, angle, mass, rate, expected_time, expected_distance) -> None:
    result = simulate_flight(velocity, angle, LinearDrag(rate / mass))
    assert_flight(result, expected_time, expected_distance)


def test_result_sampling_is_uniform() -> None:
    result = simulate_flight(30.0, 30.0, LinearDrag(0.5))
    steps = np.diff(result.times)
    assert np.allclose(steps, steps[0])
    assert np.allclose(result.speed, np.hypot(result.vx, result.vy))


def test_drag_shortens_the_flight() -> None:
    free = simulate_flight(40.0, 45.0, LinearDrag(0.0))
    damped = simulate_flight(40.0, 45.0, LinearDrag(0.5))
    assert damped.flight_distance < free.flight_distance
    assert damped.flight_time < free.flight_time
