"""Flight physics: drag models and ballistic integration."""

from .drag import GRAVITY, DragModel, LinearDrag, QuadraticDrag
from .flight import FlightResult, simulate_flight

__all__ = [
    "GRAVITY",
    "DragModel",
    "FlightResult",
    "LinearDrag",
    "QuadraticDrag",
    "simulate_flight",
]
