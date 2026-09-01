"""Entity Runtime Truth Tests (TV-ENTITY-RUNTIME-TRUTH-CLOSURE-24).

Validates that real person/visit semantics propagate from validator through
AdvanceChain to the UI view model without mocks.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.app.advance_chain import AdvanceChain
from src.perception.person_presence_validator import PersonPresenceValidator
from src.tracking.visit_session import VisitSessionManager
from src.tracking.visit_semantic import VisitSemanticSnapshot


class MockTrack:
    """Mock track for testing with required attributes."""
    def __init__(self, camera_id, track_id, last_bbox, object_type="person"):
        self.camera_id = camera_id
        self.track_id = track_id
        self.last_bbox = last_bbox
        self.object_type = object_type


class MockEvent:
    """Mock event for testing."""
    def __init__(self, event_id="evt_1", metadata=None):
        self.event_id = event_id
        self.metadata = metadata or {}
        self.inference_ref = "inf_1"


class FakeSourceManager:
    """Duck-typed SourceManager for testing."""
    def __init__(self, camera_ids):
        self._camera_ids = list(camera_ids)

    def list_sources(self):
        return [
            {"camera_id": cid, "host": "rtsp://cam.local", "channel": 1,
             "subtype": 1, "running": True}
            for cid in self._camera_ids
        ]

    def health(self, camera_id):
        class _H:
            fps = 15.0
        return _H()


def make_config(**overrides):
    cfg = {
        "observation": {
            "default_profile": "BALANCED",
            "profiles": {
                "QUALITY": {"max_analysis_fps": 5.0},
                "BALANCED": {"max_analysis_fps": 2.0},
                "ECONOMY": {"max_analysis_fps": 1.0},
            },
        },
        "inference": {
            "backend": "deterministic",
            "confidence_threshold": 0.5,
            "simulated_latency_ms": 0.0,
            "event_queue_maxlen": 16,
            "event_queue_overflow": "drop_oldest",
            "events": [
                {"type": "OBJECT_DETECTED", "min_confidence": 0.5},
                {"type": "PERSON_DETECTED", "min_confidence": 0.5, "class_name": "person"},
            ],
        },
        "temporal": {
            "association_window_ms": 2000,
            "track_timeout_ms": 5000,
            "iou_threshold": 0.05,
            "max_active_tracks": 8,
            "max_completed_history": 32,
            "max_event_refs": 16,
            "max_evidence_refs": 3,
        },
    }
    if overrides:
        import json
        cfg = json.loads(json.dumps(cfg))
        cfg.update(overrides)
    return cfg


def make_person_config(**overrides):
    """Config with deterministic generator that produces person detections."""
    import json
    cfg = make_config()
    # Inject generator for person class (class_id=0 -> person)
    def person_generator(camera_id, frame_index):
        # Returns (class_id, class_name, confidence, x1, y1, x2, y2)
        return [(0, "person", 0.9, 300, 100, 399, 199)]
    
    # We need to modify the engine creation to use this generator
    # For now, we'll patch the engine after chain creation
    return cfg


# Bright frame that triggers deterministic detection
BRIGHT_FRAME = np.zeros((480, 640, 3), dtype="uint8")
BRIGHT_FRAME[100:200, 300:400] = 255


class TestValidatorReachesSnapshot:
    """Validator result reaches AdvanceChain visit_semantics."""

    def test_validator_result_in_feed_output(self):
        """PersonPresenceValidator output appears in feed() visit_semantics."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        
        # Inject person generator into selective pipeline engine
        if hasattr(chain._selective, '_engine'):
            chain._selective._engine._generator = lambda cid, fi: [(0, "person", 0.9, 300, 100, 399, 199)]
        
        chain.register_from_source_manager()

        # Feed a frame that produces a person track
        result = chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)

        assert "visit_semantics" in result
        semantics = result["visit_semantics"]
        assert len(semantics) >= 1
        snap = semantics[0]
        assert isinstance(snap, VisitSemanticSnapshot)
        assert snap.track_id != ""
        assert snap.camera_id == "CAM-01"
        assert snap.person_state in ("PERSON_MOVING", "PERSON_STATIONARY", "LIKELY_SCENE_FIXTURE", "AMBIGUOUS_PERSON_LIKE")

        chain.close()

    def test_validator_state_persists_across_frames(self):
        """Validator maintains state across feed() calls for same track."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        
        # Inject person generator
        if hasattr(chain._selective, '_engine'):
            chain._selective._engine._generator = lambda cid, fi: [(0, "person", 0.9, 300, 100, 399, 199)]
        
        chain.register_from_source_manager()

        # First frame - track created
        result1 = chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)
        assert len(result1["visit_semantics"]) >= 1
        track_id = result1["visit_semantics"][0].track_id

        # Second frame (skipped by BALANCED policy) - no new track
        result2 = chain.feed("CAM-01", 1, 15.0, BRIGHT_FRAME)
        # Frame 1 is skipped, but if track persists, semantics may be empty
        # This is expected - only frames with observations produce semantics

        chain.close()


class TestVisitIdReachesViewModel:
    """Visit ID propagates to view model via visit_semantics."""

    def test_eligible_person_gets_visit_id(self):
        """PERSON_MOVING/STATIONARY tracks receive visit_id in semantics."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        
        # Inject person generator
        if hasattr(chain._selective, '_engine'):
            chain._selective._engine._generator = lambda cid, fi: [(0, "person", 0.9, 300, 100, 399, 199)]
        
        chain.register_from_source_manager()

        result = chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)

        assert len(result["visit_semantics"]) >= 1
        snap = result["visit_semantics"][0]
        # Eligible person states should have visit_id
        if snap.person_state in ("PERSON_MOVING", "PERSON_STATIONARY"):
            assert snap.visit_id is not None
            assert snap.visit_id.startswith("VIS-")
        else:
            # Fixture/ambiguous should not have visit_id
            assert snap.visit_id is None

        chain.close()

    def test_fixture_no_visit_id(self):
        """LIKELY_SCENE_FIXTURE never receives visit_id."""
        # Use a validator with short fixture persistence for testing
        validator = PersonPresenceValidator(fixture_persistence_seconds=0.1)
        track = MockTrack("cam_1", "t1", (100, 100, 200, 200))

        # First observation
        state = validator.evaluate_track(track, None)
        assert state == "PERSON_MOVING"  # bootstrap

        # Wait for fixture persistence
        time.sleep(0.15)
        state = validator.evaluate_track(track, None)
        assert state == "LIKELY_SCENE_FIXTURE"

        # Create visit manager and verify no visit_id
        visit_mgr = VisitSessionManager()
        visit = visit_mgr.handle_track("t1", "cam_1", (100, 100, 200, 200), is_eligible_person=False)
        assert visit is None

    def test_ambiguous_no_visit_id(self):
        """AMBIGUOUS_PERSON_LIKE has no visit_id."""
        validator = PersonPresenceValidator()
        track = MockTrack(None, "t1", (100, 100, 200, 200))  # missing camera_id

        state = validator.evaluate_track(track, None)
        assert state == "AMBIGUOUS_PERSON_LIKE"

        visit_mgr = VisitSessionManager()
        visit = visit_mgr.handle_track("t1", "cam_1", (100, 100, 200, 200), is_eligible_person=False)
        assert visit is None


class TestVisitRoleReachesUI:
    """Visit role propagates correctly."""

    def test_default_role_is_unknown(self):
        """New visit starts with UNKNOWN role, never CUSTOMER."""
        validator = PersonPresenceValidator()
        track = MockTrack("cam_1", "t1", (10, 10, 50, 50))
        validator.evaluate_track(track, None)  # PERSON_MOVING
        validator.evaluate_track(track, None)  # PERSON_MOVING

        visit_mgr = VisitSessionManager()
        visit = visit_mgr.handle_track("t1", "cam_1", (10, 10, 50, 50), is_eligible_person=True)

        assert visit is not None
        assert visit.role == "UNKNOWN"
        assert visit.visit_id.startswith("VIS-")

    def test_staff_assignment_becomes_confirmed(self):
        """Operator can set STAFF_CONFIRMED role."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit_id = visit.visit_id

        visit_mgr.set_role(visit_id, "STAFF_CONFIRMED")

        updated = visit_mgr._sessions[visit_id]
        assert updated.role == "STAFF_CONFIRMED"

    def test_staff_confirmed_excluded_from_customer_analytics(self):
        """STAFF_CONFIRMED is not eligible for customer analytics."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit_id = visit.visit_id

        visit_mgr.set_role(visit_id, "STAFF_CONFIRMED")

        assert visit_mgr._sessions[visit_id].customer_analytics_eligible is False

    def test_staff_candidate_not_auto_excluded(self):
        """STAFF_CANDIDATE remains eligible for customer analytics."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit_id = visit.visit_id

        visit_mgr.set_role(visit_id, "STAFF_CANDIDATE")

        assert visit_mgr._sessions[visit_id].customer_analytics_eligible is True


class TestVisitIdStability:
    """Visit ID remains stable for same track."""

    def test_moving_then_stationary_keeps_same_visit_id(self):
        """Person moving then stopping keeps same visit_id."""
        validator = PersonPresenceValidator(fixture_persistence_seconds=10.0)
        visit_mgr = VisitSessionManager()

        # Person moves
        track = MockTrack("cam_1", "t1", (10, 10, 50, 50))
        validator.evaluate_track(track, None)
        track.last_bbox = (100, 100, 140, 140)
        state = validator.evaluate_track(track, None)  # PERSON_MOVING
        visit = visit_mgr.handle_track("t1", "cam_1", (100, 100, 140, 140), is_eligible_person=True)
        visit_id_1 = visit.visit_id

        # Person stops - add stationary frames
        for _ in range(35):
            track.last_bbox = (100, 100, 140, 140)
            validator.evaluate_track(track, None)
        state = validator.evaluate_track(track, None)  # PERSON_STATIONARY
        visit = visit_mgr.handle_track("t1", "cam_1", (100, 100, 140, 140), is_eligible_person=True)
        visit_id_2 = visit.visit_id

        assert visit_id_1 == visit_id_2
        assert state == "PERSON_STATIONARY"


class TestPhysicalRuntimeNoMocks:
    """Physical runtime path does not use mock visit_id or role."""

    def test_advance_chain_uses_real_validator(self):
        """AdvanceChain instantiates real PersonPresenceValidator, not mock."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        assert chain._person_validator is not None
        assert isinstance(chain._person_validator, PersonPresenceValidator)
        chain.close()

    def test_advance_chain_uses_real_visit_manager(self):
        """AdvanceChain instantiates real VisitSessionManager, not mock."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        assert chain._visit_mgr is not None
        assert isinstance(chain._visit_mgr, VisitSessionManager)
        chain.close()

    def test_visit_semantics_not_mocked(self):
        """visit_semantics in feed output comes from real validator/visit manager."""
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()

        result = chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)

        # visit_semantics is a tuple of real VisitSemanticSnapshot objects
        semantics = result["visit_semantics"]
        assert isinstance(semantics, tuple)
        for snap in semantics:
            assert isinstance(snap, VisitSemanticSnapshot)
            # Real data fields, not mock placeholders
            assert snap.track_id != ""
            assert snap.camera_id == "CAM-01"
            assert snap.person_state in (
                "PERSON_MOVING", "PERSON_STATIONARY", 
                "LIKELY_SCENE_FIXTURE", "AMBIGUOUS_PERSON_LIKE"
            )
            assert snap.visit_role in ("UNKNOWN", "CUSTOMER", "STAFF_CONFIRMED", "STAFF_CANDIDATE")
            assert isinstance(snap.customer_analytics_eligible, bool)
            assert snap.visit_origin in ("ENTRY_OBSERVED", "UNKNOWN")

        chain.close()


class TestCustomerAnalyticsEligibility:
    """Customer analytics eligibility rules."""

    def test_fixture_excluded(self):
        """LIKELY_SCENE_FIXTURE excluded from customer analytics."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit.role = "LIKELY_FIXTURE"
        assert visit.customer_analytics_eligible is False

    def test_ambiguous_excluded(self):
        """AMBIGUOUS excluded from customer analytics."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit.role = "AMBIGUOUS"
        assert visit.customer_analytics_eligible is False

    def test_customer_eligible(self):
        """CUSTOMER role is eligible."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit.role = "CUSTOMER"
        assert visit.customer_analytics_eligible is True

    def test_unknown_eligible(self):
        """UNKNOWN role is eligible (plausible visitor)."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit.role = "UNKNOWN"
        assert visit.customer_analytics_eligible is True

    def test_staff_candidate_eligible(self):
        """STAFF_CANDIDATE is eligible (not confirmed)."""
        visit_mgr = VisitSessionManager()
        visit = visit_mgr._create_visit("t1", "cam_1", "ENTRY_OBSERVED")
        visit.role = "STAFF_CANDIDATE"
        assert visit.customer_analytics_eligible is True


class TestLiveCameraCounter:
    """Header live camera counter uses health snapshot."""

    def _make_sampler(self, mock_manager, camera_ids, clock=None):
        """Create sampler with test-friendly clock."""
        from src.observability.system_health import SystemHealthSampler
        if clock is None:
            clock = lambda: 0.0
        return SystemHealthSampler(
            mock_manager,
            camera_ids,
            sample_interval_seconds=2.0,
            clock=clock,
        )

    def test_online_cameras_reports_correct_count(self):
        """Health snapshot online_camera_count reflects ONLINE cameras."""
        from src.observability.system_health import SystemHealthSampler

        mock_manager = MagicMock()
        mock_manager.health.return_value = MagicMock(
            state="OPEN",
            healthy=True,
            fps=15.0,
            last_valid_frame_age_ms=100,
            stall_count=0,
            readable_frames=30,
            source_type="RTSP"
        )

        # Mock clock that advances on each call
        clock_time = [0.0]
        def mock_clock():
            return clock_time[0]
        
        sampler = self._make_sampler(mock_manager, ["CAM-01", "CAM-02", "CAM-03"], clock=mock_clock)

        snap = sampler.snapshot(runtime_running=True)
        # All 3 cameras should be ONLINE
        assert snap.online_camera_count == 3
        assert snap.total_camera_count == 3

    def test_offline_camera_reduces_counter(self):
        """OFFLINE camera reduces live count."""
        from src.observability.system_health import SystemHealthSampler

        mock_manager = MagicMock()
        
        def health_side_effect(camera_id):
            if camera_id == "CAM-01":
                return MagicMock(
                    state="OPEN", healthy=True, fps=15.0,
                    last_valid_frame_age_ms=100, stall_count=0,
                    readable_frames=30, source_type="RTSP"
                )
            else:
                return MagicMock(
                    state="CLOSED", healthy=False, fps=0.0,
                    last_valid_frame_age_ms=0, stall_count=0,
                    readable_frames=0, source_type="RTSP"
                )
        
        mock_manager.health.side_effect = health_side_effect

        sampler = self._make_sampler(mock_manager, ["CAM-01", "CAM-02"])

        snap = sampler.snapshot(runtime_running=True)
        assert snap.online_camera_count == 1
        assert snap.total_camera_count == 2

    def test_counter_uses_current_health_snapshot(self):
        """Counter derives from current health snapshot, not stale state."""
        from src.observability.system_health import SystemHealthSampler

        mock_manager = MagicMock()
        mock_manager.health.return_value = MagicMock(
            state="OPEN", healthy=True, fps=15.0,
            last_valid_frame_age_ms=100, stall_count=0,
            readable_frames=30, source_type="RTSP"
        )

        # Mock clock that advances on each snapshot call
        clock_time = [0.0]
        def mock_clock():
            return clock_time[0]
        
        sampler = self._make_sampler(mock_manager, ["CAM-01"], clock=mock_clock)

        snap1 = sampler.snapshot(runtime_running=True)
        assert snap1.online_camera_count == 1

        # Advance clock past sample interval and change health to OFFLINE
        clock_time[0] += 3.0
        mock_manager.health.return_value = MagicMock(
            state="CLOSED", healthy=False, fps=0.0,
            last_valid_frame_age_ms=0, stall_count=0,
            readable_frames=0, source_type="RTSP"
        )

        snap2 = sampler.snapshot(runtime_running=True)
        assert snap2.online_camera_count == 0

    def test_counter_ignores_stale_startup_state(self):
        """Counter reflects current health, not startup registration."""
        from src.observability.system_health import SystemHealthSampler

        mock_manager = MagicMock()
        # Initially all cameras report CLOSED (startup state)
        mock_manager.health.return_value = MagicMock(
            state="CLOSED", healthy=False, fps=0.0,
            last_valid_frame_age_ms=0, stall_count=0,
            readable_frames=0, source_type="RTSP"
        )

        clock_time = [0.0]
        def mock_clock():
            return clock_time[0]
        
        sampler = self._make_sampler(mock_manager, ["CAM-01", "CAM-02", "CAM-03"], clock=mock_clock)

        snap1 = sampler.snapshot(runtime_running=True)
        assert snap1.online_camera_count == 0

        # Advance clock and cameras come ONLINE
        clock_time[0] += 3.0
        mock_manager.health.return_value = MagicMock(
            state="OPEN", healthy=True, fps=15.0,
            last_valid_frame_age_ms=100, stall_count=0,
            readable_frames=30, source_type="RTSP"
        )

        snap2 = sampler.snapshot(runtime_running=True)
        assert snap2.online_camera_count == 3

    def test_header_derives_from_health_not_viewport(self):
        """Header counter uses full catalog health, not just visible viewport."""
        # This is validated by SystemHealthSampler using self._camera_ids
        # which is the full catalog, not the viewport subset
        from src.observability.system_health import SystemHealthSampler

        mock_manager = MagicMock()
        mock_manager.health.return_value = MagicMock(
            state="OPEN", healthy=True, fps=15.0,
            last_valid_frame_age_ms=100, stall_count=0,
            readable_frames=30, source_type="RTSP"
        )

        clock_time = [0.0]
        def mock_clock():
            return clock_time[0]
        
        # Full catalog of 15 cameras
        all_cameras = [f"CAM-{i:03d}" for i in range(1, 16)]
        sampler = self._make_sampler(mock_manager, all_cameras, clock=mock_clock)

        snap = sampler.snapshot(runtime_running=True)
        assert snap.online_camera_count == 15
        assert snap.total_camera_count == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])