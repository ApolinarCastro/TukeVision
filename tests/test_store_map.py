"""Tests for Store Operational Map (Slice 7)."""

import pytest
from src.spatial.contract import StoreCoordinate, CameraSpatialModel, CameraCoverage
from src.spatial.homography import HomographyEngine
from src.spatial.viewshed import ViewshedEngine
from src.spatial.entity_state import SpatialStateManager
from src.spatial.store_map import StoreOperationalMap

def test_store_map_generation():
    # Setup Engines
    viewshed = ViewshedEngine(resolution_px_per_m=2.0)
    store_floor = [
        StoreCoordinate(0, 0), StoreCoordinate(10, 0),
        StoreCoordinate(10, 10), StoreCoordinate(0, 10)
    ]
    viewshed.set_store_floor(store_floor)
    
    cam_cov = CameraCoverage(polygon_points=[
        StoreCoordinate(0, 0), StoreCoordinate(5, 0),
        StoreCoordinate(5, 10), StoreCoordinate(0, 10)
    ])
    cam = CameraSpatialModel(
        camera_id="cam_01",
        position_store=StoreCoordinate(0, 5),
        orientation_yaw_deg=90.0,
        field_of_view_deg=180.0,
        coverage=cam_cov,
        calibration_version="v1.0"
    )
    viewshed.add_camera_model(cam)
    
    homography = HomographyEngine()
    homography.register_calibration(
        camera_id="cam_01",
        image_points=[(0, 0), (100, 0), (100, 100), (0, 100)],
        floor_points=[(0, 0), (5, 0), (5, 10), (0, 10)],
        version="v1.0"
    )
    
    spatial = SpatialStateManager(homography)
    
    # Add an entity
    spatial.update_observation(
        entity_id="ENT-1",
        camera_id="cam_01",
        bbox=(0, 0, 100, 100),
        confidence=0.9,
        timestamp="2026-08-28T10:00:00Z"
    )
    
    # Generate Map
    store_map = StoreOperationalMap(
        store_id="STORE-101",
        viewshed_engine=viewshed,
        spatial_manager=spatial
    )
    
    state = store_map.generate_scene_state()
    
    assert state.store_id == "STORE-101"
    assert "cam_01" in state.cameras
    assert "ENT-1" in state.entities
    
    # We should have coverage gaps because the camera only covers half the store
    assert len(state.coverage_gaps) > 0
