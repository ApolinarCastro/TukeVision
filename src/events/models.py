"""Modelos de eventos.

Un evento es un conjunto de una o más observaciones relacionadas que
describen un hecho ocurrido dentro de la tienda.
"""

from dataclasses import dataclass
from typing import List, Tuple

PERMANENCIA_PROLONGADA = "PERMANENCIA_PROLONGADA"

VALID_EVENT_TYPES = (PERMANENCIA_PROLONGADA,)


@dataclass(frozen=True)
class Event:
    """Evento inmutable formado a partir de observaciones."""
    event_id: str
    event_type: str
    timestamp: str
    store_id: str
    camera_id: str
    zone_id: str
    track_id: int
    observation_ids: Tuple[str, ...]
    duration_seconds: float
