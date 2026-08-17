"""Serializable non-identity contracts for cross-camera hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

CANDIDATE = "CANDIDATE"
AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True)
class TrackReference:
    camera_id: str
    track_id: str
    object_type: str
    start_time: str
    end_time: str
    evidence_refs: Tuple[str, ...] = ()

    @classmethod
    def from_track(cls, track: Any) -> "TrackReference":
        refs = getattr(track, "evidence_refs", {}) or {}
        ordered = []
        for key in ("first", "latest", "best"):
            value = refs.get(key)
            if value and value not in ordered:
                ordered.append(str(value))
        return cls(
            camera_id=str(track.camera_id), track_id=str(track.track_id),
            object_type=str(track.object_type), start_time=str(track.started_at),
            end_time=str(track.last_seen_at), evidence_refs=tuple(ordered),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id, "track_id": self.track_id,
            "object_type": self.object_type, "start_time": self.start_time,
            "end_time": self.end_time, "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class TransitionCandidate:
    candidate_id: str
    source_camera_id: str
    source_track_id: str
    target_camera_id: str
    target_track_id: str
    source_end_time: str
    target_start_time: str
    time_delta_seconds: float
    evidence_refs: Tuple[str, ...]
    score_components: Tuple[Tuple[str, float], ...]
    correlation_score: float
    status: str = CANDIDATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_camera_id": self.source_camera_id,
            "source_track_id": self.source_track_id,
            "target_camera_id": self.target_camera_id,
            "target_track_id": self.target_track_id,
            "source_end_time": self.source_end_time,
            "target_start_time": self.target_start_time,
            "time_delta_seconds": self.time_delta_seconds,
            "evidence_refs": list(self.evidence_refs),
            "score_components": dict(self.score_components),
            "correlation_score": self.correlation_score,
            "status": self.status,
        }


@dataclass(frozen=True)
class CrossCameraLink:
    link_id: str
    candidate_id: str
    source_track_ref: str
    target_track_ref: str
    source_camera_id: str
    target_camera_id: str
    time_delta_seconds: float
    score_components: Tuple[Tuple[str, float], ...]
    correlation_score: float
    evidence_refs: Tuple[str, ...]
    status: str = CANDIDATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": self.link_id, "candidate_id": self.candidate_id,
            "source_track_ref": self.source_track_ref,
            "target_track_ref": self.target_track_ref,
            "source_camera_id": self.source_camera_id,
            "target_camera_id": self.target_camera_id,
            "time_delta_seconds": self.time_delta_seconds,
            "score_components": dict(self.score_components),
            "correlation_score": self.correlation_score,
            "evidence_refs": list(self.evidence_refs), "status": self.status,
        }


@dataclass(frozen=True)
class Trajectory:
    trajectory_id: str
    nodes: Tuple[TrackReference, ...]
    edges: Tuple[CrossCameraLink, ...]
    start_time: str
    latest_time: str
    evidence_refs: Tuple[str, ...]
    correlation_metadata: Tuple[Tuple[str, Any], ...]
    status: str = CANDIDATE

    @property
    def camera_sequence(self) -> Tuple[str, ...]:
        return tuple(node.camera_id for node in self.nodes)

    @property
    def track_sequence(self) -> Tuple[str, ...]:
        return tuple(node.track_id for node in self.nodes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "camera_sequence": list(self.camera_sequence),
            "track_sequence": list(self.track_sequence),
            "start_time": self.start_time, "latest_time": self.latest_time,
            "evidence_refs": list(self.evidence_refs),
            "correlation_metadata": dict(self.correlation_metadata),
            "status": self.status,
        }


@dataclass(frozen=True)
class CorrelationResult:
    candidates: Tuple[TransitionCandidate, ...] = ()
    link: Optional[CrossCameraLink] = None
    trajectory: Optional[Trajectory] = None
