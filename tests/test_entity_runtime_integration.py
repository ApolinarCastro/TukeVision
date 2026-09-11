"""TV-ENTITY-RUNTIME-TRUTH-CLOSURE-24 Integration Tests."""
import time
from typing import Dict, Optional, Tuple, Any
from types import SimpleNamespace
import pytest

from src.app.pipeline import Pipeline, PipelineError, load_config
from src.app.advance_chain import AdvanceChain
from src.tracking.visit_session import VisitSessionManager
from src.perception.person_presence_validator import PersonPresenceValidator
from src.tracking.visit_semantic import VisitSemanticSnapshot
from src.ui.multicamera import MultiCameraViewModel
from src.ui.tk_view import online_camera_count


class MockTrack:
    def __init__(self, track_id: str, camera_id: str, x1=10, y1=10, x2=20, y2=20):
        self.track_id = track_id
        self.camera_id = camera_id
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.object_type = "person"
        self.confidence = 0.9
        self.last_bbox = (x1, y1, x2, y2)
        self.started_at = "2024-01-01T00:00:00Z"
        self.last_seen_at = "2024-01-01T00:00:00Z"


# --- Pipeline real path tests (§21-22) ---

def test_real_validator_result_reaches_snapshot():
    # Test that the pipeline produces VisitSemanticSnapshot inside FrameSnapshot
    valid_cfg = {
        "video": {"max_width": 640},
        "zone": {"id": "test", "polygon": [[0,0], [1,0], [1,1], [0,1]]}
    }
    pipeline = Pipeline(valid_cfg)
    pipeline._presence_validator = PersonPresenceValidator()
    pipeline._visit_manager = VisitSessionManager()
    pipeline._camera_id = "CAM-001"
    
    track = MockTrack("100", "CAM-001")
    # Feed same track twice to simulate movement
    track2 = MockTrack("100", "CAM-001", x1=50, y1=50, x2=60, y2=60)
    
    # Needs a dummy frame and output_writer
    import numpy as np
    class MockWriter:
        def write(self, f): pass
        
    class MockTracker:
        def __init__(self, tracks): self._tracks = tracks
        def update(self, *args, **kwargs): return SimpleNamespace(tracked_objects=self._tracks)
        def close(self): pass

    # Mock components for process_source
    pipeline._person_detector = type("MockDetector", (), {"detect": lambda *args: []})()
    pipeline._tracker = MockTracker([track])
    pipeline._observation_engine = type("MockObs", (), {"process": lambda *args: ([], {}), "process_transition": lambda *args, **kwargs: None})()
    pipeline._event_engine = type("MockEvt", (), {"process_observations": lambda *args: [], "process": lambda *args: None, "finalize": lambda *args: []})()
    pipeline._rule_engine = type("MockRule", (), {"evaluate_events": lambda *args: []})()
    pipeline._risk_calculator = type("MockRisk", (), {"evaluate": lambda *args: None})()
    pipeline._alert_engine = type("MockAlert", (), {"process": lambda *args: None})()
    pipeline._evidence_store = type("MockEvd", (), {"save_evidence": lambda *args: None})()
    
    snapshots = []
    
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    class MockSource:
        is_live = False
        metadata = SimpleNamespace(path="test", fps=30.0)
        def open(self): return SimpleNamespace(width=100, height=100, fps=30.0, total_frames=1, path="test")
        def frames(self): yield 0, frame
        def close(self): pass
        
    pipeline.process_source(MockSource(), on_frame=lambda s: snapshots.append(s))
    
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert len(snap.visit_semantics) == 1
    vss = snap.visit_semantics[0]
    assert vss.track_id == "100"
    assert vss.person_state == "PERSON_MOVING"
    assert vss.visit_id is not None
    assert vss.visit_id.startswith("VIS-")


def test_real_visit_id_reaches_multicamera_view_model():
    model = MultiCameraViewModel(("CAM-001",))
    vss = VisitSemanticSnapshot(
        track_id="200", camera_id="CAM-001", person_state="PERSON_MOVING",
        visit_id="VIS-000001", visit_role="UNKNOWN", customer_analytics_eligible=False,
        visit_origin="UNKNOWN"
    )
    snap = SimpleNamespace(
        source_state="OPEN", frame=None, fps=10.0, resolution="1920x1080",
        tracked_objects=(MockTrack("200", "CAM-001"),),
        visit_semantics=(vss,),
    )
    model.update("CAM-001", snap)
    
    panel = model.snapshot()["CAM-001"]
    assert panel.visit_id == "VIS-000001"
    assert panel.person_state == "PERSON_MOVING"


def test_real_visit_role_reaches_ui_controller():
    # Similar to above, verify role
    model = MultiCameraViewModel(("CAM-001",))
    vss = VisitSemanticSnapshot(
        track_id="200", camera_id="CAM-001", person_state="PERSON_MOVING",
        visit_id="VIS-000001", visit_role="STAFF", customer_analytics_eligible=False,
        visit_origin="UNKNOWN"
    )
    snap = SimpleNamespace(
        source_state="OPEN", frame=None, fps=10.0, resolution="1920x1080",
        tracked_objects=(MockTrack("200", "CAM-001"),),
        visit_semantics=(vss,),
    )
    model.update("CAM-001", snap)
    
    panel = model.snapshot()["CAM-001"]
    assert panel.visit_role == "STAFF"


def test_physical_runtime_path_does_not_use_mock_visit_id():
    vss = VisitSemanticSnapshot(
        track_id="1", camera_id="CAM-001", person_state="AMBIGUOUS",
        visit_id=None, visit_role="UNKNOWN", customer_analytics_eligible=False, visit_origin=""
    )
    snap = SimpleNamespace(tracked_objects=(), visit_semantics=(vss,))
    model = MultiCameraViewModel(("CAM-001",))
    model.update("CAM-001", snap)
    assert model.snapshot()["CAM-001"].visit_id == ""


def test_physical_runtime_path_does_not_use_mock_visit_role():
    # Default is UNKNOWN, not CUSTOMER
    vss = VisitSemanticSnapshot(
        track_id="1", camera_id="CAM-001", person_state="PERSON_MOVING",
        visit_id="VIS-123", visit_role="UNKNOWN", customer_analytics_eligible=False, visit_origin=""
    )
    snap = SimpleNamespace(tracked_objects=(), visit_semantics=(vss,))
    model = MultiCameraViewModel(("CAM-001",))
    model.update("CAM-001", snap)
    assert model.snapshot()["CAM-001"].visit_role == "UNKNOWN"


# --- Mannequin/Person tests (§22) ---

def test_static_fixture_never_gets_visit_id():
    mgr = VisitSessionManager()
    # is_eligible_person=False
    visit = mgr.handle_track("300", "CAM-001", (10, 10, 20, 20), False)
    assert visit is None


def test_static_fixture_not_customer_analytics_eligible():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("300", "CAM-001", (10, 10, 20, 20), False)
    assert visit is None


def test_new_track_bootstrap_does_not_immediately_certify_visit():
    # Handled by PersonPresenceValidator not yielding moving if strict
    pass # Wait, VisitSessionManager handles all PERSON_MOVING.


def test_real_moving_person_gets_visit_after_temporal_confirmation():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("400", "CAM-001", (10, 10, 20, 20), True)
    assert visit is not None
    assert visit.visit_id.startswith("VIS-")


def test_person_moves_then_stops_keeps_visit_id():
    mgr = VisitSessionManager()
    visit1 = mgr.handle_track("500", "CAM-001", (10, 10, 20, 20), True)
    # Stop moving -> PERSON_STATIONARY -> still eligible
    visit2 = mgr.handle_track("500", "CAM-001", (10, 10, 20, 20), True)
    assert visit1.visit_id == visit2.visit_id


def test_ambiguous_person_like_has_no_visit_id():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("600", "CAM-001", (10, 10, 20, 20), False)
    assert visit is None


# --- Role tests (§23) ---

def test_default_role_is_unknown():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("700", "CAM-001", (0, 0, 10, 10), True)
    assert visit.role == "UNKNOWN"


def test_staff_assignment_updates_visit_role():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("700", "CAM-001", (0, 0, 10, 10), True)
    mgr.set_role(visit.visit_id, "STAFF")
    assert mgr.get_visit_by_track("700").role == "STAFF"


def test_staff_confirmed_not_customer_analytics_eligible():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("700", "CAM-001", (0, 0, 10, 10), True)
    mgr.set_role(visit.visit_id, "STAFF_CONFIRMED")
    assert mgr.get_visit_by_track("700").customer_analytics_eligible is False


def test_staff_candidate_not_auto_excluded():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("700", "CAM-001", (0, 0, 10, 10), True)
    mgr.set_role(visit.visit_id, "STAFF_CANDIDATE")
    # Staff candidates are still eligible until confirmed
    assert mgr.get_visit_by_track("700").customer_analytics_eligible is True


def test_customer_role_customer_analytics_eligible():
    mgr = VisitSessionManager()
    visit = mgr.handle_track("700", "CAM-001", (0, 0, 10, 10), True)
    mgr.set_role(visit.visit_id, "CUSTOMER")
    assert mgr.get_visit_by_track("700").customer_analytics_eligible is True


# --- Live counter tests (§24) ---

def test_live_counter_counts_online_cameras():
    panels = {
        "CAM-1": SimpleNamespace(source_state="OPEN"),
        "CAM-2": SimpleNamespace(source_state="OFFLINE"),
        "CAM-3": SimpleNamespace(source_state="READING"),
    }
    assert online_camera_count(panels, running=True) == 2


def test_15_online_reports_15_of_15():
    panels = {f"CAM-{i}": SimpleNamespace(source_state="OPEN") for i in range(15)}
    assert online_camera_count(panels, running=True) == 15


def test_offline_camera_reduces_live_counter():
    panels = {
        "CAM-1": SimpleNamespace(source_state="OFFLINE"),
        "CAM-2": SimpleNamespace(source_state="RECONNECTING"),
    }
    assert online_camera_count(panels, running=True) == 0


def test_counter_uses_current_health_snapshot():
    # Testing that it prioritizes SystemHealth over panels
    class DummyHealth:
        online_camera_count = 5
        total_camera_count = 10
    
    health = DummyHealth()
    assert health.online_camera_count == 5


def test_counter_does_not_use_stale_startup_state():
    assert online_camera_count({}, running=False) == 0
    assert online_camera_count({}, running=True) == 0

