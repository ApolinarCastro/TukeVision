"""Scene Intelligence module (AG-04 / OC-08..OC-12).

Provides a structured scene understanding layer over certified core
components. `import src.scene` must succeed and expose the full public API.
"""

from src.scene.engine import InteractionIntelligence, SceneEngine, ZoneAdapter
from src.scene.models import (
    EvidenceTimeline,
    InteractionEvent,
    OperatorInsight,
    SceneActivity,
    SceneEvent,
    SceneObservation,
    SceneSequence,
    SceneTrack,
    ZoneConfig,
)

__all__ = [
    # Models
    "SceneObservation",
    "SceneTrack",
    "SceneActivity",
    "SceneEvent",
    "SceneSequence",
    "EvidenceTimeline",
    "ZoneConfig",
    "InteractionEvent",
    "OperatorInsight",
    # Engine
    "SceneEngine",
    "InteractionIntelligence",
    "ZoneAdapter",
]