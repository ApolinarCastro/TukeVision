"""Multicamera Handoff Engine (Topological).

Predicts candidate cameras for an entity when it approaches the edge
of its active camera's coverage, based on spatial trajectory, velocity,
and viewshed intersections.
"""

from typing import List, Optional
import math
import logging

from src.spatial.contract import SpatialEntityState, ObservationState
from src.spatial.viewshed import ViewshedEngine

logger = logging.getLogger("tukevision.spatial.handoff")

class HandoffEngine:
    def __init__(self, viewshed_engine: ViewshedEngine, edge_distance_threshold_m: float = 1.5):
        self._viewshed = viewshed_engine
        self._threshold = edge_distance_threshold_m

    def _distance_to_segment(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate the shortest distance from point (px,py) to a line segment (x1,y1)-(x2,y2)."""
        l2 = (x2 - x1)**2 + (y2 - y1)**2
        if l2 == 0:
            return math.dist((px, py), (x1, y1))
            
        t = max(0, min(1, ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / l2))
        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)
        
        return math.dist((px, py), (proj_x, proj_y))

    def _distance_to_polygon_edge(self, px: float, py: float, polygon: List) -> float:
        """Calculate the shortest distance from a point to any edge of a polygon."""
        if not polygon:
            return float('inf')
            
        min_dist = float('inf')
        n = len(polygon)
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            dist = self._distance_to_segment(px, py, p1.x, p1.y, p2.x, p2.y)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def evaluate_handoff(self, entity: SpatialEntityState, prediction_seconds: float = 2.0) -> List[str]:
        """
        Evaluates if the entity is near an edge of its active camera coverage.
        If so, predicts candidate cameras based on velocity and overlapping viewsheds.
        """
        if not entity.active_camera:
            return []
            
        active_cam = self._viewshed.get_camera_coverage(entity.active_camera)
        if not active_cam or not active_cam.coverage.is_active:
            return []
            
        px, py = entity.current_store_position.x, entity.current_store_position.y
        dist_to_edge = self._distance_to_polygon_edge(px, py, active_cam.coverage.polygon_points)
        
        # If not near the edge, no handoff candidates yet
        if dist_to_edge > self._threshold:
            # Update entity state to clear candidates
            entity.candidate_cameras = []
            return []
            
        # Predict future position based on velocity
        vx, vy = entity.velocity_vector
        future_x = px + (vx * prediction_seconds)
        future_y = py + (vy * prediction_seconds)
        
        candidate_cameras = []
        
        # Check all other cameras to see if future position falls in their coverage
        for cam_id, cam_model in self._viewshed._cameras.items():
            if cam_id == entity.active_camera or not cam_model.coverage.is_active:
                continue
                
            from src.spatial.viewshed import VisibilityState
            # Check visibility of future point in the candidate camera
            vis = self._viewshed.check_visibility(future_x, future_y, cam_id)
            if vis == VisibilityState.VISIBLE:
                candidate_cameras.append(cam_id)
                
        entity.candidate_cameras = candidate_cameras
        
        # If it's effectively outside the current camera but we haven't seen it in the new one,
        # it is in a reconstructed state topologically
        if dist_to_edge < 0.1 and entity.observation_state != ObservationState.LIVE_OBSERVED:
            entity.observation_state = ObservationState.RECONSTRUCTED
            
        return candidate_cameras
