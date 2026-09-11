"""Tests for Spatial Scene Contract."""

import pytest
from src.spatial.contract import (
    StoreCoordinate,
    CameraCoverage,
    CameraSpatialModel,
    SpatialObservation,
    SpatialEntityState,
    SpatialTrajectoryPoint,
    StoreSceneState,
    ObservationState,
    SpatialProvenance
)
from datetime import datetime, timezone

def test_store_coordinate_instantiation():
    coord = StoreCoordinate(x=10.5, y=20.1)
    assert coord.x == 10.5
    assert coord.y == 20.1
    assert coord.z is None

def test_camera_spatial_model():
    p1 = StoreCoordinate(0, 0)
    p2 = StoreCoordinate(10, 0)
    p3 = StoreCoordinate(10, 10)
    
    coverage = CameraCoverage(polygon_points=[p1, p2, p3])
    model = CameraSpatialModel(
        camera_id="cam_01",
        position_store=StoreCoordinate(5, -1),
        orientation_yaw_deg=90.0,
        field_of_view_deg=60.0,
        coverage=coverage,
        calibration_version="v1.0"
    )
    
    assert model.camera_id == "cam_01"
    assert model.coverage.is_active is True
    assert len(model.coverage.polygon_points) == 3

def test_spatial_entity_state():
    point = SpatialTrajectoryPoint(
        x=5.0, y=5.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source_camera="cam_01",
        confidence=0.9,
        observation_state=ObservationState.LIVE_OBSERVED
    )
    
    state = SpatialEntityState(
        entity_id="ENT-001",
        current_store_position=StoreCoordinate(5.5, 5.5),
        previous_store_position=StoreCoordinate(5.0, 5.0),
        velocity_vector=(0.5, 0.5),
        direction_deg=45.0,
        current_zone="Cajas",
        previous_zone="Pasillo",
        active_camera="cam_01",
        candidate_cameras=["cam_02"],
        trajectory=[point],
        observation_state=ObservationState.DELAYED,
        confidence=0.85,
        freshness=0.5,
        last_observed_at=datetime.now(timezone.utc).isoformat()
    )
    
    assert state.entity_id == "ENT-001"
    assert state.observation_state == ObservationState.DELAYED
    assert len(state.trajectory) == 1
    
def test_spatial_observation():
    obs = SpatialObservation(
        observation_id="OBS-001",
        entity_id="ENT-001",
        camera_id="cam_01",
        bbox=(10, 20, 100, 200),
        ground_point_px=(55, 200),
        store_x=10.5,
        store_y=20.5,
        observed_at=datetime.now(timezone.utc).isoformat(),
        processed_at=datetime.now(timezone.utc).isoformat(),
        observation_state=ObservationState.LIVE_OBSERVED,
        confidence=0.95,
        source_generation="gen-1",
        provenance=SpatialProvenance.CAMERA_PROJECTION
    )
    
    assert obs.observation_state == ObservationState.LIVE_OBSERVED
    assert obs.provenance == SpatialProvenance.CAMERA_PROJECTION
