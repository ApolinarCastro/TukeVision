"""Spatial Entity State Manager.

Maintains the physical/spatial state of entities over time, computing velocity,
direction, and maintaining a bounded trajectory.
"""

from typing import Dict, Optional, List, Tuple
import datetime
import math
import collections

from src.spatial.contract import (
    StoreCoordinate,
    SpatialEntityState,
    SpatialTrajectoryPoint,
    ObservationState,
    SpatialProvenance
)
from src.spatial.homography import HomographyEngine


class SpatialStateManager:
    """Manages the spatial state of entities in the store."""

    def __init__(self, homography_engine: HomographyEngine, max_trajectory_points: int = 100):
        self._engine = homography_engine
        self._max_points = max_trajectory_points
        
        # Internal state storage
        self._states: Dict[str, SpatialEntityState] = {}
        
    def _calculate_velocity_and_direction(
        self,
        prev_pos: StoreCoordinate,
        curr_pos: StoreCoordinate,
        prev_time: str,
        curr_time: str
    ) -> Tuple[Tuple[float, float], float]:
        """Calculates velocity vector (vx, vy) in m/s and direction in degrees."""
        try:
            pt = datetime.datetime.fromisoformat(prev_time.replace("Z", "+00:00"))
            ct = datetime.datetime.fromisoformat(curr_time.replace("Z", "+00:00"))
            dt = (ct - pt).total_seconds()
        except ValueError:
            dt = 0
            
        if dt <= 0:
            return (0.0, 0.0), 0.0
            
        vx = (curr_pos.x - prev_pos.x) / dt
        vy = (curr_pos.y - prev_pos.y) / dt
        
        # Direction (0 is +x, 90 is +y)
        angle_rad = math.atan2(vy, vx)
        angle_deg = math.degrees(angle_rad) % 360.0
        
        return (vx, vy), angle_deg

    def update_observation(
        self,
        entity_id: str,
        camera_id: str,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        timestamp: str
    ) -> Optional[SpatialEntityState]:
        """Process a new detection/track observation for an entity."""
        
        # 1. Estimate Foot Point
        foot_px = self._engine.estimate_foot_point(bbox)
        
        # 2. Project to Store Coordinate
        store_coord = self._engine.project_image_to_store(camera_id, foot_px[0], foot_px[1])
        if not store_coord:
            return None # Uncalibrated camera, cannot update spatial state
            
        # 3. Trajectory Point
        point = SpatialTrajectoryPoint(
            x=store_coord.x,
            y=store_coord.y,
            timestamp=timestamp,
            source_camera=camera_id,
            confidence=confidence,
            observation_state=ObservationState.LIVE_OBSERVED
        )
        
        # 4. Update or Create State
        if entity_id not in self._states:
            state = SpatialEntityState(
                entity_id=entity_id,
                current_store_position=store_coord,
                previous_store_position=None,
                velocity_vector=(0.0, 0.0),
                direction_deg=0.0,
                current_zone=None, # Zone assignment handled by another module/slice
                previous_zone=None,
                active_camera=camera_id,
                candidate_cameras=[],
                trajectory=[point],
                observation_state=ObservationState.LIVE_OBSERVED,
                confidence=confidence,
                freshness=1.0,
                last_observed_at=timestamp
            )
            self._states[entity_id] = state
        else:
            state = self._states[entity_id]
            prev_pos = state.current_store_position
            prev_time = state.last_observed_at
            
            # Compute dynamics
            velocity, direction = self._calculate_velocity_and_direction(
                prev_pos, store_coord, prev_time, timestamp
            )
            
            # Update history
            state.trajectory.append(point)
            if len(state.trajectory) > self._max_points:
                state.trajectory.pop(0) # Keep bounded
                
            # Update state properties
            state.previous_store_position = prev_pos
            state.current_store_position = store_coord
            state.velocity_vector = velocity
            state.direction_deg = direction
            state.active_camera = camera_id
            state.last_observed_at = timestamp
            state.observation_state = ObservationState.LIVE_OBSERVED
            state.confidence = confidence
            state.freshness = 1.0 # Fresh since it's just observed
            
        return state

    def get_state(self, entity_id: str) -> Optional[SpatialEntityState]:
        return self._states.get(entity_id)

    def remove_entity(self, entity_id: str):
        if entity_id in self._states:
            del self._states[entity_id]
