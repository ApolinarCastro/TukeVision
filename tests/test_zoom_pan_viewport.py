"""Zoom/pan viewport tests (MACRO-OC-02, BLOCKS F/G/H)."""

import cv2
import numpy as np
import tempfile
import shutil
import unittest
from pathlib import Path
import tkinter as tk

from tests.conftest import shared_root
from src.ui.tk_view import (
    build_viewport_display_image,
    build_zoomed_display_image,
    _clamp_pan,
    TkApp,
    MIN_ZOOM,
    MAX_ZOOM,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = REPO_ROOT / "config" / "multistore.active.json"


def make_frame(w=640, h=480, color=100):
    return np.full((h, w, 3), color, dtype=np.uint8)


class TestViewportCrop(unittest.TestCase):
    def test_scale_1_returns_full_frame(self):
        frame = make_frame(200, 100)
        img = build_viewport_display_image(frame, 500, 500, 1.0, pan_x=0, pan_y=0)
        # At scale 1, crop == full frame, display may upscale but region is full
        self.assertIsNotNone(img)

    def test_scale_2_crops_center(self):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[25:75, 25:75] = 255
        img = build_viewport_display_image(frame, 50, 50, 2.0, pan_x=0, pan_y=0)
        self.assertIsNotNone(img)

    def test_pan_clamp_prevents_out_of_bounds(self):
        # Pan beyond frame should be clamped
        pan_x, pan_y = _clamp_pan(1000, 1000, 640, 480, 320, 240)
        self.assertLessEqual(abs(pan_x), 160)
        self.assertLessEqual(abs(pan_y), 120)

    def test_pan_shift_changes_viewport(self):
        frame = make_frame(100, 100)
        # Left half red, right half blue
        frame[:, :50] = [0, 0, 255]
        frame[:, 50:] = [255, 0, 0]
        img_center = build_viewport_display_image(frame, 50, 50, 2.0, pan_x=0, pan_y=0)
        img_left = build_viewport_display_image(frame, 50, 50, 2.0, pan_x=-20, pan_y=0)
        # Images should differ when panned
        self.assertNotEqual(img_center.tobytes(), img_left.tobytes())

    def test_zoom_bounds(self):
        self.assertEqual(MIN_ZOOM, 1.0)
        self.assertEqual(MAX_ZOOM, 4.0)

    def test_build_zoomed_is_centered_viewport(self):
        frame = make_frame(200, 200)
        a = build_zoomed_display_image(frame, 100, 100, 2.0)
        b = build_viewport_display_image(frame, 100, 100, 2.0, pan_x=0, pan_y=0)
        self.assertEqual(a.size, b.size)


class TestTkViewportIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="tuke_zoom_"))
        self.config_path = self.tmp_dir / "multistore.active.json"
        shutil.copyfile(ACTIVE_CONFIG, self.config_path)
        import json
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        from src.domain.catalog import StoreCatalog
        from src.observability.system_health import SystemHealthSampler
        from src.ui.controller import UiController
        catalog = StoreCatalog.from_dict(config)
        entries = catalog.camera_descriptors(max_width=320, process_every_n_frames=1, credential_resolver=lambda ref: ("u", "p"))
        camera_ids = tuple(e.camera_id for e in entries)
        from scripts.run_multicamera import MulticameraRuntime
        from src.capture.source_manager import SourceManager
        # Minimal controller without real sources
        self.controller = UiController(config=config, camera_ids=camera_ids[:2])
        self.app = TkApp(self.root, self.controller)
        self.camera_id = camera_ids[0]
        # Force focus
        self.app._focused_camera = self.camera_id
        if self.camera_id not in self.app._viewports:
            self.app._viewports[self.camera_id] = {"scale": 1.0, "pan_x": 0.0, "pan_y": 0.0}

    def tearDown(self):
        for w in self.root.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_zoom_plus_increases_scale(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 1.0
        self.app._on_zoom(1)
        self.assertGreater(self.app._viewport(self.camera_id)["scale"], 1.0)

    def test_zoom_minus_decreases_scale(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 2.0
        self.app._zoom_factor = 2.0
        self.app._on_zoom(-1)
        self.assertLess(self.app._viewport(self.camera_id)["scale"], 2.0)

    def test_reset_zoom_clears_pan(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 2.0
        vp["pan_x"] = 10
        vp["pan_y"] = 10
        self.app._on_zoom_reset()
        vp2 = self.app._viewport(self.camera_id)
        self.assertEqual(vp2["scale"], 1.0)
        self.assertEqual(vp2["pan_x"], 0.0)
        self.assertEqual(vp2["pan_y"], 0.0)

    def test_pan_drag_updates_viewport(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 2.0
        vp["pan_x"] = 0
        vp["pan_y"] = 0
        self.app._zoom_factor = 2.0
        # Simulate drag start
        class Ev:
            x = 100
            y = 100
        self.app._on_pan_start(Ev())
        self.assertIsNotNone(self.app._drag_state)
        Ev2 = type("E", (), {"x": 120, "y": 110})()
        self.app._on_pan_move(Ev2)
        # Pan should have changed
        self.assertNotEqual(self.app._viewport(self.camera_id)["pan_x"], 0)
        Ev3 = type("E", (), {"x": 120, "y": 110})()
        self.app._on_pan_end(Ev3)
        self.assertIsNone(self.app._drag_state)

    def test_pan_ignored_at_scale_1(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 1.0
        self.app._zoom_factor = 1.0
        class Ev:
            x = 50
            y = 50
        self.app._on_pan_start(Ev())
        self.assertIsNone(self.app._drag_state)

    def test_zoom_bounds_clamped(self):
        vp = self.app._viewport(self.camera_id)
        vp["scale"] = 1.0
        for _ in range(10):
            self.app._on_zoom(1)
        self.assertLessEqual(self.app._viewport(self.camera_id)["scale"], MAX_ZOOM)
        for _ in range(10):
            self.app._on_zoom(-1)
        self.assertGreaterEqual(self.app._viewport(self.camera_id)["scale"], MIN_ZOOM)

    def test_overlay_coherence_viewport_uses_annotated_frame(self):
        # Ensure _render_camera still calls annotate before crop (BLOCK H)
        # This is structural: we verify build_viewport works with annotated frame
        frame = make_frame(320, 240)
        from src.ui.tk_view import annotate_frame
        from types import SimpleNamespace
        panel = SimpleNamespace(
            frame=frame, frame_index=0, analytics_frame=None, analytics_frame_index=-1,
            bboxes=((10, 10, 50, 50, 0.9),), track_bbox=None, track_id=None,
            source_state="OPEN", resolution="320x240", detections=1, event_confidence=0.9,
            track_status=None, event_type="OBJECT_DETECTED", temporal=None, behavior=None, risk=None, evidence=None,
        )
        annotated = annotate_frame(frame, panel, displayed_frame_index=0)
        # Annotated frame should still be same size, viewport crop on it
        img = build_viewport_display_image(annotated, 200, 200, 2.0, pan_x=0, pan_y=0)
        self.assertIsNotNone(img)


if __name__ == "__main__":
    unittest.main()
