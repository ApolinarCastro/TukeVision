"""Operator AI Foundation (AG-05 / OC-13, OC-14).

Provides explainable OperatorInsight generation and structured query
experience with full traceability to store, cameras, tracks, scene events,
evidence and timeline. No automatic accusation - only
ACTIVITY_REQUIRES_REVIEW taxonomy.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from src.behavior.contracts import BehaviorSignal, RiskEvent
from src.correlation.correlator import CrossCameraCorrelator
from src.evidence.store import EvidenceStore
from src.scene.models import (
    EvidenceTimeline,
    OperatorInsight,
    SceneSequence,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class OperatorQuery:
    """Structured operator query (OC-14).

    Not a chatbot - structured questions over stored insights/events.
    """
    query_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    what: str = ""            # What occurred (event types)
    where: str = ""           # Store, camera, zone
    when: Tuple[str, str] = ("", "")  # Time range
    which_cameras: Tuple[str, ...] = ()
    why: str = ""             # Why review needed (signal types)
    evidence_requested: bool = False
    store_id: str = ""        # Explicit store filter (traceability)


@dataclass(frozen=True)
class QueryResult:
    """Result of an operator query."""
    query_id: str
    insights: Tuple[OperatorInsight, ...] = ()
    scene_sequences: Tuple[SceneSequence, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    total_matches: int = 0


class OperatorInsightGenerator:
    """Generates OperatorInsight from scene events (OC-13).

    Consumes: SceneSequence, EvidenceTimeline, BehaviorSignal, RiskEvent,
    store context. Produces an explainable insight whose traceability spans
    organization, store, cameras, tracks, scene events, evidence and the
    timeline span.
    """

    def __init__(
        self,
        evidence_store: Optional[EvidenceStore] = None,
        cross_camera: Optional[CrossCameraCorrelator] = None,
        organization_id: str = "",
        store_id: str = "",
    ) -> None:
        self._evidence_store = evidence_store
        self._cross_camera = cross_camera
        self._organization_id = organization_id
        self._store_id = store_id

    def generate_from_scene_sequence(
        self,
        sequence: SceneSequence,
        evidence_timeline: EvidenceTimeline,
        behavior_signals: Sequence[BehaviorSignal] = (),
        risk_events: Sequence[RiskEvent] = (),
    ) -> OperatorInsight:
        """Generate insight from a complete scene sequence."""
        cameras = set()
        tracks = set()
        scene_event_ids = []
        all_evidence = list(evidence_timeline.evidence_items)
        explanations = []

        for event in sequence.events:
            cameras.update(event.camera_ids)
            tracks.update(event.track_ids)
            scene_event_ids.append(event.event_id)
            explanations.append(event.explanation)

        explanation = self._build_sequence_explanation(sequence, explanations)
        reason = self._build_reason_for_review(behavior_signals, risk_events)
        priority = self._compute_priority(risk_events)
        uncertainty = self._compute_uncertainty(sequence, evidence_timeline)

        return OperatorInsight(
            organization_id=self._organization_id,
            store_id=self._store_id,
            cameras=tuple(sorted(cameras)),
            tracks=tuple(sorted(tracks)),
            scene_events=tuple(scene_event_ids),
            timeline_span=(sequence.start_time, sequence.end_time),
            evidence_refs=tuple(
                dict(item).get("path", "")
                for item in all_evidence
                if dict(item).get("path")
            ),
            explanation=explanation,
            reason_for_review=reason,
            priority=priority,
            uncertainty_score=uncertainty,
            recommended_action=self._recommend_action(priority, sequence),
        )

    def _build_sequence_explanation(
        self,
        sequence: SceneSequence,
        explanations: List[str],
    ) -> str:
        parts = [
            f"Secuencia de {len(sequence.events)} eventos para Track {sequence.track_id}.",
            f"Cámaras involucradas: {', '.join(sequence.camera_path)}.",
        ]
        if sequence.zones_traversed:
            parts.append(f"Zonas recorridas: {', '.join(sequence.zones_traversed)}.")
        parts.extend(explanations[:3])
        return " ".join(parts)

    @staticmethod
    def _build_reason_for_review(
        behavior_signals: Sequence[BehaviorSignal],
        risk_events: Sequence[RiskEvent],
    ) -> str:
        reasons = ["ACTIVITY_REQUIRES_REVIEW"]
        if behavior_signals:
            signal_types = ", ".join(
                dict.fromkeys(s.signal_type for s in behavior_signals)
            )
            reasons.append(f"Señales conductuales: {signal_types}")
        if risk_events:
            max_risk = max(r.risk_score for r in risk_events)
            reasons.append(f"Riesgo máximo: {max_risk}/100")
        return "; ".join(reasons)

    @staticmethod
    def _compute_priority(risk_events: Sequence[RiskEvent]) -> str:
        if not risk_events:
            return "MEDIUM"
        max_risk = max(r.risk_score for r in risk_events)
        if max_risk >= 80:
            return "CRITICAL"
        if max_risk >= 60:
            return "HIGH"
        if max_risk >= 40:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _compute_uncertainty(
        sequence: SceneSequence,
        evidence_timeline: EvidenceTimeline,
    ) -> float:
        """Uncertainty based on evidence completeness and cross-camera span."""
        base = 0.1
        if len(sequence.camera_path) > 1:
            base += 0.05
        if len(evidence_timeline.evidence_items) < len(sequence.events):
            base += 0.15
        return min(base, 1.0)

    @staticmethod
    def _recommend_action(priority: str, sequence: SceneSequence) -> str:
        if priority == "CRITICAL":
            return "Revisar inmediatamente clips de evidencia de todas las cámaras involucradas"
        if priority == "HIGH":
            return "Revisar clips de evidencia prioritarios en las próximas 2 horas"
        if priority == "MEDIUM":
            return (
                f"Sugerido revisar evidencia de cámara "
                f"{sequence.camera_path[0] if sequence.camera_path else 'principal'}"
            )
        return "Monitorear; no se requiere acción inmediata"


class OperatorQueryEngine:
    """Structured query engine for operator questions (OC-14).

    Supports queries: what, where (store/camera/zone), when, which cameras,
    why, show evidence. Insights are indexed by store, camera, track and
    scene event for traceable retrieval.
    """

    def __init__(
        self,
        evidence_store: Optional[EvidenceStore] = None,
    ) -> None:
        self._evidence_store = evidence_store
        self._insight_index: Dict[str, List[OperatorInsight]] = defaultdict(list)
        self._sequence_index: Dict[str, List[SceneSequence]] = defaultdict(list)

    def index_insight(self, insight: OperatorInsight) -> None:
        """Add insight to search indices (store/camera/track/event)."""
        for key in (f"store:{insight.store_id}",) if insight.store_id else ():
            self._insight_index[key].append(insight)
        for cam in insight.cameras:
            self._insight_index[f"camera:{cam}"].append(insight)
        for track in insight.tracks:
            self._insight_index[f"track:{track}"].append(insight)
        for event_id in insight.scene_events:
            self._insight_index[f"event:{event_id}"].append(insight)

    def index_sequence(self, sequence: SceneSequence) -> None:
        """Add sequence to search indices."""
        if sequence.store_id:
            self._sequence_index[f"store:{sequence.store_id}"].append(sequence)
        for cam in sequence.camera_path:
            self._sequence_index[f"camera:{cam}"].append(sequence)

    def query(self, query: OperatorQuery) -> QueryResult:
        """Execute structured query."""
        candidate_insights: set = set()
        candidate_sequences: set = set()

        store_id = query.store_id
        if not store_id and query.where:
            store_id = self._store_from_where(query.where)

        if store_id:
            candidate_insights.update(self._insight_index.get(f"store:{store_id}", []))
            candidate_sequences.update(self._sequence_index.get(f"store:{store_id}", []))

        if query.which_cameras:
            for cam in query.which_cameras:
                candidate_insights.update(self._insight_index.get(f"camera:{cam}", []))
                candidate_sequences.update(self._sequence_index.get(f"camera:{cam}", []))

        if query.when[0] and query.when[1]:
            candidate_insights = {
                i for i in candidate_insights
                if query.when[0] <= i.timestamp_utc <= query.when[1]
            }
            candidate_sequences = {
                s for s in candidate_sequences
                if query.when[0] <= s.start_time <= query.when[1]
            }

        if query.why:
            candidate_insights = {
                i for i in candidate_insights
                if query.why.lower() in i.reason_for_review.lower()
            }

        if query.what:
            candidate_insights = {
                i for i in candidate_insights
                if query.what.lower() in i.explanation.lower()
            }

        evidence: set = set()
        for i in candidate_insights:
            evidence.update(i.evidence_refs)

        return QueryResult(
            query_id=query.query_id,
            insights=tuple(sorted(candidate_insights, key=lambda i: i.timestamp_utc)),
            scene_sequences=tuple(sorted(
                candidate_sequences, key=lambda s: s.start_time
            )),
            evidence_refs=tuple(evidence),
            total_matches=len(candidate_insights),
        )

    @staticmethod
    def _store_from_where(where: str) -> str:
        """Extract a store id from a free-form ``where`` value."""
        text = str(where or "").strip()
        if not text:
            return ""
        if " " in text:
            first = text.split()[0]
            return first if first.startswith(("store_", "STORE")) else ""
        return text if text.startswith(("store_", "STORE")) else ""