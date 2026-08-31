"""Temporal semantic validator to suppress static fixtures (mannequins).

State machine per track:

    New track (1st observation):
        → PERSON_MOVING  (bootstrap default — no classification yet)

    Displacement > threshold observed:
        ever_moved = True
        → PERSON_MOVING

    ever_moved=True, displacement ≤ threshold now:
        → PERSON_STATIONARY  (was moving, now stopped — still a real person)

    No movement ever (ever_moved=False), duration ≥ fixture_persistence_seconds:
        → LIKELY_SCENE_FIXTURE  (static from the start — mannequin/object)

    Insufficient history (< 2 bboxes) and no movement:
        → PERSON_MOVING  (bootstrap — do not downgrade to AMBIGUOUS prematurely)

entry_observed is independent of ever_moved:
    entry_observed = True  when track crosses a configured ENTRY_ZONE.
    entry_observed = False when track appeared inside frame (UNKNOWN origin).
    Used exclusively to set visit_origin, not to classify person state.

AMBIGUOUS_PERSON_LIKE is returned ONLY when required fields are missing
(camera_id / track_id / bbox) — not as a time-based transition.
Time without movement accumulates evidence toward LIKELY_SCENE_FIXTURE, not
toward PERSON_MOVING. The two are never confused.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class ValidationHistory:
    first_seen: float
    last_seen: float
    bboxes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    centroids: List[Tuple[float, float]] = field(default_factory=list)
    classification: str = "PERSON_MOVING"
    # Movement evidence: True once displacement > threshold is observed.
    # Does NOT mean the person entered via a door/zone — that is entry_observed.
    ever_moved: bool = False
    # Entry zone evidence: True when track crossed a configured ENTRY_ZONE.
    # Set externally by the caller that knows zone geometry.
    entry_observed: bool = False

    def centroid(self, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def add_bbox(self, bbox: Tuple[int, int, int, int], now: float):
        self.last_seen = now
        self.bboxes.append(bbox)
        self.centroids.append(self.centroid(bbox))
        # Keep bounded memory (2 seconds at 30 fps ≈ 60 frames)
        if len(self.bboxes) > 60:
            self.bboxes.pop(0)
            self.centroids.pop(0)


class PersonPresenceValidator:
    def __init__(
        self,
        fixture_persistence_seconds: float = 60.0,
        max_centroid_variance: float = 0.05,
        store_state: str = "OPEN",
    ):
        self.fixture_persistence_seconds = fixture_persistence_seconds
        self.max_centroid_variance = max_centroid_variance
        self.store_state = store_state

        # camera_id -> track_id -> ValidationHistory
        self._memory: Dict[str, Dict[str, ValidationHistory]] = {}

    def evaluate_track(
        self,
        track: Any,
        event: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Evaluate a person track and return its semantic presence state.

        Returns one of:
            PERSON_MOVING        — active displacement detected (or bootstrap)
            PERSON_STATIONARY    — ever_moved=True but currently still
            LIKELY_SCENE_FIXTURE — no movement ever, persisted long enough
            AMBIGUOUS_PERSON_LIKE — missing required fields (camera_id/track_id/bbox)

        Note: AMBIGUOUS is ONLY for missing inputs. It is NOT a time-based
        transition. Time without movement → LIKELY_SCENE_FIXTURE, never
        promotes toward PERSON_MOVING.
        """
        camera_id = getattr(track, "camera_id", None)
        track_id = getattr(track, "track_id", None)

        if not camera_id or not track_id:
            return "AMBIGUOUS_PERSON_LIKE"

        bbox = getattr(track, "last_bbox", None)
        if not bbox or len(bbox) != 4:
            return "AMBIGUOUS_PERSON_LIKE"

        now = time.time()

        if camera_id not in self._memory:
            self._memory[camera_id] = {}

        history = self._memory[camera_id].get(track_id)
        if not history:
            history = ValidationHistory(first_seen=now, last_seen=now)
            self._memory[camera_id][track_id] = history

        history.add_bbox(bbox, now)

        duration = now - history.first_seen

        # Use recent history (last 30 frames ~1s at 30fps) for current movement detection
        # Full history is used for fixture detection (duration since first_seen)
        recent_centroids = history.centroids[-30:] if len(history.centroids) > 30 else history.centroids
        
        displacement = 0.0
        if len(recent_centroids) > 1:
            cx_vals = [c[0] for c in recent_centroids]
            cy_vals = [c[1] for c in recent_centroids]

            # Normalize by bounding box size
            w = max(1, bbox[2] - bbox[0])
            h = max(1, bbox[3] - bbox[1])

            var_x = (max(cx_vals) - min(cx_vals)) / w
            var_y = (max(cy_vals) - min(cy_vals)) / h

            displacement = max(var_x, var_y)

        # --- Classification logic ---

        if displacement > self.max_centroid_variance:
            # Active movement detected → record ever_moved, classify as moving
            history.ever_moved = True
            history.classification = "PERSON_MOVING"
            return history.classification

        # No significant displacement at this evaluation
        if history.ever_moved:
            # Person has moved before (ever_moved=True) but is now still.
            # Retains person identity as PERSON_STATIONARY — NOT a fixture.
            # No amount of stillness after movement degrades to LIKELY_SCENE_FIXTURE.
            history.classification = "PERSON_STATIONARY"
        elif len(history.centroids) < 2:
            # Bootstrap: only one observation, no displacement data.
            # Remain at PERSON_MOVING (default) until we have enough history.
            pass  # classification stays "PERSON_MOVING"
        elif duration >= self.fixture_persistence_seconds:
            # Never moved, static for long enough → scene fixture / mannequin
            history.classification = "LIKELY_SCENE_FIXTURE"
        # else: more than one obs, no movement yet, under fixture threshold
        # → remains PERSON_MOVING (bootstrap; evidence insufficient for fixture)

        return history.classification

    def mark_entry_observed(self, camera_id: str, track_id: str) -> None:
        """Mark that a track crossed a configured ENTRY_ZONE for this camera.

        This is INDEPENDENT of ever_moved. It drives visit_origin, not
        person state classification.
        """
        cam_tracks = self._memory.get(camera_id, {})
        history = cam_tracks.get(str(track_id))
        if history is not None:
            history.entry_observed = True

    def is_entry_observed(self, camera_id: str, track_id: str) -> bool:
        """Return True if this track's entry via ENTRY_ZONE has been confirmed."""
        cam_tracks = self._memory.get(camera_id, {})
        history = cam_tracks.get(str(track_id))
        return bool(history and history.entry_observed)

    def update_store_state(self, state: str):
        self.store_state = state

    def cleanup_stale(self, timeout_s: float = 300.0):
        now = time.time()
        for cam, tracks in list(self._memory.items()):
            for tid, hist in list(tracks.items()):
                if now - hist.last_seen > timeout_s:
                    del tracks[tid]
            if not tracks:
                del self._memory[cam]
