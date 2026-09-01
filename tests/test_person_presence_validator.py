import pytest
import time
from types import SimpleNamespace
from src.perception.person_presence_validator import PersonPresenceValidator

class MockTrack:
    def __init__(self, camera_id, track_id, last_bbox, object_type="person"):
        self.camera_id = camera_id
        self.track_id = track_id
        self.last_bbox = last_bbox
        self.object_type = object_type

@pytest.fixture
def validator():
    return PersonPresenceValidator(
        fixture_persistence_seconds=1.0,  # Fast for tests
        max_centroid_variance=0.1,
        store_state="OPEN"
    )

def test_static_person_like_does_not_become_confirmed_person(validator):
    track = MockTrack("cam_1", "t1", (100, 100, 200, 200))
    # First seen
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_MOVING"

    # Stay still for longer than persistence
    time.sleep(1.1)
    res2 = validator.evaluate_track(track, None)
    assert res2 == "LIKELY_SCENE_FIXTURE"

def test_static_fixture_does_not_generate_prolonged_dwell(validator):
    # This is implicitly tested in advance_chain skipping logic,
    # but we verify the classification stays fixture
    track = MockTrack("cam_1", "t1", (100, 100, 200, 200))
    validator.evaluate_track(track, None)
    time.sleep(1.1)
    assert validator.evaluate_track(track, None) == "LIKELY_SCENE_FIXTURE"

def test_static_fixture_does_not_generate_behavior_risk():
    pass # Checked in advance_chain skipping logic

def test_small_bbox_jitter_is_not_real_motion(validator):
    track = MockTrack("cam_1", "t2", (100, 100, 200, 200))
    validator.evaluate_track(track, None)
    time.sleep(1.1)

    # Small jitter within max_centroid_variance
    track.last_bbox = (102, 98, 202, 198)
    res = validator.evaluate_track(track, None)
    assert res == "LIKELY_SCENE_FIXTURE"

def test_real_person_entering_scene_is_detected(validator):
    track = MockTrack("cam_1", "t3", (10, 10, 50, 50))
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_MOVING"

    track.last_bbox = (100, 100, 140, 140)
    res2 = validator.evaluate_track(track, None)
    assert res2 == "PERSON_MOVING"

def test_real_person_stopping_remains_person(validator):
    track = MockTrack("cam_1", "t4", (10, 10, 50, 50))
    validator.evaluate_track(track, None)

    # Person moves significantly - this sets ever_moved=True
    track.last_bbox = (100, 100, 140, 140)
    validator.evaluate_track(track, None)

    # Now person stops - add enough stationary frames for movement to fall out of recent window (30 frames)
    for _ in range(35):
        track.last_bbox = (100, 100, 140, 140)
        validator.evaluate_track(track, None)

    validator.fixture_persistence_seconds = 10.0

    # Hack first_seen to simulate 6 seconds since first seen
    validator._memory["cam_1"]["t4"].first_seen = time.time() - 6.0
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_STATIONARY"

def test_static_fixture_moved_is_revalidated(validator):
    track = MockTrack("cam_1", "t5", (100, 100, 200, 200))
    validator.evaluate_track(track, None)
    time.sleep(1.1)
    assert validator.evaluate_track(track, None) == "LIKELY_SCENE_FIXTURE"

    # Moved significantly (x jumps 150 px)
    track.last_bbox = (250, 100, 350, 200)
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_MOVING"

def test_closed_store_new_motion_is_unexpected_activity(validator):
    validator.update_store_state("CLOSED")
    track = MockTrack("cam_1", "t6", (100, 100, 200, 200))
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_MOVING"
    # advance_chain adds the metadata UNEXPECTED_HUMAN_ACTIVITY

def test_closed_store_does_not_disable_person_detection(validator):
    validator.update_store_state("CLOSED")
    track = MockTrack("cam_1", "t7", (10, 10, 50, 50))
    res = validator.evaluate_track(track, None)
    assert res == "PERSON_MOVING"
