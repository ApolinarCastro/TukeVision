"""Data transfer objects for semantic person observations."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VisitSemanticSnapshot:
    """Immutable snapshot of a person's semantic state at a specific frame.
    
    This DTO bridges the tracking/perception engines (Pipeline, AdvanceChain)
    and the UI/Presentation layer without exposing mutable internal states.
    """
    track_id: str
    camera_id: str
    person_state: str
    visit_id: Optional[str]
    visit_role: str
    customer_analytics_eligible: bool
    visit_origin: str
