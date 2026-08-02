"""Modelos de evidencia.

La evidencia respalda una observación o evento y nunca puede modificarse.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class EvidenceMetadata:
    """Metadatos inmutables asociados a una evidencia."""
    alert_id: str
    event_id: str
    observation_ids: Tuple[str, ...]
    track_id: int
    zone_id: str
    duration_seconds: float
    risk_score: int
    rule_id: str
    timestamp: str
    frame_sha256: str
