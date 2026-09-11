"""Phase 12: 2D Operational Spatial Map Model & Visualizer.

Provides metric 2D coordinate mapping for store floor plans, calibrated cameras,
zones, viewsheds, active entities, trajectories, and multi-camera handoffs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.spatial.contract import (
    CameraCoverage,
    CameraSpatialModel,
    ObservationState,
    SpatialEntityState,
    SpatialObservation,
    SpatialProvenance,
    SpatialTrajectoryPoint,
    StoreCoordinate,
)


@dataclass
class MapZone:
    """A defined zone on the 2D metric floor plan."""
    zone_id: str
    zone_name: str
    polygon_points: List[Tuple[float, float]]  # (x, y) in meters
    color: str = "#38BDF8"
    opacity: float = 0.2


@dataclass
class HandoffVisualVector:
    """Visual representation of a multi-camera entity transition."""
    from_camera: str
    to_camera: str
    zone_id: str
    entity_id: str
    confidence: float
    status: str  # "CONFIRMED_BY_RULE", "LIKELY", "AMBIGUOUS"
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]


class SpatialMapModel:
    """Model that maintains 2D spatial layout and provides renderable primitives."""

    def __init__(self, store_width_m: float = 30.0, store_height_m: float = 20.0):
        self.store_width_m = store_width_m
        self.store_height_m = store_height_m
        self.zones: Dict[str, MapZone] = {}
        self.cameras: Dict[str, CameraSpatialModel] = {}
        self.entities: Dict[str, SpatialEntityState] = {}
        self.active_handoffs: List[HandoffVisualVector] = []

    def add_zone(self, zone: MapZone) -> None:
        self.zones[zone.zone_id] = zone

    def add_camera(self, camera_model: CameraSpatialModel) -> None:
        self.cameras[camera_model.camera_id] = camera_model

    def update_entity(self, entity_state: SpatialEntityState) -> None:
        self.entities[entity_state.entity_id] = entity_state

    def record_handoff(self, vector: HandoffVisualVector) -> None:
        self.active_handoffs.append(vector)
        if len(self.active_handoffs) > 20:
            self.active_handoffs.pop(0)

    def to_render_primitives(self, canvas_width: int, canvas_height: int) -> Dict[str, Any]:
        """Translates metric store coordinates (meters) to canvas pixel primitives."""
        scale_x = canvas_width / max(1.0, self.store_width_m)
        scale_y = canvas_height / max(1.0, self.store_height_m)
        scale = min(scale_x, scale_y) * 0.9
        offset_x = (canvas_width - self.store_width_m * scale) / 2.0
        offset_y = (canvas_height - self.store_height_m * scale) / 2.0

        def to_px(x: float, y: float) -> Tuple[float, float]:
            return (offset_x + x * scale, offset_y + y * scale)

        # Zones
        rendered_zones = []
        for zone in self.zones.values():
            px_poly = [to_px(x, y) for (x, y) in zone.polygon_points]
            rendered_zones.append({
                "zone_id": zone.zone_id,
                "name": zone.zone_name,
                "points": px_poly,
                "color": zone.color,
            })

        # Cameras and Viewsheds
        rendered_cameras = []
        for cam in self.cameras.values():
            cam_px = to_px(cam.position_store.x, cam.position_store.y)
            coverage_px = []
            if cam.coverage and cam.coverage.polygon_points:
                coverage_px = [to_px(p.x, p.y) for p in cam.coverage.polygon_points]
            rendered_cameras.append({
                "camera_id": cam.camera_id,
                "position": cam_px,
                "yaw_deg": cam.orientation_yaw_deg,
                "coverage_polygon": coverage_px,
            })

        # Entities & Trajectories
        rendered_entities = []
        for ent in self.entities.values():
            pos_px = to_px(ent.current_store_position.x, ent.current_store_position.y)
            traj = getattr(ent, "trajectory", None) or getattr(ent, "trajectory_history", [])
            if traj:
                traj_px = [to_px(p.x, p.y) for p in traj[-15:]]
            rendered_entities.append({
                "entity_id": ent.entity_id,
                "position": pos_px,
                "trajectory": traj_px,
                "confidence": getattr(ent, "confidence", 1.0),
                "epistemic_state": getattr(ent, "current_observation_state", ObservationState.LIVE_OBSERVED).value,
            })

        # Handoffs
        rendered_handoffs = []
        for h in self.active_handoffs:
            rendered_handoffs.append({
                "from_cam": h.from_camera,
                "to_cam": h.to_camera,
                "entity_id": h.entity_id,
                "status": h.status,
                "p1": to_px(*h.start_point),
                "p2": to_px(*h.end_point),
            })

        return {
            "canvas_size": (canvas_width, canvas_height),
            "zones": rendered_zones,
            "cameras": rendered_cameras,
            "entities": rendered_entities,
            "handoffs": rendered_handoffs,
        }
