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
    # ONVIF Media Signing Contract Readiness (P0)
    signing_status: str = "SOURCE_UNSIGNED"
    signature_scheme: Optional[str] = None
    source_identity: Optional[str] = None
    verification_status: str = "NOT_APPLICABLE"
    provenance_chain: List[str] = field(default_factory=list)


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
        bundle = None
        for b_id in inv.evidence_bundle_ids:
            if b_id in self.evidence_bundles:
                bundle = self.evidence_bundles[b_id]
                break

        cam = bundle.source_camera if bundle else "CAM-01"
        ent = bundle.entity_id if bundle else (inv.candidate_id or "ENT-01")

        events = [
            OperatorTimelineEvent("OBSERVATION", now, f"Ingested frame and motion detected on {cam}", cam, "FACT"),
            OperatorTimelineEvent("TRACK", now, f"Tracker established visual trajectory {ent}", ent, "FACT"),
            OperatorTimelineEvent("BEHAVIOR", now, f"Temporal dwell behavior computed for {ent}", ent, "FACT"),
            OperatorTimelineEvent("SITUATION", now, f"Situation candidate detected: {inv.situation_type}", inv.candidate_id, "FACT"),
            OperatorTimelineEvent("EVIDENCE", now, f"Evidence bundle packaged with SHA-256 integrity", ", ".join(inv.evidence_bundle_ids), "FACT"),
            OperatorTimelineEvent("REASONING", now, f"Resolved via {inv.reasoning_level} cascade", inv.investigation_id, "INFERENCE"),
            OperatorTimelineEvent("ACTION", now, f"Proposed policy response: {inv.recommended_action}", inv.investigation_id, "INFERENCE"),
            OperatorTimelineEvent("OPERATOR_REVIEW", now, "Governed action validated under AUTONOMY_2", inv.investigation_id, "FACT"),
            OperatorTimelineEvent("OUTCOME", now, "Action executed and logged to audit store", inv.investigation_id, "FACT"),
        ]

        if self.experiences:
            exp_id = list(self.experiences.keys())[0]
            events.append(OperatorTimelineEvent("EXPERIENCE", now, f"Associated with experience memory {exp_id}", exp_id, "INFERENCE"))
        else:
            events.append(OperatorTimelineEvent("EXPERIENCE", now, "No prior failure experience matches", inv.investigation_id, "INFERENCE"))

        self.timelines[investigation_id] = events
        return events
