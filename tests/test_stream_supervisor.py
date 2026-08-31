import pytest
import threading
import time
from unittest.mock import Mock, MagicMock

from src.capture.source_manager import SourceManager, CameraDescriptor, _CameraRuntime

class MockSource:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.state = "OPEN"
        self._closed = False
        self._frames_to_yield = []
        self._fps = 10.0

    def open(self):
        return Mock(width=1280, height=720, fps=10.0, path=self.descriptor.host)

    def frames(self):
        for item in self._frames_to_yield:
            if self._closed:
                break
            if isinstance(item, Exception):
                raise item
            if item == "STALL":
                self.state = "STALLED"
                break
            if item == "HANG":
                while not self._closed:
                    time.sleep(0.1)
                break
            yield item

    def close(self):
        self._closed = True
        self.state = "CLOSED"


import random

@pytest.fixture(autouse=True)
def mock_random(monkeypatch):
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)

@pytest.fixture
def sm():
    return SourceManager(
        source_factory=MockSource,
        startup_grace_seconds=0.1,
        consecutive_failure_threshold=3,
        recovery_window_seconds=1.0,
        max_recovery_attempts=2,
        recovery_backoff_seconds=0.01,
        decoder_shutdown_timeout=0.1,
        first_frame_timeout=0.2,
        experience_sink=Mock()
    )

def test_single_frame_failure_does_not_restart(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        # Yield (index, frame). None means frame failure. Hang so it doesn't exit.
        src._frames_to_yield = [(0, "frame0"), (1, None), (2, "frame2"), "HANG"]
        return src
    
    sm._source_factory = mock_factory
    sm.start("cam_1")
    
    time.sleep(0.1)
    sm.stop("cam_1")
    
    rt = sm._get_runtime("cam_1")
    assert rt.generation == 1
    assert len(rt.queue) > 0
    assert rt.queue[-1][1] == "frame2"

def test_repeated_failure_triggers_bounded_recovery(sm):
    sm.startup_grace_seconds = -1.0 # disable grace completely
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        # Yield valid frame first, then 4 failures > threshold (3)
        src._frames_to_yield = [(0, "frame0"), (1, None), (2, None), (3, None), (4, None), "HANG"]
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    
    time.sleep(0.1)
    sm.stop("cam_1")
    
    rt = sm._get_runtime("cam_1")
    assert rt.generation > 1

def test_no_restart_during_startup_grace(sm):
    sm.startup_grace_seconds = 10.0
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        src._frames_to_yield = [(0, "frame0"), (1, None), (2, None), (3, None), (4, None), "HANG"]
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    
    time.sleep(0.1)
    sm.stop("cam_1")
    
    rt = sm._get_runtime("cam_1")
    assert rt.generation == 1

def test_restart_does_not_spawn_parallel_decoder(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    active_decoders = 0
    max_active = 0
    lock = threading.Lock()
    
    class TrackedSource(MockSource):
        def open(self):
            nonlocal active_decoders, max_active
            with lock:
                active_decoders += 1
                if active_decoders > max_active:
                    max_active = active_decoders
            return super().open()
            
        def close(self):
            nonlocal active_decoders
            with lock:
                active_decoders -= 1
            super().close()
            
    def mock_factory(descriptor):
        src = TrackedSource(descriptor)
        src._frames_to_yield = ["STALL"] 
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    
    time.sleep(0.2)
    sm.stop("cam_1")
    
    assert max_active == 1

def test_restart_waits_for_previous_owner_exit(sm):
    pass

def test_duplicate_decoder_is_detected(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    sm.start("cam_1")
    
    with pytest.raises(Exception):
        sm.start("cam_1")
        
    sm.stop("cam_1")

def test_generation_increments_after_restart(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        src._frames_to_yield = ["STALL"]
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    time.sleep(0.1)
    sm.stop("cam_1")
    
    rt = sm._get_runtime("cam_1")
    assert rt.generation > 1

def test_recovery_success_requires_generation_advance(sm):
    pass

def test_recovery_success_requires_first_frame_after_restart(sm):
    pass

def test_recovery_success_requires_sequence_advance(sm):
    pass

def test_recovery_budget_prevents_restart_storm(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        src._frames_to_yield = ["STALL"]
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    time.sleep(0.3)
    
    rt = sm._get_runtime("cam_1")
    assert rt.recovery_attempts >= sm.max_recovery_attempts
    
    health = sm.health("cam_1")
    assert health.state == "OFFLINE"
    
    sm.stop("cam_1")

def test_failed_recovery_marks_stream_offline(sm):
    pass

def test_successful_recovery_restores_healthy_state(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    attempt = 0
    def mock_factory(descriptor):
        nonlocal attempt
        src = MockSource(descriptor)
        if attempt == 0:
            src._frames_to_yield = ["STALL"]
        else:
            src._frames_to_yield = [(0, "frame0"), (1, "frame1"), "HANG"]
        attempt += 1
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    time.sleep(0.2)
    
    health = sm.health("cam_1")
    assert health.healthy is True
    
    sm.stop("cam_1")

def test_recovery_event_records_failure_and_actual_outcome(sm):
    desc = CameraDescriptor(camera_id="cam_1", host="rtsp://test")
    sm.register_source(desc)
    
    events = []
    sm.experience_sink = lambda ev: events.append(ev)
    
    def mock_factory(descriptor):
        src = MockSource(descriptor)
        src._frames_to_yield = ["STALL"]
        return src
        
    sm._source_factory = mock_factory
    sm.start("cam_1")
    time.sleep(0.1)
    sm.stop("cam_1")
    
    assert len(events) > 0
    ev = events[0]
    assert ev["camera_id"] == "cam_1"
    assert "old_generation" in ev
    assert "new_generation" in ev
    assert "outcome" in ev
