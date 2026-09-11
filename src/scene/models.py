"""Scene Intelligence models (AG-04 / OC-08..OC-12).

Structured layer over existing certified capabilities:

    ActivityObservation -> SceneObservation
    LocalTrack          -> SceneTrack
    TemporalActivity    -> SceneActivity
    BehaviorResult      -> SceneEvent -> SceneSequence -> EvidenceTimeline

The certified core (ActivityLayer, BehaviorEngine, TemporalActivity,
CrossCameraCorrelation) is never replaced; these models adapt its canonical
contracts into a scene-level representation for operator insights.

Traceability: every model that belongs to a camera carries ``camera_id`` and,
where applicable, ``store_id`` so operator insights can trace back to
store -> cameras -> tracks -> scene events -> evidence -> timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import uuid4


def _utc_now_iso() -> str:
    """Timestamp UTC ISO-8601 (formato canónico del sistema)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _duration_seconds(start: str, end: str) -> float:
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (end_dt - start_dt).total_seconds()
    except (ValueError, TypeError):
        return 0.0


@dataclass(frozen=True)
class SceneObservation:
    """Single observation of an object/entity in a scene at a timestamp.

    Adapts a certified ``ActivityObservation`` (src.observations.activity)
    with optional track context from ``LocalTrack`` (src.temporal.contract).
    """
    observation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    store_id: str = ""
    camera_id: str = ""
    track_id: Optional[str] = None
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x1, y1, x2, y2
    confidence: Optional[float] = None
    object_class: str = "person"
    observation_type: str = ""
    state: str = ""
    observation_ref: str = ""  # source ActivityObservation id
    attributes: dict = field(default_factory=dict)

    @classmethod
    def from_activity_observation(cls, obs, track_id: Optional[str] = None) -> "SceneObservation":
        """Adapt a certified ActivityObservation into a SceneObservation."""
        payload = dict(getattr(obs, "payload", {}) or {})
        bbox = payload.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            bbox = (0, 0, 0, 0)
        else:
            bbox = tuple(int(v) for v in bbox)
        object_class = str(payload.get("class_name") or "person")
        return cls(
            observation_id=str(getattr(obs, "observation_id", "") or ""),
            timestamp_utc=str(getattr(obs, "timestamp", "") or _utc_now_iso()),
            camera_id=str(getattr(obs, "camera_id", "") or ""),
            track_id=track_id,
            bbox=bbox,
            confidence=getattr(obs, "confidence", None),
            object_class=object_class,
            observation_type=str(getattr(obs, "observation_type", "") or ""),
            state=str(getattr(obs, "state", "") or ""),
            observation_ref=str(getattr(obs, "observation_id", "") or ""),
            attributes=payload,
        )


@dataclass(frozen=True)
class SceneTrack:
    """Scene-level track aggregating observations over time.

    Adapts ``LocalTrack`` (src.temporal.contract) which is LOCAL identity:
    valid only within one camera and observation window, never real-person
    identity and never cross-camera re-identification.
    """
    track_id: str
    camera_id: str
    store_id: str = ""
    start_time: str = ""
    end_time: str = ""
    object_class: str = "person"
    status: str = "ACTIVE"
    observations: Tuple[SceneObservation, ...] = ()
    zone_sequence: Tuple[str, ...] = ()
    is_active: bool = True

    @property
    def duration_seconds(self) -> float:
        return _duration_seconds(self.start_time, self.end_time)

    @classmethod
    def from_local_track(cls, track, store_id: str = "") -> "SceneTrack":
        """Adapt a certified LocalTrack into a SceneTrack."""
        status = str(getattr(track, "status", "ACTIVE") or "ACTIVE")
        return cls(
            track_id=str(track.track_id),
            camera_id=str(track.camera_id),
            store_id=store_id,
            start_time=str(getattr(track, "started_at", "") or ""),
            end_time=str(getattr(track, "last_seen_at", "") or ""),
            object_class=str(getattr(track, "object_type", "person") or "person"),
            status=status,
            is_active=status in ("STARTED", "ACTIVE"),
        )


@dataclass(frozen=True)
class SceneActivity:
    """High-level activity within a scene (e.g., PRESENCE, DWELL, TRANSIT).

    Adapts ``TemporalActivity`` (src.temporal.contract) which is GENERIC
    activity (never behavior classification such as theft/intent/threat).
    """
    activity_id: str = field(default_factory=lambda: str(uuid4()))
    track_id: str = ""
    camera_id: str = ""
    store_id: str = ""
    activity_type: str = "PRESENCE"  # PRESENCE, DWELL, TRANSIT, INTERACTION
    zone: str = ""
    start_time: str = ""
    end_time: str = ""
    confidence: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return _duration_seconds(self.start_time, self.end_time)

    @classmethod
    def from_temporal_activity(cls, activity, zone: str = "", store_id: str = "") -> "SceneActivity":
        """Adapt a certified TemporalActivity into a SceneActivity."""
        duration_ms = float(getattr(activity, "duration_ms", 0) or 0)
        return cls(
            activity_id=str(getattr(activity, "activity_id", "") or ""),
            track_id=str(getattr(activity, "track_id", "") or ""),
            camera_id=str(getattr(activity, "source_id", "") or ""),
            store_id=store_id,
            activity_type=cls._map_activity_type(str(getattr(activity, "activity_type", ""))),
            zone=zone,
            start_time=str(getattr(activity, "started_at", "") or ""),
            end_time=str(getattr(activity, "ended_at", "") or getattr(activity, "last_seen_at", "") or ""),
            confidence=getattr(activity, "confidence", None),
            metadata={"duration_seconds": duration_ms / 1000.0},
        )

    @staticmethod
    def _map_activity_type(temporal_type: str) -> str:
        mapping = {
            "PERSON_PRESENCE": "PRESENCE",
            "OBJECT_PRESENCE": "PRESENCE",
            "PRESENCE": "PRESENCE",
            "DWELL": "DWELL",
            "TRANSIT": "TRANSIT",
            "LOITERING": "INTERACTION",
        }
        return mapping.get(temporal_type, "PRESENCE")


@dataclass(frozen=True)
class SceneEvent:
    """Atomic scene event with causal explanation.

    Composed from: SceneActivity + BehaviorSignal + RiskEvent + Evidence.
    Signals are hypotheses, never guilt (explainable behavior contracts).
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    store_id: str = ""
    camera_ids: Tuple[str, ...] = ()
    track_ids: Tuple[str, ...] = ()
    event_type: str = "ACTIVITY_REQUIRES_REVIEW"
    explanation: str = ""
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    uncertainty_score: float = 0.0
    evidence_refs: Tuple[str, ...] = ()  # JPEG/MP4 paths
    scene_activities: Tuple[SceneActivity, ...] = ()
    behavior_signals: Tuple[str, ...] = ()  # signal_type names
    risk_score: Optional[float] = None


@dataclass(frozen=True)
class SceneSequence:
    """Temporal sequence of related SceneEvents (same track across cameras).

    Built from certified cross-camera correlation plus scene events.
    Camera path is topological (DEC-0040); never implies identity.
    """
    sequence_id: str = field(default_factory=lambda: str(uuid4()))
    track_id: str = ""
    store_id: str = ""
    events: Tuple[SceneEvent, ...] = ()
    start_time: str = ""
    end_time: str = ""
    camera_path: Tuple[str, ...] = ()  # ordered camera_ids visited
    zones_traversed: Tuple[str, ...] = ()

    @property
    def duration_seconds(self) -> float:
        return _duration_seconds(self.start_time, self.end_time)


@dataclass(frozen=True)
class EvidenceTimeline:
    """Immutable timeline of evidence for a scene sequence or track.

    Links to persistent JPEG evidence, QW-04 MP4 clips and review records.
    """
    timeline_id: str = field(default_factory=lambda: str(uuid4()))
    sequence_id: str = ""
    track_id: str = ""
    store_id: str = ""
    evidence_items: Tuple[dict, ...] = ()  # {type: "jpg|mp4", path, timestamp, camera_id, event_id}

    def add_evidence(self, item: dict) -> "EvidenceTimeline":
        return EvidenceTimeline(
            timeline_id=self.timeline_id,
            sequence_id=self.sequence_id,
            track_id=self.track_id,
            store_id=self.store_id,
            evidence_items=self.evidence_items + (dict(item),),
        )


@dataclass(frozen=True)
class ZoneConfig:
    """Zone definition for scene intelligence (OC-10).

    Supports both simple rectangles and complex polygons.
    """
    zone_id: str
    zone_name: str
    zone_type: str = "RECTANGLE"  # RECTANGLE | POLYGON | LINE
    polygon: Tuple[Tuple[float, float], ...] = ()  # [(x1,y1), (x2,y2), ...]
    rectangle: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x1, y1, x2, y2
    camera_id: str = ""
    is_restricted: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class InteractionEvent:
    """Person-entity interaction in scene (OC-11).

    Types: person-zone, person-poi (rack/display), person-person (co-location).
    Deterministic heuristics; no new models.
    """
    interaction_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    track_id: str = ""
    camera_id: str = ""
    store_id: str = ""
    interaction_type: str = "ZONE_ENTRY"  # ZONE_ENTRY, ZONE_EXIT, POI_APPROACH, PERSON_PROXIMITY
    target_id: str = ""  # zone_id, poi_id, or other track_id
    duration_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OperatorInsight:
    """Operator-facing insight per AG-05 contract (OC-13).

    No automatic accusation - only ACTIVITY_REQUIRES_REVIEW taxonomy.
    Full traceability to: store, cameras, tracks, scene events, evidence,
    timeline span.
    """
    insight_id: str = field(default_factory=lambda: str(uuid4()))
    organization_id: str = ""
    store_id: str = ""
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    cameras: Tuple[str, ...] = ()
    tracks: Tuple[str, ...] = ()
    scene_events: Tuple[str, ...] = ()
    timeline_span: Tuple[str, str] = ("", "")
    evidence_refs: Tuple[str, ...] = ()
    explanation: str = ""
    reason_for_review: str = "ACTIVITY_REQUIRES_REVIEW"
    priority: str = "MEDIUM"
    uncertainty_score: float = 0.0
    recommended_action: str = ""