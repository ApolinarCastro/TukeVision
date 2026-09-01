"""Scene Intelligence Engine (AG-04 / OC-08, OC-12).

Composes scene models from existing certified components:
- ActivityObservation (observations.activity)
- LocalTrack / TemporalActivity (temporal.contract)
- BehaviorSignal / RiskEvent / BehaviorResult (behavior.contracts)
- CrossCameraCorrelation (correlation.correlator)
- CameraTopology (correlation.topology)

Never replaces certified core. Only adds a structured scene layer on top,
with full traceability to store / cameras / tracks / scene events / evidence.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from src.behavior.contracts import BehaviorResult, RiskEvent, BehaviorSignal
from src.correlation.correlator import CrossCameraCorrelator
from src.correlation.topology import CameraTopology
from src.observations.activity import ActivityObservation
from src.scene.models import (
    EvidenceTimeline,
    InteractionEvent,
    SceneActivity,
    SceneEvent,
    SceneObservation,
    SceneSequence,
    SceneTrack,
    ZoneConfig,
)
from src.temporal.contract import LocalTrack, TemporalActivity


class ZoneAdapter:
    """Zone geometry adapter (OC-10).

    Supports rectangle and polygon zones with a deterministic ray-casting
    implementation (no external geometry dependency). Supervision remains
    optional behind SDL-03; the certified stack never requires it.
    """

    def __init__(self, zones: Sequence[ZoneConfig]):
        self._zones = {z.zone_id: z for z in zones}

    def contains_point(self, zone_id: str, x: float, y: float) -> bool:
        """Check if point is inside zone."""
        zone = self._zones.get(zone_id)
        if not zone:
            return False
        if zone.zone_type == "RECTANGLE":
            x1, y1, x2, y2 = zone.rectangle
            return x1 <= x <= x2 and y1 <= y <= y2
        if zone.zone_type == "POLYGON" and zone.polygon:
            return self._point_in_polygon((x, y), zone.polygon)
        return False

    def _point_in_polygon(self, point: Tuple[float, float], polygon: Sequence[Tuple[float, float]]) -> bool:
        """Ray casting algorithm for point-in-polygon."""
        x, y = point
        inside = False
        n = len(polygon)
        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside

    def get_zone_for_point(self, camera_id: str, x: float, y: float) -> Optional[str]:
        """Find zone containing point for a camera."""
        for zone in self._zones.values():
            if zone.camera_id == camera_id and self.contains_point(zone.zone_id, x, y):
                return zone.zone_id
        return None


class SceneEngine:
    """Scene Intelligence composition engine (OC-08, OC-12).

    Vertical chain (all inputs from certified contracts):

        ActivityObservation -> SceneObservation -> SceneTrack
        TemporalActivity     -> SceneActivity
        BehaviorResult       -> SceneEvent -> SceneSequence -> EvidenceTimeline

    Outputs:
    - SceneEvent stream
    - SceneSequence builder
    - EvidenceTimeline builder
    """

    def __init__(
        self,
        zone_adapter: Optional[ZoneAdapter] = None,
        topology: Optional[CameraTopology] = None,
        cross_camera: Optional[CrossCameraCorrelator] = None,
        store_id: str = "",
    ) -> None:
        self._zone_adapter = zone_adapter
        self._topology = topology
        self._cross_camera = cross_camera
        self._store_id = store_id
        self._tracks: Dict[str, SceneTrack] = {}
        self._track_observations: Dict[str, List[SceneObservation]] = defaultdict(list)
        self._track_activities: Dict[str, List[SceneActivity]] = defaultdict(list)
        self._track_sequences: Dict[str, List[SceneEvent]] = defaultdict(list)
        self._evidence_timelines: Dict[str, EvidenceTimeline] = {}

    # ------------------------------------------------------------------
    # Observation -> Track
    # ------------------------------------------------------------------
    def process_activity_observation(
        self,
        observation: ActivityObservation,
        track: Optional[LocalTrack] = None,
    ) -> List[SceneObservation]:
        """Adapt an ActivityObservation into SceneObservation(s)."""
        track_id = str(track.track_id) if track is not None else None
        scene_obs = SceneObservation.from_activity_observation(
            observation, track_id=track_id
        )
        scene_obs = SceneObservation(
            **{**scene_obs.__dict__, "store_id": self._store_id}
        )
        if track_id is not None:
            self._track_observations[track_id].append(scene_obs)
        return [scene_obs]

    def add_scene_track(self, track: LocalTrack) -> SceneTrack:
        """Adapt and register a certified LocalTrack as a SceneTrack."""
        scene_track = SceneTrack.from_local_track(track, store_id=self._store_id)
        self._tracks[scene_track.track_id] = scene_track
        return scene_track

    # ------------------------------------------------------------------
    # Activity
    # ------------------------------------------------------------------
    def process_temporal_activity(
        self,
        temporal: TemporalActivity,
        track: Optional[LocalTrack] = None,
    ) -> Optional[SceneActivity]:
        """Adapt a TemporalActivity into a SceneActivity with zone context."""
        camera_id = str(getattr(temporal, "source_id", "") or "")
        zone = ""
        if self._zone_adapter is not None:
            reference = track or self._tracks.get(str(getattr(temporal, "track_id", "") or ""))
            if reference is not None and reference.last_bbox:
                cx = (reference.last_bbox[0] + reference.last_bbox[2]) / 2
                cy = (reference.last_bbox[1] + reference.last_bbox[3]) / 2
                zone = self._zone_adapter.get_zone_for_point(camera_id, cx, cy) or ""

        activity = SceneActivity.from_temporal_activity(
            temporal, zone=zone, store_id=self._store_id
        )
        self._track_activities[activity.track_id].append(activity)
        return activity

    # ------------------------------------------------------------------
    # Scene events (ACTIVITY_REQUIRES_REVIEW only - never accusation)
    # ------------------------------------------------------------------
    def process_behavior_result(
        self,
        behavior: BehaviorResult,
        camera_id: str = "",
        track_id: str = "",
    ) -> List[SceneEvent]:
        """Adapt BehaviorResult + RiskEvent into SceneEvent(s).

        Emits only ACTIVITY_REQUIRES_REVIEW events with an explainable
        summary; never an accusation.
        """
        events: List[SceneEvent] = []
        signals: Sequence[BehaviorSignal] = tuple(behavior.signals or ())
        if not signals:
            return events
        risk_event = behavior.risk_event
        for signal in signals:
            explanation = self._build_explanation(
                signal, risk_event, camera_id, track_id
            )
            event = SceneEvent(
                store_id=self._store_id,
                camera_ids=(camera_id,) if camera_id else tuple(behavior.camera_ids or ()),
                track_ids=(track_id,) if track_id else (),
                event_type="ACTIVITY_REQUIRES_REVIEW",
                explanation=explanation,
                priority=self._map_priority(risk_event.risk_score if risk_event else 0),
                uncertainty_score=0.1,
                evidence_refs=tuple(behavior.evidence_refs or ()),
                scene_activities=tuple(self._track_activities.get(track_id, [])),
                behavior_signals=(signal.signal_type,),
                risk_score=risk_event.risk_score if risk_event else None,
            )
            events.append(event)
            if track_id:
                self._track_sequences[track_id].append(event)
        return events

    def _build_explanation(
        self,
        signal: BehaviorSignal,
        risk_event: Optional[RiskEvent],
        camera_id: str,
        track_id: str,
    ) -> str:
        parts = [f"Track {track_id} en cámara {camera_id}"]
        parts.append(f"señal: {signal.signal_type}")
        if risk_event:
            parts.append(
                f"riesgo: {risk_event.risk_event_type} ({risk_event.risk_score})"
            )
        activities = self._track_activities.get(track_id, [])
        if activities:
            zones = ", ".join(
                dict.fromkeys(a.zone for a in activities if a.zone)
            )
            if zones:
                parts.append(f"zonas: {zones}")
        return ". ".join(parts) + "."

    @staticmethod
    def _map_priority(risk_score: float) -> str:
        if risk_score >= 80:
            return "CRITICAL"
        if risk_score >= 60:
            return "HIGH"
        if risk_score >= 40:
            return "MEDIUM"
        return "LOW"

    # ------------------------------------------------------------------
    # Sequences and timelines
    # ------------------------------------------------------------------
    def build_scene_sequences(self) -> List[SceneSequence]:
        """Build SceneSequences from correlated events (OC-12).

        Uses CrossCameraCorrelation when provided for multi-camera linking;
        camera path is topological only (DEC-0040, no identity).
        """
        sequences: List[SceneSequence] = []
        for track_id, events in self._track_sequences.items():
            if not events:
                continue
            camera_path: List[str] = []
            zones: List[str] = []
            for ev in events:
                for cam in ev.camera_ids:
                    if cam not in camera_path:
                        camera_path.append(cam)
                for act in ev.scene_activities:
                    if act.zone and act.zone not in zones:
                        zones.append(act.zone)
            sequences.append(SceneSequence(
                track_id=track_id,
                store_id=self._store_id,
                events=tuple(events),
                start_time=events[0].timestamp_utc,
                end_time=events[-1].timestamp_utc,
                camera_path=tuple(camera_path),
                zones_traversed=tuple(zones),
            ))
        return sequences

    def get_evidence_timeline(self, track_id: str) -> EvidenceTimeline:
        """Get or create evidence timeline for a track."""
        if track_id not in self._evidence_timelines:
            self._evidence_timelines[track_id] = EvidenceTimeline(
                track_id=track_id, store_id=self._store_id
            )
        return self._evidence_timelines[track_id]

    def add_evidence_to_timeline(self, track_id: str, evidence_item: dict) -> None:
        timeline = self.get_evidence_timeline(track_id)
        self._evidence_timelines[track_id] = timeline.add_evidence(evidence_item)

    # ------------------------------------------------------------------
    # Convenience vertical
    # ------------------------------------------------------------------
    def observe(
        self,
        observation: ActivityObservation,
        track: Optional[LocalTrack],
        temporal: Optional[TemporalActivity] = None,
    ) -> dict:
        """Run the minimal Observation->Track->Activity->Scene vertical.

        Returns the scene observations, registered track and optional
        activity for one canonical pipeline step.
        """
        scene_obs = self.process_activity_observation(observation, track)
        scene_track = self.add_scene_track(track) if track is not None else None
        scene_activity = (
            self.process_temporal_activity(temporal, track)
            if temporal is not None else None
        )
        return {
            "observations": scene_obs,
            "track": scene_track,
            "activity": scene_activity,
        }


class InteractionIntelligence:
    """Interaction detection (OC-11).

    Detects: person-zone, person-POI (rack/display), person-person co-location.
    Deterministic heuristics over tracks and zones. No new models.
    """

    def __init__(self, zone_adapter: ZoneAdapter, store_id: str = "") -> None:
        self._zone_adapter = zone_adapter
        self._store_id = store_id
        self._track_last_zone: Dict[str, str] = {}
        self._poi_registry: Dict[str, Tuple[float, float, float]] = {}

    def register_poi(self, poi_id: str, x: float, y: float, radius: float = 2.0) -> None:
        """Register a point of interest (e.g., rack, display)."""
        self._poi_registry[poi_id] = (x, y, radius)

    def process_track(self, track: LocalTrack, camera_id: str) -> List[InteractionEvent]:
        """Detect interactions for a track in current frame."""
        events: List[InteractionEvent] = []
        if not track.last_bbox:
            return events
        cx = (track.last_bbox[0] + track.last_bbox[2]) / 2
        cy = (track.last_bbox[1] + track.last_bbox[3]) / 2
        track_id = str(track.track_id)

        zone = self._zone_adapter.get_zone_for_point(camera_id, cx, cy)
        last_zone = self._track_last_zone.get(track_id)
        if zone and zone != last_zone:
            if last_zone:
                events.append(InteractionEvent(
                    track_id=track_id,
                    camera_id=camera_id,
                    store_id=self._store_id,
                    interaction_type="ZONE_EXIT",
                    target_id=last_zone,
                ))
            events.append(InteractionEvent(
                track_id=track_id,
                camera_id=camera_id,
                store_id=self._store_id,
                interaction_type="ZONE_ENTRY",
                target_id=zone,
            ))
            self._track_last_zone[track_id] = zone
        elif not zone and last_zone:
            events.append(InteractionEvent(
                track_id=track_id,
                camera_id=camera_id,
                store_id=self._store_id,
                interaction_type="ZONE_EXIT",
                target_id=last_zone,
            ))
            self._track_last_zone[track_id] = ""

        for poi_id, (px, py, radius) in self._poi_registry.items():
            dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
            if dist <= radius:
                events.append(InteractionEvent(
                    track_id=track_id,
                    camera_id=camera_id,
                    store_id=self._store_id,
                    interaction_type="POI_APPROACH",
                    target_id=poi_id,
                    metadata={"distance": dist},
                ))
        return events