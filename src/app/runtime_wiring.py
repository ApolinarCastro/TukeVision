"""Runtime wiring of the vertical tail (MACRO-OC-02, Bloques E/F/G).

Pipeline results (already produced by the certified AdvanceChain) are
connected to the existing Scene / Operator / Learning foundations:

    Scene (E):  ActivityObservation -> SceneObservation -> SceneTrack
                TemporalActivity -> SceneActivity
                BehaviorResult -> SceneEvent -> SceneSequence -> EvidenceTimeline
    Operator (F): SceneSequence + EvidenceTimeline + BehaviorSignal/RiskEvent
                  -> OperatorInsight (only ACTIVITY_REQUIRES_REVIEW)
    Learning (G): pipeline signal -> RawCase -> human review -> ReviewedCase
                  -> training eligible -> FeedbackDataset (never auto-promote)

No layer is reimplemented.  No new detector/tracker.  No autonomous model or
policy promotion: the CANDIDATE_PROMOTION_GATE stays in PolicyManager.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.learning.memory import (
    CaseMemory,
    FeedbackDataset,
    FeedbackDatasetBuilder,
    PolicyManager,
    RawCase,
    ReviewedCase,
    SignalLabel,
)
from src.operator.engine import OperatorInsightGenerator, OperatorQueryEngine
from src.review.contracts import SignalReviewRecord
from src.scene.engine import SceneEngine, ZoneAdapter
from src.scene.models import ZoneConfig

logger = logging.getLogger("tukevision.runtime_wiring")


def _classification_to_label(classification: str) -> SignalLabel:
    """Map the QW-00 human classification onto the learning label set."""
    value = str(classification or "").upper()
    if value == "USEFUL_SIGNAL":
        return SignalLabel.USEFUL_SIGNAL
    if value == "BENIGN_ACTIVITY":
        return SignalLabel.FALSE_POSITIVE
    return SignalLabel.INSUFFICIENT_EVIDENCE


def _zone_configs_from_config(config: Dict[str, Any]) -> List[ZoneConfig]:
    """Build ZoneConfigs from the product config when present (no invention)."""
    raw = config.get("zone_configs") or config.get("zones") or config.get("zone")
    zones: List[ZoneConfig] = []
    if isinstance(raw, dict):
        if "zone_id" in raw or "name" in raw:
            raw = [raw]
        else:
            raw = list(raw.values())
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        polygon = tuple(
            tuple(float(v) for v in point)
            for point in (item.get("polygon") or ())
            if isinstance(point, (list, tuple)) and len(point) >= 2
        )
        rectangle = tuple(item.get("rectangle") or (0, 0, 0, 0))
        if len(rectangle) != 4:
            rectangle = (0, 0, 0, 0)
        zones.append(ZoneConfig(
            zone_id=str(item.get("zone_id") or ""),
            zone_name=str(item.get("zone_name") or ""),
            zone_type=str(item.get("zone_type") or "RECTANGLE"),
            polygon=polygon,
            rectangle=tuple(int(v) for v in rectangle),
            camera_id=str(item.get("camera_id") or ""),
            is_restricted=bool(item.get("is_restricted", False)),
            metadata=dict(item.get("metadata") or {}),
        ))
    return zones


class RuntimeWiring:
    """Per-store vertical wiring from pipeline results to learning cases.

    Thread-safety: the edge runtime feeds results from its worker thread and
    review records may arrive from the operator thread.  All state mutation
    is guarded by a lock; generated insights/sequences are deduplicated.
    """

    def __init__(
        self,
        *,
        organization_id: str = "",
        store_id: str = "",
        zone_configs: Optional[Sequence[ZoneConfig]] = None,
        dataset_root: str = "data/learning/datasets",
        policy_root: str = "data/learning/policies",
        dataset_version: str = "v1",
    ) -> None:
        import threading
        self._lock = threading.RLock()
        self._organization_id = organization_id
        self._store_id = store_id
        self._dataset_version = dataset_version
        self._zone_adapter = ZoneAdapter(list(zone_configs or ()))
        self._scene = SceneEngine(
            zone_adapter=self._zone_adapter, store_id=store_id
        )
        self._insight = OperatorInsightGenerator(
            organization_id=organization_id, store_id=store_id
        )
        self._queries = OperatorQueryEngine()
        self._memory = CaseMemory()
        self._datasets = FeedbackDatasetBuilder(self._memory, dataset_root)
        self._policies = PolicyManager(policy_root)
        self._events: List[Any] = []
        self._insights: List[Any] = []
        self._sequences: List[Any] = []
        self._raw_by_signal: Dict[str, RawCase] = {}
        self._signals_by_track: Dict[str, list] = defaultdict(list)
        self._risk_by_track: Dict[str, list] = defaultdict(list)
        self._sequence_keys = set()
        self._counts = {
            "scene_events": 0,
            "insights": 0,
            "sequences": 0,
            "raw_cases": 0,
            "reviewed_cases": 0,
            "training_eligible": 0,
        }

    # ------------------------------------------------------------------
    # Scene (E)
    # ------------------------------------------------------------------
    def ingest_result(self, camera_id: str, snapshot: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, int]:
        """Feed one canonical pipeline result into the scene layer."""
        with self._lock:
            observation = result.get("observation")
            track = result.get("track")
            temporal = result.get("temporal_activity")
            behavior = result.get("behavior")
            evidence = result.get("evidence")
            track_id = str(getattr(track, "track_id", "") or "") or None

            if observation is not None:
                self._scene.observe(observation, track, temporal)
            if evidence is not None and track_id:
                self._scene.add_evidence_to_timeline(
                    track_id,
                    {
                        "type": "jpg",
                        "path": evidence.get("relative_path", ""),
                        "timestamp": str(evidence.get("timestamp") or ""),
                        "camera_id": camera_id,
                    },
                )

            if behavior is not None:
                events = self._scene.process_behavior_result(
                    behavior, camera_id=camera_id, track_id=track_id or ""
                )
                self._events.extend(events)
                self._counts["scene_events"] += len(events)
                if track_id:
                    self._signals_by_track[track_id].extend(
                        tuple(getattr(behavior, "signals", ()) or ())
                    )
                    if getattr(behavior, "risk_event", None) is not None:
                        self._risk_by_track[track_id].append(behavior.risk_event)
                self._register_raw_cases(behavior, camera_id, track_id, evidence)

            created = {
                "scene_events": len(events) if behavior is not None else 0,
                "insights": 0,
                "sequences": 0,
                "raw_cases": 0,
            }
            created["raw_cases"] = self._counts["raw_cases"]

            for sequence in self._scene.build_scene_sequences():
                key = (sequence.track_id, sequence.start_time, sequence.end_time)
                if key in self._sequence_keys:
                    continue
                self._sequence_keys.add(key)
                self._sequences.append(sequence)
                self._counts["sequences"] += 1
                created["sequences"] += 1
                timeline = self._scene.get_evidence_timeline(sequence.track_id)
                signals = tuple(self._signals_by_track.get(sequence.track_id, ()))
                risks = tuple(self._risk_by_track.get(sequence.track_id, ()))
                insight = self._insight.generate_from_scene_sequence(
                    sequence, timeline, signals, risks
                )
                self._insights.append(insight)
                self._queries.index_insight(insight)
                self._queries.index_sequence(sequence)
                self._counts["insights"] += 1
                created["insights"] += 1
            return created

    def _register_raw_cases(
        self,
        behavior: Any,
        camera_id: str,
        track_id: Optional[str],
        evidence: Optional[Dict[str, Any]],
    ) -> None:
        risk_event = getattr(behavior, "risk_event", None)
        for signal in tuple(getattr(behavior, "signals", ()) or ()):
            signal_id = str(getattr(signal, "signal_id", "") or "")
            if not signal_id or signal_id in self._raw_by_signal:
                continue
            refs = tuple(getattr(behavior, "evidence_refs", ()) or ())
            if not refs and evidence is not None:
                refs = (str(evidence.get("relative_path") or ""),)
            risk_score = 0.0
            if risk_event is not None:
                risk_score = float(getattr(risk_event, "risk_score", 0.0) or 0.0)
            if not risk_score:
                risk_score = float(getattr(signal, "rule_score", 0.0) or 0.0)
            raw = RawCase(
                signal_type=str(getattr(signal, "signal_type", "") or ""),
                signal_metadata={
                    "signal_id": signal_id,
                    "rule_id": str(getattr(signal, "rule_id", "") or ""),
                    "rule_score": float(getattr(signal, "rule_score", 0.0) or 0.0),
                    "window_start": str(getattr(signal, "window_start", "") or ""),
                    "window_end": str(getattr(signal, "window_end", "") or ""),
                },
                risk_score=risk_score,
                camera_ids=(camera_id,),
                track_ids=(track_id,) if track_id else (),
                evidence_refs=refs,
                scene_context={
                    "store_id": self._store_id,
                    "organization_id": self._organization_id,
                    "behavior_signals": tuple(
                        str(getattr(item, "signal_type", "") or "")
                        for item in tuple(getattr(behavior, "signals", ()) or ())
                    ),
                },
            )
            self._memory = self._memory.add_raw(raw)
            self._raw_by_signal[signal_id] = raw
            self._counts["raw_cases"] += 1

    # ------------------------------------------------------------------
    # Operator (F)
    # ------------------------------------------------------------------
    def query(self, query: Any) -> Any:
        with self._lock:
            return self._queries.query(query)

    def insights(self) -> Tuple[Any, ...]:
        with self._lock:
            return tuple(self._insights)

    def scene_events(self) -> Tuple[Any, ...]:
        with self._lock:
            return tuple(self._events)

    def scene_sequences(self) -> Tuple[Any, ...]:
        with self._lock:
            return tuple(self._sequences)

    # ------------------------------------------------------------------
    # Learning (G)
    # ------------------------------------------------------------------
    def review_and_learn(self, record: SignalReviewRecord) -> ReviewedCase:
        """Map a human-reviewed record onto the case memory (no auto-promote)."""
        with self._lock:
            label = _classification_to_label(record.human_classification)
            raw = self._raw_by_signal.get(record.signal_id)
            reviewed = ReviewedCase(
                case_id=record.review_id,
                raw_case_id=raw.case_id if raw is not None else record.review_id,
                reviewer_id="operator",
                label=label,
                reviewer_notes=str(record.review_notes or ""),
            )
            self._memory = self._memory.add_reviewed(reviewed)
            self._counts["reviewed_cases"] += 1
            if label == SignalLabel.USEFUL_SIGNAL:
                self._memory = self._memory.promote_to_training(
                    reviewed.case_id, self._dataset_version
                )
                self._counts["training_eligible"] = len(
                    self._memory.get_training_eligible()
                )
            return reviewed

    def build_dataset(self, version: Optional[str] = None) -> FeedbackDataset:
        with self._lock:
            builder = FeedbackDatasetBuilder(
                self._memory, self._datasets._dataset_root
            )
            return builder.build_dataset(
                version or self._dataset_version,
                parent_version=None,
            )

    def policy_manager(self) -> PolicyManager:
        return self._policies

    def current_policy(self) -> Optional[Any]:
        return self._policies.current()

    def case_memory(self) -> CaseMemory:
        return self._memory

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        with self._lock:
            policy = self._policies.current()
            return {
                "store_id": self._store_id,
                "organization_id": self._organization_id,
                "scene_events": self._counts["scene_events"],
                "scene_sequences": self._counts["sequences"],
                "insights": self._counts["insights"],
                "raw_cases": self._counts["raw_cases"],
                "reviewed_cases": self._counts["reviewed_cases"],
                "training_eligible": self._counts["training_eligible"],
                "policy_current_version": policy.version if policy else None,
                "policy_candidates": len(self._policies._candidates),
            }