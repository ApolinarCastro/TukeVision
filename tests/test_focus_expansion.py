"""DEF-UI-FOCUS-SIZE-02: FOCUS fills the workspace between header and bar.

ROOT_CAUSE: entering FOCUS kept the previous grid's residual row/column
weights (e.g. rows 1..3 of a 4x4 grid), so the single focused cell only
received a fraction of the vertical workspace. These tests prove the focused
canvas now fills the area (>= 60% of the video workspace in both axes), that
the aspect ratio is preserved (letterbox/pillarbox, never stretched), and
that zoom operates on the expanded view.
"""

import tkinter as tk
import unittest

import numpy as np

from tests.conftest import shared_root

from src.ui.tk_view import (
    build_display_image,
    build_zoomed_display_image,
    TkApp,
)

CAMERA_IDS = tuple(f"cam_{i:02d}" for i in range(1, 16))


class FakeController:
    is_multicamera = True
    store_id = "store_nicopoly_principal"

    def __init__(self):
        self._ids = CAMERA_IDS

    @property
    def camera_ids(self):
        return self._ids

    def stores(self):
        return ["store_nicopoly_principal"]

    def store_zones(self, store_id):
        return []

    def select_store(self, store_id, zone=""):
        self.store_id = store_id

    def poll_state(self):
        return {
            "status": "RUNNING", "store_id": self.store_id,
            "system_health": None, "alert_log": [], "evidence_paths": [],
            "clips_available": None, "fps": 0.0,
        }

    def poll_multicamera(self):
        return {}

    def ptz_status(self, camera_id):
        return {"supported": False, "certified": False, "status": "CAPABILITY_GATED"}

    def ptz_command(self, camera_id, action):
        return False

    def mark_ui_rendered(self, camera_id, frame_index):
        pass

    def latest_evidence(self):
        return None

    def clip_target(self):
        return None

    def review_available(self):
        return False

    def close(self):
        pass


class FocusExpansionBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    def setUp(self):
        self._clear_children()
        self.app = TkApp(self.root, FakeController())
        self.root.geometry("1366x768+3000+3000")
        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()

    def _clear_children(self):
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass

    def tearDown(self):
        self._clear_children()
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

    def _enter_focus_from_grid(self, preset, camera_id):
        self.app._grid_preset = preset
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:preset]
        self.app._rebuild_grid()
        self.root.update_idletasks()
        self.root.update()
        self.app._on_click_camera(camera_id)
        self.root.update_idletasks()
        self.root.update()

    def _focus_geometry(self):
        canvas = self.app._video_canvases[self.app._focused_camera]
        wrap = self.app._video_wrap
        return (
            canvas.winfo_width(), canvas.winfo_height(),
            wrap.winfo_width(), wrap.winfo_height(),
        )

    def _assert_focus_fills_workspace(self):
        cw, ch, ww, wh = self._focus_geometry()
        self.assertGreater(cw, 0)
        self.assertGreater(ch, 0)
        self.assertGreaterEqual(
            cw, 0.6 * ww,
            f"FOCUS canvas width {cw} should fill workspace width {ww}",
        )
        self.assertGreaterEqual(
            ch, 0.6 * wh,
            f"FOCUS canvas height {ch} should fill workspace height {wh}",
        )


class TestFocusExpansion(FocusExpansionBase):
    def test_focus_fills_workspace_after_grid16(self):
        # GRID16 leaves rows 0..3 weighted; FOCUS must not inherit the split.
        self._enter_focus_from_grid(16, "cam_05")
        self._assert_focus_fills_workspace()

    def test_focus_fills_workspace_after_grid9(self):
        self._enter_focus_from_grid(9, "cam_03")
        self._assert_focus_fills_workspace()

    def test_focus_fills_workspace_after_grid1(self):
        self._enter_focus_from_grid(1, "cam_01")
        self._assert_focus_fills_workspace()

    def test_focus_canvas_is_single_large_panel(self):
        self._enter_focus_from_grid(16, "cam_09")
        self.assertEqual(len(self.app._video_canvases), 1)
        self.assertEqual(self.app._focused_camera, "cam_09")
        cw, ch, _, _ = self._focus_geometry()
        self.assertGreaterEqual(cw, 500, "focused canvas must be large, not a tile")
        self.assertGreaterEqual(ch, 300, "focused canvas must be large, not a tile")

    def test_return_to_grid_restores_grid_geometry(self):
        self._enter_focus_from_grid(16, "cam_07")
        self.app._on_back_to_grid()
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(len(self.app._video_canvases), 16 - 1)  # 15 + empty
        self.assertEqual(len(self.app._empty_canvases), 1)

    def test_zoom_operates_on_expanded_focus(self):
        self._enter_focus_from_grid(16, "cam_02")
        self.app._on_zoom(1)
        self.assertGreater(self.app._zoom_factor, 1.0)
        self.assertEqual(self.app._focused_camera, "cam_02")
        self.app._on_zoom_reset()
        self.assertEqual(self.app._zoom_factor, 1.0)


class TestDisplayGeometry(unittest.TestCase):
    def _aspect(self, frame):
        h, w = frame.shape[:2]
        return w / h

    def test_aspect_ratio_preserved_when_focus_upscales(self):
        frame = np.zeros((600, 800, 3), dtype=np.uint8)
        image = build_display_image(frame, 1000, 700, allow_upscale=True)
        self.assertAlmostEqual(
            image.width / image.height, self._aspect(frame), places=1,
        )
        self.assertGreater(image.width, 800, "FOCUS should use the available area")
        self.assertGreater(image.height, 600)

    def test_grid_default_never_upscales(self):
        frame = np.zeros((600, 800, 3), dtype=np.uint8)
        image = build_display_image(frame, 1000, 700)
        self.assertEqual((image.width, image.height), (800, 600))

    def test_zoom_on_expanded_focus_preserves_aspect(self):
        frame = np.zeros((1080, 1440, 3), dtype=np.uint8)
        zoomed = build_zoomed_display_image(
            frame, 1000, 700, 2.0, allow_upscale=True
        )
        self.assertAlmostEqual(
            zoomed.width / zoomed.height, self._aspect(frame), places=1,
        )
        # Note: 1440/2 = 720. 720x540 crop fits into 1000x700 by scaling to 933x700
        # which is > 720. We just assert > 720 since crop is 720.
        self.assertGreater(zoomed.width, 720)


if __name__ == "__main__":
    unittest.main()