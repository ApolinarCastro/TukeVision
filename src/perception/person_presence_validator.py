"""Temporal semantic validator to suppress static fixtures (mannequins)."""
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
    
    def centroid(self, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def add_bbox(self, bbox: Tuple[int, int, int, int], now: float):
        self.last_seen = now
        self.bboxes.append(bbox)
        self.centroids.append(self.centroid(bbox))
        # Keep bounded memory
        if len(self.bboxes) > 60:
            self.bboxes.pop(0)
            self.centroids.pop(0)

class PersonPresenceValidator:
    def __init__(
        self,
        fixture_persistence_seconds: float = 60.0,
        max_centroid_variance: float = 0.05,
        store_state: str = "OPEN"
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
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Evaluate a person track and return semantic presence type."""
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
        
        displacement = 0.0
        # Calculate displacement if enough history exists
        if len(history.centroids) > 1:
            cx_vals = [c[0] for c in history.centroids]
            cy_vals = [c[1] for c in history.centroids]
            
            # Simple bounding box size for normalization
            w = max(1, bbox[2] - bbox[0])
            h = max(1, bbox[3] - bbox[1])
            
            var_x = (max(cx_vals) - min(cx_vals)) / w
            var_y = (max(cy_vals) - min(cy_vals)) / h
            
            displacement = max(var_x, var_y)
            
        # Rule 11: Fixture invalidation if significant movement occurs
        if displacement > self.max_centroid_variance:
            history.classification = "PERSON_MOVING"
            # If store is closed, unexpected activity
            if self.store_state == "CLOSED":
                # Let the system handle UNEXPECTED_HUMAN_ACTIVITY higher up or here
                pass
            return history.classification
            
        # If displacement is negligible and persistence is long -> fixture
        if duration >= self.fixture_persistence_seconds:
            history.classification = "LIKELY_SCENE_FIXTURE"
        elif duration > 5.0 and displacement <= self.max_centroid_variance:
            # Stopped for a short time, could be a real person standing still
            history.classification = "PERSON_STATIONARY"
        
        return history.classification

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
