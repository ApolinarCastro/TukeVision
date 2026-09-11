"""FOCUS return navigation tests (MACRO-OC-02, Bloques F/G/H/I).

Validates with the real TkApp (withdrawn root) that:
  - FOCUS saves the previous layout context (grid/preset/order/store/zone)
  - GRID16 -> FOCUS -> VOLVER restores exactly GRID16 (never defaults)
  - the same exact-return holds for GRID9 / GRID4
  - the return button is visible and enabled in FOCUS
  - ESC returns to the previous grid ONLY in FOCUS and never closes the app
  - 15 physical cameras render one empty slot over the 16-cell grid
"""

import tkinter as tk
import unittest

from tests.conftest import shared_root
from src.ui.tk_view import TkApp


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
            "status": "RUNNING",
            "store_id": self.store_id,
            "system_health": None,
            "alert_log": [],
            "evidence_paths": [],
            "clips_available": None,
            "fps": 0.0,
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


class TkAppFocusBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # One Tk root per process avoids flaky ttk theme reloads on Windows.
        cls.root = shared_root()

    def setUp(self):
        self._clear_children()
        self.app = TkApp(self.root, FakeController())

    def _clear_children(self):
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass

    def tearDown(self):
        self._clear_children()


class TestFocusReturnNavigation(TkAppFocusBase):
    def test_initial_grid_is_all_15_cameras(self):
        self.assertEqual(len(self.app._visible_camera_ids), 15)
        self.assertIsNone(self.app._grid_preset)
        self.assertEqual(self.app._grid_capacity(), 15)

    def test_enter_focus_saves_context_and_enables_return(self):
        self.app._on_click_camera("cam_07")
        self.assertEqual(self.app._focused_camera, "cam_07")
        self.assertEqual(self.app._back_btn.cget("state"), tk.NORMAL)
        ctx = self.app._previous_context
        self.assertEqual(ctx["visible_camera_ids"], CAMERA_IDS)
        self.assertIsNone(ctx["grid_preset"])
        self.assertEqual(ctx["store"], "store_nicopoly_principal")

    def test_return_from_focus_restores_exact_initial_grid(self):
        self.app._on_click_camera("cam_07")
        self.app._on_back_to_grid()
        self.assertIsNone(self.app._focused_camera)
        self.assertEqual(self.app._visible_camera_ids, CAMERA_IDS)
        self.assertIsNone(self.app._grid_preset)
        self.assertEqual(self.app._back_btn.cget("state"), tk.DISABLED)

    def test_grid16_focus_return_preserves_grid16(self):
        self.app._grid_preset = 16
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:15]
        self.app._on_click_camera("cam_09")
        self.app._on_back_to_grid()
        self.assertEqual(self.app._grid_preset, 16)
        self.assertEqual(len(self.app._visible_camera_ids), 15)
        self.assertEqual(self.app._visible_camera_ids[0], "cam_01")
        self.assertEqual(self.app._visible_camera_ids[-1], "cam_15")

    def test_grid9_focus_return_preserves_grid9(self):
        self.app._grid_preset = 9
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:9]
        self.app._on_click_camera("cam_05")
        self.app._on_back_to_grid()
        self.assertEqual(self.app._grid_preset, 9)
        self.assertEqual(self.app._visible_camera_ids, CAMERA_IDS[:9])

    def test_grid4_focus_return_preserves_grid4_and_ordering(self):
        self.app._grid_preset = 4
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:4]
        self.app._on_click_camera("cam_03")
        self.app._on_back_to_grid()
        self.assertEqual(self.app._grid_preset, 4)
        self.assertEqual(self.app._visible_camera_ids, CAMERA_IDS[:4])

    def test_return_button_visible_in_focus(self):
        self.app._on_click_camera("cam_01")
        self.assertEqual(self.app._back_btn.cget("state"), tk.NORMAL)
        # The button is always present and managed by the packer (visible).
        self.assertEqual(self.app._back_btn.winfo_manager(), "pack")

    def test_esc_returns_to_previous_grid_in_focus(self):
        self.app._grid_preset = 4
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:4]
        self.app._on_click_camera("cam_02")
        self.app._on_escape()
        self.assertIsNone(self.app._focused_camera)
        self.assertEqual(self.app._grid_preset, 4)
        self.assertEqual(self.app._visible_camera_ids, CAMERA_IDS[:4])

    def test_esc_in_grid_mode_does_not_close_app(self):
        self.assertIsNone(self.app._focused_camera)
        self.app._on_escape()
        self.assertTrue(self.root.winfo_exists())
        self.assertEqual(self.app._visible_camera_ids, CAMERA_IDS)

    def test_focus_navigation_does_not_change_store(self):
        self.app._on_click_camera("cam_06")
        self.assertEqual(self.app._controller.store_id, "store_nicopoly_principal")
        self.app._on_back_to_grid()
        self.assertEqual(self.app._controller.store_id, "store_nicopoly_principal")

    def test_grid16_renders_one_empty_slot_for_15_cameras(self):
        self.app._grid_preset = 16
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:15]
        self.app._rebuild_grid()
        self.assertEqual(len(self.app._empty_canvases), 1)
        self.assertEqual(len(self.app._video_canvases), 15)

    def test_video_context_preserved_across_navigation(self):
        # BLOCK Q: FOCUS / ZOOM / PREV / NEXT / RETURN must never destroy the
        # video context: the controller panels keep their frames and still
        # accept newer frames after the full navigation sequence.
        from types import SimpleNamespace

        import numpy as np

        from src.ui.controller import UiController

        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass
        controller = UiController(config={}, camera_ids=CAMERA_IDS)
        controller.is_multicamera = True
        for camera_id in CAMERA_IDS:
            controller.ingest_camera_snapshot(camera_id, SimpleNamespace(
                frame_index=5,
                frame=np.full((4, 6, 3), 7, dtype=np.uint8),
                source_state="OPEN", fps=2.0,
            ))
        app = TkApp(self.root, controller)
        app._on_double_click("cam_05")
        app._on_zoom(1)
        app._on_next_camera()
        app._on_prev_camera()
        app._on_back_to_grid()
        panels = controller.poll_multicamera()
        self.assertEqual(panels["cam_05"].frame_index, 5)
        self.assertEqual(panels["cam_05"].source_state, "OPEN")
        # The same live context still accepts newer frames after navigation.
        controller.ingest_camera_snapshot("cam_05", SimpleNamespace(
            frame_index=6,
            frame=np.full((4, 6, 3), 8, dtype=np.uint8),
            source_state="OPEN", fps=2.0,
        ))
        self.assertEqual(controller.poll_multicamera()["cam_05"].frame_index, 6)
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass


if __name__ == "__main__":
    unittest.main()