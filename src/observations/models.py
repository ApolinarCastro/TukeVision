"""Modelos de observación.

Una observación es el hecho más pequeño y objetivo que el sistema registra.
No contiene interpretaciones ni acusaciones.
"""

from dataclasses import dataclass

PERSON_ENTERED_ZONE = "PERSON_ENTERED_ZONE"
PERSON_REMAINED_IN_ZONE = "PERSON_REMAINED_IN_ZONE"
PERSON_EXITED_ZONE = "PERSON_EXITED_ZONE"

VALID_OBSERVATION_TYPES = (
    PERSON_ENTERED_ZONE,
    PERSON_REMAINED_IN_ZONE,
    PERSON_EXITED_ZONE,
)


@dataclass(frozen=True)
class Observation:
    """Observación objetiva e inmutable del sistema."""
    observation_id: str
    timestamp: str
    store_id: str
    camera_id: str
    zone_id: str
    track_id: int
    observation_type: str
    value: float
    confidence: float
    source_frame: int
