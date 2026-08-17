"""Deterministic temporal/topological correlator; correlation is not identity."""

from __future__ import annotations

import hashlib
from collections import OrderedDict, defaultdict, deque
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.correlation.contracts import (
    AMBIGUOUS, CANDIDATE, CorrelationResult, CrossCameraLink,
    TrackReference, Trajectory, TransitionCandidate,
)
from src.correlation.topology import CameraTopology, TRANSITION_ALLOWED


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{digest}"


def _unique(values) -> Tuple[str, ...]:
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return tuple(out)


class CrossCameraCorrelator:
    """Build bounded trajectory hypotheses from independent local tracks."""

    def __init__(
        self, topology: CameraTopology, *, score_weights: Dict[str, float],
        max_active_trajectories: int = 32,
        max_candidates_per_camera_pair: int = 16,
        candidate_ttl_seconds: float = 120.0,
        trajectory_ttl_seconds: float = 600.0,
        max_tracks: int = 256,
    ) -> None:
        self._topology = topology
        self._weights = self._validated_weights(score_weights)
        for name, value in (
            ("max_active_trajectories", max_active_trajectories),
            ("max_candidates_per_camera_pair", max_candidates_per_camera_pair),
            ("max_tracks", max_tracks),
        ):
            if int(value) < 1:
                raise ValueError(f"{name} debe ser positivo")
        if candidate_ttl_seconds <= 0 or trajectory_ttl_seconds <= 0:
            raise ValueError("TTL debe ser positivo")
        self._max_trajectories = int(max_active_trajectories)
        self._max_candidates = int(max_candidates_per_camera_pair)
        self._candidate_ttl = float(candidate_ttl_seconds)
        self._trajectory_ttl = float(trajectory_ttl_seconds)
        self._max_tracks = int(max_tracks)
        self._tracks: OrderedDict[Tuple[str, str], Tuple[TrackReference, Dict[str, Any]]] = OrderedDict()
        self._candidates: Dict[Tuple[str, str], Deque[TransitionCandidate]] = defaultdict(
            lambda: deque(maxlen=self._max_candidates)
        )
        self._trajectories: OrderedDict[str, Trajectory] = OrderedDict()
        self._track_trajectory: Dict[Tuple[str, str], str] = {}
        self._incoming = set()
        self._outgoing = set()
        self._closed = False

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "CrossCameraCorrelator":
        block = config.get("correlation") if isinstance(config, dict) else None
        if not isinstance(block, dict) or not block.get("enabled", False):
            raise ValueError("correlation debe estar habilitado")
        return cls(
            CameraTopology.from_config(config),
            score_weights=dict(block.get("score_weights") or {}),
            max_active_trajectories=int(block.get("max_active_trajectories", 32)),
            max_candidates_per_camera_pair=int(block.get("max_candidates_per_camera_pair", 16)),
            candidate_ttl_seconds=float(block.get("candidate_ttl_seconds", 120.0)),
            trajectory_ttl_seconds=float(block.get("trajectory_ttl_seconds", 600.0)),
            max_tracks=int(block.get("max_tracks", 256)),
        )

    @staticmethod
    def _validated_weights(weights: Dict[str, float]) -> Dict[str, float]:
        values = {name: float(weights.get(name, default)) for name, default in (
            ("temporal", 0.7), ("topology", 0.3), ("direction", 0.0)
        )}
        if any(value < 0 for value in values.values()) or sum(values.values()) <= 0:
            raise ValueError("score_weights inválidos")
        total = sum(values.values())
        return {name: value / total for name, value in values.items()}

    def ingest(self, track: Any, activity: Any = None, metadata: Optional[Dict[str, Any]] = None) -> CorrelationResult:
        if self._closed:
            raise RuntimeError("correlator cerrado")
        target = TrackReference.from_track(track)
        target_key = (target.camera_id, target.track_id)
        now = _time(target.start_time)
        self._purge(now)
        self._tracks[target_key] = (target, dict(metadata or {}))
        self._tracks.move_to_end(target_key)
        while len(self._tracks) > self._max_tracks:
            evicted_key, _ = self._tracks.popitem(last=False)
            self._drop_track_state(evicted_key)

        valid = []
        for source_key, (source, source_metadata) in list(self._tracks.items()):
            if source_key == target_key or source.camera_id == target.camera_id:
                continue
            if source_key in self._outgoing:
                continue
            rule = self._topology.rule(source.camera_id, target.camera_id)
            if rule is None or self._topology.transition_state(source.camera_id, target.camera_id) != TRANSITION_ALLOWED:
                continue
            if source.object_type != target.object_type:
                continue
            delta = (_time(target.start_time) - _time(source.end_time)).total_seconds()
            if delta < rule.min_transition_seconds or delta > rule.max_transition_seconds:
                continue
            target_metadata = dict(metadata or {})
            components = self._components(delta, rule, source_metadata, target_metadata)
            score = round(sum(self._weights[name] * components[f"{name}_score"] for name in self._weights), 6)
            evidence = _unique(source.evidence_refs + target.evidence_refs)
            candidate = TransitionCandidate(
                candidate_id=_stable_id("CAND", source.camera_id, source.track_id, target.camera_id, target.track_id, source.end_time, target.start_time),
                source_camera_id=source.camera_id, source_track_id=source.track_id,
                target_camera_id=target.camera_id, target_track_id=target.track_id,
                source_end_time=source.end_time, target_start_time=target.start_time,
                time_delta_seconds=delta, evidence_refs=evidence,
                score_components=tuple(components.items()), correlation_score=score,
            )
            valid.append((candidate, source, source_key))

        if len(valid) > 1:
            ambiguous = tuple(replace(item[0], status=AMBIGUOUS) for item in valid)
            for candidate in ambiguous:
                self._remember_candidate(candidate)
            return CorrelationResult(candidates=ambiguous)
        if not valid:
            return CorrelationResult()

        candidate, source, source_key = valid[0]
        self._remember_candidate(candidate)
        if source_key in self._outgoing or target_key in self._incoming:
            return CorrelationResult(candidates=(candidate,))
        link = CrossCameraLink(
            link_id=_stable_id("LINK", candidate.candidate_id),
            candidate_id=candidate.candidate_id,
            source_track_ref=source.track_id, target_track_ref=target.track_id,
            source_camera_id=source.camera_id, target_camera_id=target.camera_id,
            time_delta_seconds=candidate.time_delta_seconds,
            score_components=candidate.score_components,
            correlation_score=candidate.correlation_score,
            evidence_refs=candidate.evidence_refs,
        )
        trajectory = self._link(source, source_key, target, target_key, link)
        self._outgoing.add(source_key)
        self._incoming.add(target_key)
        return CorrelationResult(candidates=(candidate,), link=link, trajectory=trajectory)

    def _components(self, delta, rule, source_metadata, target_metadata):
        span = rule.max_transition_seconds - rule.min_transition_seconds
        temporal = 1.0 if span == 0 else 1.0 - ((delta - rule.min_transition_seconds) / span)
        temporal = round(max(0.0, min(1.0, temporal)), 6)
        direction = 1.0
        if rule.direction:
            direction = 1.0 if (
                source_metadata.get("direction") == rule.direction
                or target_metadata.get("direction") == rule.direction
            ) else 0.0
        return {
            "temporal_score": temporal,
            "topology_score": round(rule.weight, 6),
            "direction_score": direction,
        }

    def _remember_candidate(self, candidate: TransitionCandidate) -> None:
        self._candidates[(candidate.source_camera_id, candidate.target_camera_id)].append(candidate)

    def _link(self, source, source_key, target, target_key, link):
        trajectory_id = self._track_trajectory.get(source_key)
        if trajectory_id and trajectory_id in self._trajectories:
            current = self._trajectories[trajectory_id]
            nodes = current.nodes + (target,)
            edges = current.edges + (link,)
            evidence = _unique(current.evidence_refs + target.evidence_refs)
        else:
            trajectory_id = _stable_id("TRAJ", link.link_id)
            nodes = (source, target)
            edges = (link,)
            evidence = _unique(source.evidence_refs + target.evidence_refs)
        trajectory = Trajectory(
            trajectory_id=trajectory_id, nodes=nodes, edges=edges,
            start_time=nodes[0].start_time, latest_time=target.end_time,
            evidence_refs=evidence,
            correlation_metadata=(("method", "temporal_topological"), ("link_count", len(edges))),
        )
        self._trajectories[trajectory_id] = trajectory
        self._trajectories.move_to_end(trajectory_id)
        self._track_trajectory[source_key] = trajectory_id
        self._track_trajectory[target_key] = trajectory_id
        while len(self._trajectories) > self._max_trajectories:
            old_id, _ = self._trajectories.popitem(last=False)
            self._drop_trajectory_refs(old_id)
        return trajectory

    def _purge(self, now: datetime) -> None:
        for pair in list(self._candidates):
            kept = [candidate for candidate in self._candidates[pair]
                    if (now - _time(candidate.target_start_time)).total_seconds() <= self._candidate_ttl]
            self._candidates[pair] = deque(kept, maxlen=self._max_candidates)
            if not kept:
                del self._candidates[pair]
        for trajectory_id, trajectory in list(self._trajectories.items()):
            if (now - _time(trajectory.latest_time)).total_seconds() > self._trajectory_ttl:
                del self._trajectories[trajectory_id]
                self._drop_trajectory_refs(trajectory_id)
        for key, (reference, _) in list(self._tracks.items()):
            if (now - _time(reference.end_time)).total_seconds() > self._candidate_ttl:
                del self._tracks[key]
                self._drop_track_state(key)

    def _drop_track_state(self, key: Tuple[str, str]) -> None:
        self._incoming.discard(key)
        self._outgoing.discard(key)
        self._track_trajectory.pop(key, None)

    def _drop_trajectory_refs(self, trajectory_id: str) -> None:
        for key, value in list(self._track_trajectory.items()):
            if value == trajectory_id:
                del self._track_trajectory[key]

    def trajectories(self) -> Tuple[Trajectory, ...]:
        return tuple(self._trajectories.values())

    def metrics(self) -> Dict[str, int]:
        return {
            "track_count": len(self._tracks),
            "candidate_count": sum(len(items) for items in self._candidates.values()),
            "trajectory_count": len(self._trajectories),
            "association_count": len(self._incoming) + len(self._outgoing),
        }

    def reset(self) -> None:
        self._tracks.clear()
        self._candidates.clear()
        self._trajectories.clear()
        self._track_trajectory.clear()
        self._incoming.clear()
        self._outgoing.clear()

    def close(self) -> None:
        self.reset()
        self._closed = True


def build_correlator(config: Dict[str, Any]) -> Optional[CrossCameraCorrelator]:
    block = config.get("correlation") if isinstance(config, dict) else None
    if not isinstance(block, dict) or not block.get("enabled", False):
        return None
    return CrossCameraCorrelator.from_config(config)
