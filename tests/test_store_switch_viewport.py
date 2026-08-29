"""Store switch + viewport tests (MACRO-OC-02, Bloques A/J).

Validates the catalog/viewport split:
  - STORE_SWITCH_RUNTIME: switching stores only changes the visible viewport
  - late frames from a store no longer in view never raise "unsupported camera"
  - catalog panel state is preserved across switches (A -> B -> A)
  - grid layouts reflect the current viewport (4/16 -> 4 rows)
"""

import json
import unittest
from types import SimpleNamespace
from pathlib import Path

from src.ui.controller import UiController
from src.ui.multicamera import MultiCameraViewModel

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "config" / "multistore.example.json"


def load_example():
    with open(EXAMPLE_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


ALL_CAMERAS = (
    "cam_caja_01", "cam_caja_02", "cam_pasillo_01", "cam_acceso_01",
    "cam_pasillo_02", "cam_ip_vitrina_01", "cam_norte_caja_01",
)
PRINCIPAL = ALL_CAMERAS[:6]
NORTE = ("cam_norte_caja_01",)


def panel(frame_index=0):
    return SimpleNamespace(
        frame_index=frame_index, frame=None, source_state="OPEN", fps=15.0,
        detections=1, track_id=None, track_status=None, track_bbox=None,
        bboxes=None, event_id=None, event_type=None, event_confidence=None,
        inference_ref=None, temporal=None, behavior=None, risk=None,
        evidence=None, resolution="640x480",
    )


class TestMultiCameraViewModelCatalogViewport(unittest.TestCase):
    def setUp(self):
        self.model = MultiCameraViewModel(PRINCIPAL, catalog_ids=ALL_CAMERAS)

    def test_catalog_is_superset_of_viewport(self):
        self.assertEqual(self.model.catalog_ids, ALL_CAMERAS)
        self.assertEqual(self.model.camera_ids, PRINCIPAL)
        self.assertEqual(tuple(self.model.snapshot()), PRINCIPAL)

    def test_late_frame_from_off_viewport_catalog_camera_is_retained(self):
        # cam_norte_caja_01 belongs to the catalog but not the viewport.
        self.model.update("cam_norte_caja_01", panel())
        self.assertNotIn("cam_norte_caja_01", self.model.snapshot())
        # Switching to the norte viewport shows the retained panel state.
        self.model.select_viewport(NORTE)
        self.assertIn("cam_norte_caja_01", self.model.snapshot())

    def test_select_viewport_changes_snapshot_and_layout(self):
        self.model.select_viewport(NORTE)
        self.assertEqual(tuple(self.model.snapshot()), NORTE)
        self.assertEqual(self.model.layout, (NORTE,))

    def test_unknown_camera_still_raises(self):
        with self.assertRaises(ValueError):
            self.model.update("CAM-NOPE", panel())
        with self.assertRaises(ValueError):
            self.model.mark_state("CAM-NOPE", "OPEN")

    def test_viewport_camera_must_be_in_catalog(self):
        with self.assertRaises(ValueError):
            self.model.select_viewport(("CAM-NOPE",))

    def test_grid_layout_matches_viewport_size(self):
        sixteen = tuple(f"CAM-{i:02d}" for i in range(1, 17))
        model = MultiCameraViewModel(sixteen, catalog_ids=sixteen)
        self.assertEqual(len(model.layout), 4)  # 16 cameras -> 4 rows
        model.select_viewport(sixteen[:4])
        self.assertEqual(len(model.layout), 2)  # 4 cameras -> 2x2 grid


class TestUiControllerStoreSwitch(unittest.TestCase):
    def setUp(self):
        self.config = load_example()
        self.controller = UiController(
            config=self.config, camera_ids=ALL_CAMERAS
        )

    def test_catalog_and_initial_viewport_are_all_cameras(self):
        self.assertEqual(self.controller.camera_ids, ALL_CAMERAS)

    def test_switch_a_to_b_changes_viewport_only(self):
        self.controller.select_store("store_nicopoly_norte")
        self.assertEqual(self.controller.current_store, "store_nicopoly_norte")
        self.assertEqual(self.controller.camera_ids, NORTE)
        self.assertEqual(tuple(self.controller.poll_multicamera()), NORTE)

    def test_switch_a_to_b_to_a_preserves_catalog(self):
        self.controller.ingest_camera_snapshot("cam_caja_01", panel(frame_index=1))
        self.controller.select_store("store_nicopoly_norte")
        self.controller.select_store("store_nicopoly_principal")
        self.assertEqual(self.controller.camera_ids, PRINCIPAL)
        self.assertIn("cam_caja_01", self.controller.poll_multicamera())

    def test_late_frame_from_previous_store_is_accepted(self):
        self.controller.select_store("store_nicopoly_norte")
        # Late frame from the principal store still in the catalog.
        self.controller.ingest_camera_snapshot("cam_caja_01", panel(frame_index=7))
        self.controller.select_store("store_nicopoly_principal")
        panels = self.controller.poll_multicamera()
        self.assertEqual(panels["cam_caja_01"].frame_index, 7)

    def test_zone_filter_within_store(self):
        self.controller.select_store("store_nicopoly_principal", zone="Cajas")
        self.assertEqual(
            self.controller.camera_ids, ("cam_caja_01", "cam_caja_02")
        )

    def test_unknown_store_keeps_current_viewport(self):
        self.controller.select_store("store_inexistente")
        self.assertEqual(self.controller.current_store, "store_inexistente")
        # Viewport stays on the last valid catalog set.
        self.assertEqual(self.controller.camera_ids, ALL_CAMERAS)

    def test_ptz_status_remains_gated_not_certified(self):
        status = self.controller.ptz_status("cam_acceso_01")
        self.assertTrue(status["supported"])
        self.assertFalse(status["certified"])
        self.assertEqual(status["status"], "CAPABILITY_GATED")


if __name__ == "__main__":
    unittest.main()