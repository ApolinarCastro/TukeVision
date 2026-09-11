import pytest
import threading
import time
from src.ui.controller import UiController

class FakeSourceManager:
    def __init__(self):
        self.switches = []
        self.lock = threading.Lock()
        self.switch_event = threading.Event()
        self.active_transitions = 0
        self.max_active = 0
    
    def switch_stream(self, cam, subtype, max_width=0):
        with self.lock:
            self.active_transitions += 1
            if self.active_transitions > self.max_active:
                self.max_active = self.active_transitions
        
        # Simulate slow switch
        self.switch_event.wait()
        
        with self.lock:
            self.switches.append((cam, subtype))
            self.active_transitions -= 1

def test_set_focus_is_non_blocking():
    ctrl = UiController(camera_ids=("cam_08", "cam_09"))
    fake_mgr = FakeSourceManager()
    ctrl._manager = fake_mgr
    
    start_time = time.time()
    ctrl.set_focus("cam_08")
    end_time = time.time()
    
    assert end_time - start_time < 0.1  # Must return immediately
    
    fake_mgr.switch_event.set()
    time.sleep(0.1) # allow worker to finish
    ctrl.close()

def test_latest_intent_wins():
    ctrl = UiController(camera_ids=("cam_08", "cam_09", "cam_12"))
    fake_mgr = FakeSourceManager()
    ctrl._manager = fake_mgr
    
    # Send cam08, which will block in switch_stream
    ctrl.set_focus("cam_08")
    time.sleep(0.05) # give worker time to pick it up and block
    
    # Send rapid intents
    ctrl.set_focus("cam_09")
    ctrl.set_focus("cam_12")
    
    fake_mgr.switch_event.set()
    time.sleep(0.2) # allow worker to finish processing
    
    with fake_mgr.lock:
        switches = fake_mgr.switches
        
    assert fake_mgr.max_active == 1  # Only 1 transition at a time
    
    # Check that cam12 was processed, but cam09 was skipped because 12 overwrote it
    main_switches = [cam for cam, sub in switches if sub == 0]
    assert "cam_12" in main_switches
    assert "cam_09" not in main_switches
    ctrl.close()

def test_no_thread_explosion():
    ctrl = UiController(camera_ids=("cam_08",))
    fake_mgr = FakeSourceManager()
    ctrl._manager = fake_mgr
    fake_mgr.switch_event.set() # Don't block
    
    initial_threads = threading.active_count()
    for _ in range(100):
        ctrl.set_focus("cam_08")
    
    time.sleep(0.1)
    final_threads = threading.active_count()
    # At most 1 thread added by the worker
    assert final_threads - initial_threads <= 2
    ctrl.close()
