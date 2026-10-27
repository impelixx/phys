"""
Oracle tests: closed-form references for the rod pendulum.

Small-amplitude cases and tolerances follow the original lab test suite;
large amplitudes are checked against the exact elliptic-integral period.
"""

import math

import numpy as np
import pytest

from pendulumswing.physics import (
    Rod,
    damped_period,
    exact_period,
    linear_angle,
    simulate_swing,
    small_angle_period,
    swing_period,
)

ABSOLUTE_PRECISION = 1.75 * 10 ** (-4)  # 0.01 degrees
RELATIVE_PRECISION = 5 * 10 ** (-4)  # 0.05%
SIMULATION_TIME = 10.0

SMALL_SWINGS = [
    # length, mass, amplitude (degrees)
    (1.0, 1.0, 2.0),
    (0.5, 1.0, 2.0),
    (2.0, 1.0, 2.0),
    (1.0, 1.0, 1.0),
    (1.0, 1.0, 5.0),
    (1.0, 2.0, 2.0),
    (1.0, 0.5, 2.0),
]

DAMPED_SWINGS = [
    # length, mass, amplitude (degrees), friction
    (1.0, 1.0, 2.0, 0.1),
    (1.0, 1.0, 2.0, 1.0),
    (0.5, 1.0, 1.0, 0.1),
    (2.0, 1.0, 2.0, 0.1),
    (2.0, 1.0, 3.0, 0.1),
    (1.0, 1.0, 1.0, 0.1),
    (1.0, 2.0, 2.0, 0.1),
    (1.0, 0.5, 2.0, 0.1),
]


def almost_equal(value: float, reference: float) -> bool:
    tolerance = max(ABSOLUTE_PRECISION, RELATIVE_PRECISION * max(abs(value), abs(reference)))
    return abs(value - reference) < tolerance


@pytest.mark.parametrize(("length", "mass", "amplitude"), SMALL_SWINGS)
def test_small_angle_period(length, mass, amplitude) -> None:
    rod = Rod(mass=mass, length=length)
    result = simulate_swing(rod, amplitude, SIMULATION_TIME)
    assert almost_equal(result.period, small_angle_period(rod))


@pytest.mark.parametrize(("length", "mass", "amplitude"), SMALL_SWINGS)
def test_energy_conservation(length, mass, amplitude) -> None:
    rod = Rod(mass=mass, length=length)
    result = simulate_swing(rod, amplitude, SIMULATION_TIME)
    assert result.energy_drift < 10 ** (-7)


@pytest.mark.parametrize("amplitude", [10.0, 45.0, 90.0, 135.0, 170.0])
def test_exact_period_at_large_amplitude(amplitude) -> None:
    rod = Rod(mass=1.0, length=1.0)
    expected = exact_period(rod, amplitude)
    assert swing_period(rod, amplitude) == pytest.approx(expected, rel=10 ** (-7))
    result = simulate_swing(rod, amplitude, 4 * expected)
    assert result.period == pytest.approx(expected, rel=10 ** (-7))
    assert result.energy_drift < 10 ** (-7)


def test_exact_period_sanity() -> None:
    """The well-known ratio T(90°) / T₀ ≈ 1.18 pins down the elliptic parameter."""
    rod = Rod(mass=1.0, length=1.0)
    assert exact_period(rod, 90.0) / small_angle_period(rod) == pytest.approx(
        1.1803, abs=10 ** (-4)
    )
    assert exact_period(rod, 0.0) == pytest.approx(small_angle_period(rod))


@pytest.mark.parametrize(("length", "mass", "amplitude", "friction"), DAMPED_SWINGS)
def test_damped_swing_matches_linear_theory(length, mass, amplitude, friction) -> None:
    rod = Rod(mass=mass, length=length, friction=friction)
    result = simulate_swing(rod, amplitude, SIMULATION_TIME)
    assert almost_equal(result.period, damped_period(rod))
    expected = linear_angle(rod, amplitude, result.times)
    for simulated, theoretical in zip(result.angle, expected, strict=True):
        assert almost_equal(simulated, theoretical)


@pytest.mark.parametrize(("length", "mass", "amplitude", "friction"), DAMPED_SWINGS)
def test_friction_drains_energy(length, mass, amplitude, friction) -> None:
    rod = Rod(mass=mass, length=length, friction=friction)
    result = simulate_swing(rod, amplitude, SIMULATION_TIME)
    assert np.all(np.diff(result.total_energy) <= 10 ** (-12))
    assert result.total_energy[-1] < result.total_energy[0]


@pytest.mark.parametrize("friction", [8.0, 10.0])
def test_overdamped_rod_creeps_without_swinging(friction) -> None:
    rod = Rod(mass=0.5, length=1.0, friction=friction)
    assert rod.damping_ratio > 1
    result = simulate_swing(rod, 3.0, SIMULATION_TIME)
    assert result.period is None
    assert np.all(result.angle > 0)
    expected = linear_angle(rod, 3.0, result.times)
    assert np.allclose(result.angle, expected, atol=ABSOLUTE_PRECISION)


def test_period_grows_with_amplitude() -> None:
    rod = Rod(mass=1.0, length=1.0)
    periods = [swing_period(rod, amplitude) for amplitude in (5, 30, 60, 90, 120, 150)]
    assert periods == sorted(periods)


def test_mass_does_not_change_the_motion() -> None:
    light = simulate_swing(Rod(mass=0.1, length=1.5), 40.0, 5.0)
    heavy = simulate_swing(Rod(mass=100.0, length=1.5), 40.0, 5.0)
    assert np.allclose(light.angle, heavy.angle, atol=10 ** (-9))


def test_sampling_is_uniform() -> None:
    result = simulate_swing(Rod(mass=1.0, length=1.0, friction=0.5), 20.0, 3.0)
    steps = np.diff(result.times)
    assert np.allclose(steps, steps[0])
    assert result.angle[0] == pytest.approx(math.radians(20.0))
