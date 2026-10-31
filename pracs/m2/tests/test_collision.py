"""
Oracle tests: conservation laws and closed-form contact dynamics.

Head-on impacts must reproduce the instantaneous-impact formulas exactly.
In oblique impacts the line of centres turns slightly while the balls are in
contact, by about v_t τ / 2R, so those cases use a stiff contact and a tolerance
derived from that estimate.
"""

import math

import numpy as np
import pytest

from billiards.physics import (
    CollisionSetup,
    HertzContact,
    HookeContact,
    contact_duration,
    elastic_velocities,
    max_compression,
    reduced_mass,
    simulate_collision,
    wall_reflection,
)

RELATIVE_ERROR = 10 ** (-6)
RADIUS = 0.0286  # pool ball
BALL_MASS = 0.17

CONTACTS = [HookeContact(10.0**5), HertzContact(4.5 * 10.0**8)]
STIFF_CONTACTS = [HookeContact(10.0**9), HertzContact(10.0**12)]

HEAD_ON_CASES = [
    # mass1, mass2, velocity1, velocity2
    (BALL_MASS, BALL_MASS, (2.0, 0.0), (0.0, 0.0)),
    (BALL_MASS, BALL_MASS, (3.0, 0.0), (-1.0, 0.0)),
    (0.1, 0.4, (2.0, 0.0), (0.0, 0.0)),
    (0.4, 0.1, (2.0, 0.0), (0.0, 0.0)),
    (0.2, 0.3, (1.5, 0.0), (-2.5, 0.0)),
    (0.3, 0.3, (4.0, 0.0), (1.0, 0.0)),
    (0.25, 0.15, (1.0, 1.0), (-0.5, -0.5)),
]

OBLIQUE_CASES = [
    # mass1, mass2, velocity1, velocity2, impact
    (BALL_MASS, BALL_MASS, (2.0, 0.0), (0.0, 0.0), 0.5),
    (BALL_MASS, BALL_MASS, (2.0, 0.0), (0.0, 0.0), 0.9),
    (0.1, 0.3, (2.0, 0.0), (0.0, 0.0), 0.3),
    (0.3, 0.1, (2.0, 0.0), (0.0, 1.0), 0.6),
    (0.2, 0.2, (1.0, 2.0), (-1.0, 0.5), 0.4),
]


def setup_of(mass1, mass2, velocity1, velocity2, impact=0.0) -> CollisionSetup:
    return CollisionSetup(
        mass1=mass1,
        mass2=mass2,
        radius=RADIUS,
        velocity1=np.array(velocity1),
        velocity2=np.array(velocity2),
        impact=impact,
    )


def expected_velocities(setup: CollisionSetup) -> tuple[np.ndarray, np.ndarray]:
    return elastic_velocities(
        setup.mass1, setup.mass2, setup.velocity1, setup.velocity2, setup.touch_normal
    )


def wall_setup(mass, velocity, impact=0.0) -> CollisionSetup:
    return CollisionSetup(
        mass1=mass,
        mass2=1.0,
        radius=RADIUS,
        velocity1=np.array(velocity),
        velocity2=np.zeros(2),
        impact=impact,
        wall=True,
    )


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize(("mass1", "mass2", "velocity1", "velocity2"), HEAD_ON_CASES)
def test_head_on_matches_conservation_laws(mass1, mass2, velocity1, velocity2, contact) -> None:
    setup = setup_of(mass1, mass2, velocity1, velocity2)
    result = simulate_collision(setup, contact)
    first, second = expected_velocities(setup)
    scale = np.linalg.norm(setup.relative_velocity)
    assert np.allclose(result.velocity1_after, first, atol=RELATIVE_ERROR * scale)
    assert np.allclose(result.velocity2_after, second, atol=RELATIVE_ERROR * scale)


@pytest.mark.parametrize("contact", CONTACTS)
def test_equal_masses_exchange_velocities(contact) -> None:
    result = simulate_collision(setup_of(BALL_MASS, BALL_MASS, (2.0, 0.0), (0.0, 0.0)), contact)
    assert np.allclose(result.velocity1_after, (0.0, 0.0), atol=10 ** (-6))
    assert np.allclose(result.velocity2_after, (2.0, 0.0), atol=10 ** (-6))


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize(("mass1", "mass2", "velocity1", "velocity2"), HEAD_ON_CASES)
def test_contact_time_and_compression(mass1, mass2, velocity1, velocity2, contact) -> None:
    setup = setup_of(mass1, mass2, velocity1, velocity2)
    result = simulate_collision(setup, contact)
    mass = reduced_mass(mass1, mass2)
    speed = setup.approach_speed
    assert result.contact_duration == pytest.approx(
        contact_duration(contact, mass, speed), rel=RELATIVE_ERROR
    )
    assert result.max_compression == pytest.approx(
        max_compression(contact, mass, speed), rel=10 ** (-4)
    )


def test_hooke_contact_lasts_half_a_spring_period() -> None:
    contact = HookeContact(2.0 * 10**4)
    mass = reduced_mass(0.2, 0.3)
    assert contact_duration(contact, mass, 1.7) == pytest.approx(math.pi * math.sqrt(mass / 2e4))
    assert max_compression(contact, mass, 1.7) == pytest.approx(1.7 * math.sqrt(mass / 2e4))


def test_hertz_contact_time_constant() -> None:
    """τ = 2.9432 δₘ / v for the Hertz law: the textbook constant."""
    contact = HertzContact(10.0**9)
    ratio = contact_duration(contact, 0.1, 2.0) / (max_compression(contact, 0.1, 2.0) / 2.0)
    assert ratio == pytest.approx(2.9432, abs=10 ** (-4))


@pytest.mark.parametrize("contact", STIFF_CONTACTS)
@pytest.mark.parametrize(("mass1", "mass2", "velocity1", "velocity2", "impact"), OBLIQUE_CASES)
def test_oblique_matches_conservation_laws(
    mass1, mass2, velocity1, velocity2, impact, contact
) -> None:
    setup = setup_of(mass1, mass2, velocity1, velocity2, impact)
    result = simulate_collision(setup, contact)
    first, second = expected_velocities(setup)
    speed = np.linalg.norm(setup.relative_velocity)
    turn = speed * result.contact_duration / (2 * RADIUS)
    tolerance = turn * speed + RELATIVE_ERROR * speed
    assert np.allclose(result.velocity1_after, first, atol=tolerance)
    assert np.allclose(result.velocity2_after, second, atol=tolerance)


@pytest.mark.parametrize("contact", STIFF_CONTACTS)
@pytest.mark.parametrize("impact", [0.2, 0.5, 0.8])
def test_equal_masses_scatter_at_right_angle(impact, contact) -> None:
    result = simulate_collision(
        setup_of(BALL_MASS, BALL_MASS, (2.0, 0.0), (0.0, 0.0), impact), contact
    )
    assert result.separation_angle == pytest.approx(90.0, abs=10 ** (-2))


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize(("mass1", "mass2", "velocity1", "velocity2", "impact"), OBLIQUE_CASES)
def test_momentum_and_energy_are_conserved(
    mass1, mass2, velocity1, velocity2, impact, contact
) -> None:
    setup = setup_of(mass1, mass2, velocity1, velocity2, impact)
    result = simulate_collision(setup, contact)
    initial_momentum = mass1 * np.array(velocity1) + mass2 * np.array(velocity2)
    momentum_scale = np.linalg.norm(initial_momentum) + mass1 * np.linalg.norm(velocity1)
    assert np.allclose(result.momentum, initial_momentum, atol=10 ** (-9) * momentum_scale)
    energy = result.total_energy
    assert np.allclose(energy, energy[0], rtol=10 ** (-8))
    assert result.elastic_energy[0] == pytest.approx(0.0, abs=10 ** (-12) * energy[0])
    assert result.kinetic_energy[-1] == pytest.approx(energy[0], rel=10 ** (-8))


@pytest.mark.parametrize("contact", CONTACTS)
def test_contact_is_symmetric_in_time(contact) -> None:
    result = simulate_collision(setup_of(0.2, 0.3, (2.0, 0.0), (0.0, 0.0)), contact)
    assert np.allclose(result.compression, result.compression[::-1], atol=10 ** (-9))


def test_balls_moving_together_never_meet() -> None:
    with pytest.raises(ValueError, match="never collide"):
        simulate_collision(setup_of(0.2, 0.2, (1.0, 0.0), (1.0, 0.0)), HookeContact(10.0**5))


def test_too_soft_contact_is_rejected() -> None:
    with pytest.raises(ValueError, match="too soft"):
        simulate_collision(setup_of(1.0, 1.0, (10.0, 0.0), (0.0, 0.0)), HookeContact(10.0))


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize(
    ("mass", "velocity"), [(0.17, (2.0, 0.0)), (1.0, (0.0, -5.0)), (0.05, (3.0, 4.0))]
)
def test_head_on_wall_bounce_reverses_velocity(mass, velocity, contact) -> None:
    result = simulate_collision(wall_setup(mass, velocity), contact)
    assert np.allclose(result.velocity1_after, -np.array(velocity), atol=10 ** (-6))
    assert result.contact_duration == pytest.approx(
        contact_duration(contact, mass, np.linalg.norm(velocity)), rel=RELATIVE_ERROR
    )
    assert np.allclose(result.position2, 0.0)


@pytest.mark.parametrize("contact", CONTACTS)
@pytest.mark.parametrize("impact", [0.3, 0.6, 0.9])
def test_wall_reflection_angle_and_energy(impact, contact) -> None:
    """Angle of reflection equals the angle of incidence; the tangential speed survives."""
    setup = wall_setup(0.17, (2.0, 0.0), impact)
    result = simulate_collision(setup, contact)
    expected = wall_reflection(setup.velocity1, setup.touch_normal)
    assert np.allclose(result.velocity1_after, expected, atol=10 ** (-6))
    energy = result.total_energy
    assert np.allclose(energy, energy[0], rtol=10 ** (-8))
    incoming = setup.velocity1 @ setup.touch_normal
    outgoing = result.velocity1_after @ setup.touch_normal
    assert outgoing == pytest.approx(-incoming, rel=10 ** (-6))


def test_very_heavy_ball_acts_as_a_wall() -> None:
    heavy = simulate_collision(
        setup_of(0.17, 0.17 * 10**9, (2.0, 0.0), (0.0, 0.0), 0.4), STIFF_CONTACTS[1]
    )
    mirrored = wall_reflection(heavy.setup.velocity1, heavy.setup.touch_normal)
    assert np.allclose(heavy.velocity1_after, mirrored, atol=10 ** (-3))


def test_wall_cannot_move() -> None:
    setup = CollisionSetup(
        mass1=0.2,
        mass2=1.0,
        radius=RADIUS,
        velocity1=np.array([1.0, 0.0]),
        velocity2=np.array([0.5, 0.0]),
        wall=True,
    )
    with pytest.raises(ValueError, match="cannot move"):
        simulate_collision(setup, HookeContact(10.0**5))
