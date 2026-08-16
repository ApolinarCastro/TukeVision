"""Tracking LOCAL temporal y actividad temporal (LOOP-0018R).

    EVENT -> LOCAL TRACK -> TEMPORAL ACTIVITY -> OPERATIONAL EVIDENCE

`track_id` es identidad temporal/LOCAL dentro de una cámara y una ventana de
observación. NO es identidad real de una persona, NO es facial, NO es
re-identificación entre cámaras. NO existe correlación cross-camera de
identidad.

Módulos:

  - contract: LocalTrack, TemporalActivity, estados y validación.
  - tracker: LocalTracker (asociación determinista, ciclo STARTED/ACTIVE/ENDED,
    retención acotada, aislamiento por cámara) y build_tracker config-driven.
"""

from src.temporal.contract import (
    ACTIVE,
    ENDED,
    OBJECT_PRESENCE,
    PERSON_PRESENCE,
    STARTED,
    LocalTrack,
    TemporalActivity,
    TemporalConfigError,
    TemporalError,
    TemporalValidationError,
    duration_ms,
)
from src.temporal.tracker import (
    LocalTracker,
    build_tracker,
    compute_iou,
)

__all__ = [
    "ACTIVE",
    "ENDED",
    "OBJECT_PRESENCE",
    "PERSON_PRESENCE",
    "STARTED",
    "LocalTrack",
    "TemporalActivity",
    "TemporalConfigError",
    "TemporalError",
    "TemporalValidationError",
    "duration_ms",
    "LocalTracker",
    "build_tracker",
    "compute_iou",
]