"""Tests for Multicamera Handoff Engine (Slice 6)."""

import pytest
from src.spatial.contract import (
    StoreCoordinate, CameraSpatialModel, CameraCoverage, SpatialEntityState, ObservationState
)
from src.spatial.viewshed import ViewshedEngine
from src.spatial.handoff import HandoffEngine

def test_handoff_logic():
    viewshed = ViewshedEngine()
    
    # Cam 1: 0,0 to 10,10
    cam1 = CameraSpatialModel(
        camera_id="cam_01",
        position_store=StoreCoordinate(0, 0),
        orientation_yaw_deg=45.0,
        field_of_view_deg=90.0,
        coverage=CameraCoverage(polygon_points=[
            StoreCoordinate(0, 0), StoreCoordinate(10, 0),
            StoreCoordinate(10, 10), StoreCoordinate(0, 10)
        ]),
        calibration_version="v1"
    )
    
    # Cam 2: 10,0 to 20,10
    cam2 = CameraSpatialModel(
        camera_id="cam_02",
        position_store=StoreCoordinate(20, 0),
        orientation_yaw_deg=135.0,
        field_of_view_deg=90.0,
        coverage=CameraCoverage(polygon_points=[
            StoreCoordinate(10, 0), StoreCoordinate(20, 0),
            StoreCoordinate(20, 10), StoreCoordinate(10, 10)
        ]),
        calibration_version="v1"
    )
    
    viewshed.add_camera_model(cam1)
    viewshed.add_camera_model(cam2)
    
    handoff = HandoffEngine(viewshed, edge_distance_threshold_m=1.5)
    
    # Entity is at 9.0, 5.0 (inside cam1, close to right edge at x=10)
    # Moving right with velocity (1.0, 0.0) -> in 2 seconds it will be at 11.0, 5.0 (inside cam2)
    entity = SpatialEntityState(
        entity_id="ENT-1",
        current_store_position=StoreCoordinate(9.0, 5.0),
        previous_store_position=StoreCoordinate(8.0, 5.0),
        velocity_vector=(1.0, 0.0),
        direction_deg=0.0,
        current_zone=None,
        previous_zone=None,
        active_camera="cam_01",
        candidate_cameras=[],
        trajectory=[],
        observation_state=ObservationState.LIVE_OBSERVED,
        confidence=0.9,
        freshness=1.0,
        last_observed_at="2026-08-28T10:00:00Z"
    )
    
    cands = handoff.evaluate_handoff(entity, prediction_seconds=2.0)
    
    # Edge dist to x=10 is 1.0m, which is < 1.5m threshold.
    # Future point is (11, 5), which is in cam2.
    assert "cam_02" in cands
    assert entity.candidate_cameras == ["cam_02"]

def test_handoff_not_near_edge():
    viewshed = ViewshedEngine()
    
    cam1 = CameraSpatialModel(
        camera_id="cam_01",
        position_store=StoreCoordinate(0, 0),
        orientation_yaw_deg=45.0,
        field_of_view_deg=90.0,
        coverage=CameraCoverage(polygon_points=[
            StoreCoordinate(0, 0), StoreCoordinate(10, 0),
            StoreCoordinate(10, 10), StoreCoordinate(0, 10)
        ]),
        calibration_version="v1"
    )
    viewshed.add_camera_model(cam1)
    
    handoff = HandoffEngine(viewshed, edge_distance_threshold_m=1.5)
    
    # Entity at 5.0, 5.0 (center of cam1)
    entity = SpatialEntityState(
        entity_id="ENT-2",
        current_store_position=StoreCoordinate(5.0, 5.0),
        previous_store_position=StoreCoordinate(4.0, 5.0),
        velocity_vector=(1.0, 0.0),
        direction_deg=0.0,
        current_zone=None,
        previous_zone=None,
        active_camera="cam_01",
        candidate_cameras=["cam_02"], # Assuming it had old candidates
        trajectory=[],
        observation_state=ObservationState.LIVE_OBSERVED,
        confidence=0.9,
        freshness=1.0,
        last_observed_at="2026-08-28T10:00:00Z"
    )
    
    cands = handoff.evaluate_handoff(entity)
    
    # Edge dist is 5.0m > 1.5m threshold. Should return empty candidates and clear old ones.
    assert len(cands) == 0
    assert len(entity.candidate_cameras) == 0
