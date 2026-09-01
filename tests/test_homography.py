"""Tests for Homography Engine (Slice 3)."""

import pytest
import numpy as np
from src.spatial.homography import HomographyEngine

def test_missing_calibration():
    engine = HomographyEngine()
    # Less than 4 points -> UNCALIBRATED
    calib = engine.register_calibration(
        camera_id="cam_01",
        image_points=[(0, 0), (10, 10)],
        floor_points=[(0, 0), (1, 1)]
    )
    assert calib.status == "UNCALIBRATED"
    
    # Projection should return None
    assert engine.project_image_to_store("cam_01", 5, 5) is None

def test_degenerate_matrix():
    engine = HomographyEngine()
    # All points are the same, collinear or degenerate
    calib = engine.register_calibration(
        camera_id="cam_02",
        image_points=[(0, 0), (0, 0), (0, 0), (0, 0)],
        floor_points=[(1, 1), (1, 1), (1, 1), (1, 1)]
    )
    assert calib.status == "DEGENERATE"
    assert engine.project_image_to_store("cam_02", 5, 5) is None

def test_known_point_projection_and_inverse():
    engine = HomographyEngine()
    
    # Create a simple mapping: 
    # Image is a 100x100 square mapped to a 10x10 store square
    img_pts = [(0, 0), (100, 0), (100, 100), (0, 100)]
    store_pts = [(0, 0), (10, 0), (10, 10), (0, 10)]
    
    calib = engine.register_calibration(
        camera_id="cam_03",
        image_points=img_pts,
        floor_points=store_pts,
        version="v2.0"
    )
    
    assert calib.status == "CALIBRATED"
    assert calib.calibration_version == "v2.0"
    assert calib.validation_error is not None
    assert calib.validation_error < 1e-4  # Should be perfectly 0
    
    # Test Forward Projection (Center of square)
    store_c = engine.project_image_to_store("cam_03", 50, 50)
    assert store_c is not None
    assert pytest.approx(store_c.x, 0.01) == 5.0
    assert pytest.approx(store_c.y, 0.01) == 5.0
    
    # Test Inverse Projection
    img_c = engine.project_store_to_image("cam_03", 5.0, 5.0)
    assert img_c is not None
    assert pytest.approx(img_c[0], 0.01) == 50.0
    assert pytest.approx(img_c[1], 0.01) == 50.0
    
    # Test out-of-bounds (Should still project mathematically)
    store_oob = engine.project_image_to_store("cam_03", 200, 200)
    assert store_oob is not None
    assert pytest.approx(store_oob.x, 0.01) == 20.0

def test_foot_point_estimation():
    bbox = (10, 20, 30, 40)
    fx, fy = HomographyEngine.estimate_foot_point(bbox)
    assert fx == 20  # (10 + 30) / 2
    assert fy == 40  # Bottom Y
