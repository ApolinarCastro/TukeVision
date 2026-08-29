"""Phase 12: Unified Operational Intelligence Presentation Model.

Connects backend events (Perception, Spatial, Situations, Evidence Bundles,
Agent Monitor, Governed Actions, and Experiences) into human-navigable UI views.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SituationViewItem:
    situation_id: str
    situation_type: str
    camera_ids: List[str]
    zone_ids: List[str]
    entity_ids: List[str]
    started_at: str
    duration_seconds: float
    status: str
    confidence: float
    evidence_bundle_ref: Optional[str] = None
    investigation_id: Optional[str] = None
    severity: str = "MEDIUM"


@dataclass
class InvestigationViewItem:
    investigation_id: str
    candidate_id: str
    situation_type: str
    priority: str
    reasoning_level: str  # "STRUCTURED", "DETERMINISTIC", "LOCAL_LLM", "LOCAL_VLM"
    facts: List[str]
    inferences: List[str]
    unknowns: List[str]
    evidence_bundle_ids: List[str]
    recommended_action: str
    status: str
    updated_at: str


@dataclass
class EvidenceBundleViewItem:
    bundle_id: str
    source_camera: str
    observed_at: str
    entity_id: Optional[str]
    situation_id: Optional[str]
    confidence: float
    detector_runtime: str
    model_id: str
    hashes: Dict[str, str]
    key_frame_path: Optional[str]
    roi_crop_path: Optional[str]
    freshness_ms: float = 24.5


@dataclass
class GovernedActionViewItem:
    action_id: str
    action_type: str
    target_channel: str
    site_id: str
    autonomy_level: str  # "AUTONOMY_0", "AUTONOMY_1", "AUTONOMY_2"
    autonomy_3_status: str = "DISABLED"
    policy_decision: str = "ALLOW"
    operator_review_required: bool = False
    execution_status: str = "VERIFIED"
    outcome: str = "SUCCESS"


@dataclass
class ExperienceContextViewItem:
    experience_id: str
    failure_signature: str
    root_cause: str
    proven_resolution: str
    recurrence_count: int
    context_type: str = "HISTORICAL_EXPERIENCE"


@dataclass
class OperatorTimelineEvent:
    stage: str  # "OBSERVATION", "TRACK", "BEHAVIOR", "SITUATION", "EVIDENCE", "INVESTIGATION", "REASONING", "ACTION", "OPERATOR_REVIEW", "OUTCOME", "EXPERIENCE"
    timestamp: str
    summary: str
    reference_id: str
    epistemic_state: str = "FACT"


class OperationalIntelligenceViewModel:
    """Aggregates and formats backend state for the Command Center."""

    def __init__(self):
        self.active_situations: Dict[str, SituationViewItem] = {}
        self.investigations: Dict[str, InvestigationViewItem] = {}
        self.evidence_bundles: Dict[str, EvidenceBundleViewItem] = {}
        self.governed_actions: Dict[str, GovernedActionViewItem] = {}
        self.experiences: Dict[str, ExperienceContextViewItem] = {}
        self.timelines: Dict[str, List[OperatorTimelineEvent]] = {}

    def record_situation(self, situation: SituationViewItem) -> None:
        self.active_situations[situation.situation_id] = situation

    def record_investigation(self, inv: InvestigationViewItem) -> None:
        self.investigations[inv.investigation_id] = inv

    def record_evidence_bundle(self, bundle: EvidenceBundleViewItem) -> None:
        self.evidence_bundles[bundle.bundle_id] = bundle

    def record_action(self, action: GovernedActionViewItem) -> None:
        self.governed_actions[action.action_id] = action

    def record_experience(self, exp: ExperienceContextViewItem) -> None:
        self.experiences[exp.experience_id] = exp

    def build_operator_timeline(self, investigation_id: str) -> List[OperatorTimelineEvent]:
        """Constructs an end-to-end audit timeline for an investigation."""
        inv = self.investigations.get(investigation_id)
        if not inv:
            return []

        now = datetime.now(timezone.utc).isoformat()
        events = []
        if inv.situation_type:
            events.append(OperatorTimelineEvent("SITUATION", now, f"Situation detected: {inv.situation_type}", inv.candidate_id, "FACT"))
        if inv.evidence_bundle_ids:
            events.append(OperatorTimelineEvent("EVIDENCE", now, f"Evidence bundle packaged with SHA-256", ", ".join(inv.evidence_bundle_ids), "FACT"))
        events.append(OperatorTimelineEvent("INVESTIGATION", now, f"Agent Monitor active with priority {inv.priority}", inv.investigation_id, "FACT"))
        if inv.reasoning_level:
            events.append(OperatorTimelineEvent("REASONING", now, f"Resolved via {inv.reasoning_level} cascade", inv.investigation_id, "INFERENCE"))
        if inv.recommended_action:
            events.append(OperatorTimelineEvent("ACTION", now, f"Proposed: {inv.recommended_action}", inv.investigation_id, "INFERENCE"))

        self.timelines[investigation_id] = events
        return events
