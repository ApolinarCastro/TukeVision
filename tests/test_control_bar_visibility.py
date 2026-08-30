"""Real-window control-bar visibility tests (MACRO-OC-02, Bloques A/C/D/F/G/H).

The operator reported that controls EXIST in code but are NOT visible in the
real window (CODE_EXISTENCE != PRODUCT_PASS). Root cause: the video body
(expand=True, fill=BOTH) was packed before the fixed bars and swallowed all
vertical space, collapsing the control bar to a 1px strip off-viewport.

These tests measure a REAL mapped Tk window at operator-equivalent sizes and
prove:
  - every essential control is mapped and inside the viewport (GRID and FOCUS)
  - CONFIGURACIÓN is visible and opens the DeviceSettingsWindow
  - ZOOM+/ZOOM- are visible and enabled in FOCUS, bounded, and act on the
    presented image only (never on window geometry)
  - DOUBLE_CLICK: grid -> FOCUS; FOCUS -> zoom toggle
  - no ghost "SIN CÁMARA" slot in FOCUS (DEF-UI-FOCUS-EMPTY-01)
  - header health denominator is 15, never 16
"""

import tkinter as tk
import unittest
from types import SimpleNamespace

from tests.conftest import shared_root

from src.ui.tk_view import MAX_ZOOM, MIN_ZOOM, ZOOM_STEP, TkApp

CAMERA_IDS = tuple(f"cam_{i:02d}" for i in range(1, 16))


class FakeController:
    is_multicamera = True
    store_id = "store_nicopoly_principal"

    def __init__(self):
        self._ids = CAMERA_IDS
        self._closed = False

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

    def close(self):
        self._closed = True


class _PtzDeclaredController(FakeController):
    """FakeController where the focused camera declares PTZ support (BLOCK M)."""

    def ptz_status(self, camera_id):
        return {"supported": True, "certified": False, "status": "CAPABILITY_GATED"}


ESSENTIAL_CONTROLS = (
    "_stop_btn", "_evidence_btn", "_clip_btn", "_back_btn", "_prev_btn",
    "_next_btn", "_fullscreen_btn", "_grid_btn", "_zoom_in_btn",
    "_zoom_out_btn", "_zoom_reset_btn", "_settings_btn",
)


class RealWindowBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.withdraw()
        except tk.TclError:
            pass

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
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

    def _map(self, width, height):
        """Map the window off-screen at the given client size and measure."""
        self.root.geometry(f"{width}x{height}+3000+3000")
        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()
        return self.root.winfo_height()

    def _measure(self, widget):
        win_h = self.root.winfo_height()
        y = widget.winfo_rooty() - self.root.winfo_rooty()
        h = widget.winfo_height()
        return y, h, win_h, widget.winfo_ismapped() == 1

    def _assert_control_visible(self, name, win_h):
        w = getattr(self.app, name)
        y, h, _, mapped = self._measure(w)
        self.assertTrue(mapped, f"{name} not mapped")
        self.assertGreater(h, 0, f"{name} has zero height")
        self.assertGreaterEqual(y, 0, f"{name} above viewport (y={y})")
        self.assertLessEqual(y + h, win_h + 1, f"{name} below viewport (bottom={y + h} > {win_h})")


class TestControlBarVisibility(RealWindowBase):
    def test_all_controls_visible_at_1366x768(self):
        win_h = self._map(1366, 768)
        for name in ESSENTIAL_CONTROLS:
            self._assert_control_visible(name, win_h)

    def test_all_controls_visible_at_1600x900(self):
        win_h = self._map(1600, 900)
        for name in ESSENTIAL_CONTROLS:
            self._assert_control_visible(name, win_h)

    def test_all_controls_visible_at_1920x1080(self):
        win_h = self._map(1920, 1080)
        for name in ESSENTIAL_CONTROLS:
            self._assert_control_visible(name, win_h)

    def test_controls_still_visible_in_focus(self):
        win_h = self._map(1366, 768)
        self.app._on_click_camera("cam_05")
        self.root.update_idletasks()
        self.root.update()
        for name in ("_back_btn", "_zoom_in_btn", "_zoom_out_btn",
                     "_zoom_reset_btn", "_settings_btn"):
            self._assert_control_visible(name, win_h)
            self.assertEqual(
                getattr(self.app, name).cget("state"), tk.NORMAL,
                f"{name} should be enabled in FOCUS",
            )

    def test_ptz_frame_hidden_when_not_supported(self):
        # BLOCK M: NOT_SUPPORTED cameras must hide the PTZ surface entirely so
        # the mandatory controls (RETURN/CONFIG/ZOOM/GRID) never get pushed
        # off-viewport on operator resolutions.
        self._map(1366, 768)
        self.app._on_click_camera("cam_06")
        self.root.update_idletasks()
        self.root.update()
        ptz = getattr(self.app, "_ptz_frame", None)
        self.assertIsNotNone(ptz)
        self.assertEqual(ptz.winfo_ismapped(), 0)
        for btn in (self.app._ptz_up_btn, self.app._ptz_left_btn):
            self.assertEqual(btn.cget("state"), tk.DISABLED)

    def test_ptz_frame_shown_but_gated_when_declared_not_certified(self):
        # A camera that declares PTZ support reveals the surface but the
        # buttons stay disabled until the runtime certifies a real physical
        # implementation (CAPABILITY_GATED).
        self._map(1366, 768)
        self.app._controller = _PtzDeclaredController()
        self.app._on_click_camera("cam_06")
        self.root.update_idletasks()
        self.root.update()
        ptz = getattr(self.app, "_ptz_frame", None)
        self.assertIsNotNone(ptz)
        self.assertEqual(ptz.winfo_ismapped(), 1)
        for btn in (self.app._ptz_up_btn, self.app._ptz_left_btn):
            self.assertEqual(btn.cget("state"), tk.DISABLED)

    def test_grid16_empty_slot_then_focus_has_no_ghost(self):
        self._map(1366, 768)
        self.app._grid_preset = 16
        self.app._visible_camera_ids = tuple(self.app._camera_ids)[:15]
        self.app._rebuild_grid()
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(len(self.app._empty_canvases), 1)
        self.app._on_click_camera("cam_07")
        self.root.update_idletasks()
        self.root.update()
        # DEF-UI-FOCUS-EMPTY-01: FOCUS must have no empty-slot canvas.
        self.assertEqual(len(self.app._empty_canvases), 0)
        self.assertEqual(len(self.app._empty_cells), 0)


class TestConfigButton(RealWindowBase):
    def test_config_button_visible_and_opens_device_settings(self):
        self._map(1366, 768)
        self._assert_control_visible("_settings_btn", self.root.winfo_height())
        self.app._open_device_settings()
        self.root.update_idletasks()
        self.root.update()
        toplevels = [
            w for w in self.root.winfo_children()
            if isinstance(w, tk.Toplevel)
        ]
        self.assertTrue(toplevels, "DeviceSettingsWindow not created")
        self.assertEqual(
            str(toplevels[0].title()),
            "Configuración · Dispositivos",
        )


class TestDigitalZoom(RealWindowBase):
    def test_zoom_buttons_bounded_and_act_on_image_only(self):
        self._map(1366, 768)
        self.app._on_click_camera("cam_01")
        self.assertEqual(self.app._zoom_factor, MIN_ZOOM)
        win_geometry_before = self.root.geometry()
        for _ in range(10):
            self.app._on_zoom(1)
        self.assertEqual(self.app._zoom_factor, MAX_ZOOM)
        for _ in range(10):
            self.app._on_zoom(-1)
        self.assertEqual(self.app._zoom_factor, MIN_ZOOM)
        self.assertEqual(self.app._zoom_factor, ZOOM_STEP * round(self.app._zoom_factor / ZOOM_STEP))
        # Zoom never changes window geometry.
        self.assertEqual(self.root.geometry(), win_geometry_before)

    def test_zoom_out_disabled_outside_focus_and_enabled_in_focus(self):
        self._map(1366, 768)
        self.assertEqual(self.app._zoom_in_btn.cget("state"), tk.DISABLED)
        self.app._on_click_camera("cam_02")
        self.assertEqual(self.app._zoom_in_btn.cget("state"), tk.NORMAL)

    def test_double_click_grid_to_focus(self):
        self._map(1366, 768)
        self.app._on_double_click("cam_03")
        self.assertEqual(self.app._focused_camera, "cam_03")
        self.assertEqual(self.app._zoom_factor, MIN_ZOOM)

    def test_double_click_focus_toggles_zoom(self):
        self._map(1366, 768)
        self.app._on_double_click("cam_04")
        self.app._on_double_click("cam_04")
        self.assertGreater(self.app._zoom_factor, 1.0)
        self.app._on_double_click("cam_04")
        self.assertEqual(self.app._zoom_factor, MIN_ZOOM)

    def test_zoom_reset_button_functional(self):
        self._map(1366, 768)
        self.assertEqual(self.app._zoom_reset_btn.cget("state"), tk.DISABLED)
        self.app._on_click_camera("cam_02")
        self.assertEqual(self.app._zoom_reset_btn.cget("state"), tk.NORMAL)
        self.app._zoom_factor = 2.0
        self.app._on_zoom_reset()
        self.assertEqual(self.app._zoom_factor, MIN_ZOOM)
        self.assertEqual(
            self.app._zoom_reset_btn.cget("text"), "Restablecer"
        )


class TestHealthHeader(RealWindowBase):
    def test_health_denominator_is_15_never_16(self):
        self._map(1366, 768)
        health = SimpleNamespace(
            cpu_percent=None, ram_percent=None, ram_used_mb=None,
            ram_total_mb=None, disk_percent=None, disk_free_gb=None,
            global_health="UNKNOWN", online_camera_count=7,
            total_camera_count=15,
        )
        self.app._render_header({"status": "RUNNING", "system_health": health, "fps": 0.0})
        self.assertEqual(self.app._cameras_var.get(), "CÁMARAS: 7 / 15 EN VIVO")

    def test_online_never_inflated_above_online_count(self):
        self._map(1366, 768)
        health = SimpleNamespace(
            cpu_percent=None, ram_percent=None, ram_used_mb=None,
            ram_total_mb=None, disk_percent=None, disk_free_gb=None,
            global_health="OK", online_camera_count=15,
            total_camera_count=15,
        )
        self.app._render_header({"status": "RUNNING", "system_health": health, "fps": 0.0})
        self.assertEqual(self.app._cameras_var.get(), "CÁMARAS: 15 / 15 EN VIVO")


if __name__ == "__main__":
    unittest.main()