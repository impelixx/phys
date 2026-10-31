"""Collision physics: contact laws, impact integration and conservation-law references."""

from .collision import CollisionResult, CollisionSetup, simulate_collision
from .contact import ContactModel, HertzContact, HookeContact
from .theory import (
    contact_duration,
    elastic_velocities,
    max_compression,
    reduced_mass,
    wall_reflection,
)

__all__ = [
    "CollisionResult",
    "CollisionSetup",
    "ContactModel",
    "HertzContact",
    "HookeContact",
    "contact_duration",
    "elastic_velocities",
    "max_compression",
    "reduced_mass",
    "simulate_collision",
    "wall_reflection",
]
