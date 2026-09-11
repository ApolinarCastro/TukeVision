"""Tests for Camera Coverage and Viewshed (Slice 4)."""

import pytest
from src.spatial.contract import StoreCoordinate, CameraSpatialModel, CameraCoverage
from src.spatial.viewshed import ViewshedEngine, VisibilityState

def test_viewshed_basic_visibility():
    engine = ViewshedEngine()
    
    # Store floor: 0,0 to 20,20
    store = [
        StoreCoordinate(0, 0), StoreCoordinate(20, 0),
        StoreCoordinate(20, 20), StoreCoordinate(0, 20)
    ]
    engine.set_store_floor(store)
    
    # Camera covers 0,0 to 10,10 with an occlusion at 5,5 to 6,6
    cam_cov = CameraCoverage(polygon_points=[
        StoreCoordinate(0, 0), StoreCoordinate(10, 0),
        StoreCoordinate(10, 10), StoreCoordinate(0, 10)
    ])
    
    occ = [
        StoreCoordinate(5, 5), StoreCoordinate(6, 5),
        StoreCoordinate(6, 6), StoreCoordinate(5, 6)
    ]
    
    cam = CameraSpatialModel(
        camera_id="cam_01",
        position_store=StoreCoordinate(0, 0),
        orientation_yaw_deg=45.0,
        field_of_view_deg=90.0,
        coverage=cam_cov,
        calibration_version="v1.0",
        occlusion_model=[occ]
    )
    engine.add_camera_model(cam)
    
    # Test Visible (inside coverage, outside occlusion)
    assert engine.check_visibility(2, 2) == VisibilityState.VISIBLE
    
    # Test Occluded
    assert engine.check_visibility(5.5, 5.5) == VisibilityState.OCCLUDED
    
    # Test Outside Coverage (inside store but outside camera)
    assert engine.check_visibility(15, 15) == VisibilityState.OUTSIDE_COVERAGE
    
def test_coverage_gaps():
    engine = ViewshedEngine(resolution_px_per_m=5.0)
    
    # Store floor: 0,0 to 10,10
    store = [
        StoreCoordinate(0, 0), StoreCoordinate(10, 0),
        StoreCoordinate(10, 10), StoreCoordinate(0, 10)
    ]
    engine.set_store_floor(store)
    
    # Camera covers left half: 0,0 to 5,10
    cam_cov = CameraCoverage(polygon_points=[
        StoreCoordinate(0, 0), StoreCoordinate(5, 0),
        StoreCoordinate(5, 10), StoreCoordinate(0, 10)
    ])
    
    cam = CameraSpatialModel(
        camera_id="cam_02",
        position_store=StoreCoordinate(0, 5),
        orientation_yaw_deg=90.0,
        field_of_view_deg=180.0,
        coverage=cam_cov,
        calibration_version="v1.0"
    )
    engine.add_camera_model(cam)
    
    gaps = engine.get_coverage_gaps()
    
    # The gap should be the right half: 5,0 to 10,10 roughly
    assert len(gaps) == 1
    
    # Pick a point in the expected gap (e.g., 7, 5) and ensure it's inside the gap contour
    import cv2
    import numpy as np
    
    gap = gaps[0]
    pts = np.array([[p.x, p.y] for p in gap], dtype=np.float32)
    
    # Point (7,5) should be inside the gap polygon
    assert cv2.pointPolygonTest(pts, (7, 5), False) >= 0
    # Point (2,5) should be outside (it's covered)
    assert cv2.pointPolygonTest(pts, (2, 5), False) < 0
