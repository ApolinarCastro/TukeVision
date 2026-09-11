"""Tests for Spatial Entity State (Slice 5)."""

import pytest
import datetime
from src.spatial.homography import HomographyEngine
from src.spatial.entity_state import SpatialStateManager
from src.spatial.contract import ObservationState

def test_spatial_state_manager_lifecycle():
    engine = HomographyEngine()
    
    # Register a dummy calibration so projection works
    engine.register_calibration(
        camera_id="cam_01",
        image_points=[(0, 0), (100, 0), (100, 100), (0, 100)],
        floor_points=[(0, 0), (10, 0), (10, 10), (0, 10)],
        version="v1"
    )
    
    manager = SpatialStateManager(engine, max_trajectory_points=5)
    
    t0 = "2026-08-28T10:00:00Z"
    
    # First observation (Bbox: center bottom is (50, 100) -> which should project to (5, 10))
    state = manager.update_observation(
        entity_id="ENT-1",
        camera_id="cam_01",
        bbox=(0, 0, 100, 100),
        confidence=0.9,
        timestamp=t0
    )
    
    assert state is not None
    assert state.entity_id == "ENT-1"
    assert state.current_store_position.x == pytest.approx(5.0, 0.01)
    assert state.current_store_position.y == pytest.approx(10.0, 0.01)
    assert len(state.trajectory) == 1
    assert state.velocity_vector == (0.0, 0.0)
    assert state.observation_state == ObservationState.LIVE_OBSERVED
    
    # Second observation 1 second later (Bbox moves to right: center bottom (60, 100) -> (6, 10))
    t1 = "2026-08-28T10:00:01Z"
    state2 = manager.update_observation(
        entity_id="ENT-1",
        camera_id="cam_01",
        bbox=(10, 0, 110, 100),
        confidence=0.95,
        timestamp=t1
    )
    
    assert state2.current_store_position.x == pytest.approx(6.0, 0.01)
    assert state2.previous_store_position.x == pytest.approx(5.0, 0.01)
    assert len(state2.trajectory) == 2
    
    # Velocity should be approx +1.0 in X, 0.0 in Y
    vx, vy = state2.velocity_vector
    assert vx == pytest.approx(1.0, 0.01)
    assert vy == pytest.approx(0.0, 0.01)
    
    # Direction should be ~0 degrees (moving right)
    assert state2.direction_deg == pytest.approx(0.0, 0.1)
    
def test_trajectory_bounded_history():
    engine = HomographyEngine()
    engine.register_calibration(
        camera_id="cam_01",
        image_points=[(0, 0), (100, 0), (100, 100), (0, 100)],
        floor_points=[(0, 0), (10, 0), (10, 10), (0, 10)]
    )
    
    manager = SpatialStateManager(engine, max_trajectory_points=3)
    
    # Insert 5 points
    for i in range(5):
        manager.update_observation(
            entity_id="ENT-2",
            camera_id="cam_01",
            bbox=(i*10, 0, i*10 + 100, 100),
            confidence=0.9,
            timestamp=f"2026-08-28T10:00:0{i}Z"
        )
        
    state = manager.get_state("ENT-2")
    # History should be bounded to 3
    assert len(state.trajectory) == 3
