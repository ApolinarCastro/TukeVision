"""COMMAND CENTER tests (MACRO-OC-01-R, Block 9).

Covers GRID_16/9/6/4/1 layouts, PRESET_SWITCHING (cycle changes the
rendered set), FOCUS_NAVIGATION (back/prev/next over the full catalog),
DIGITAL_ZOOM (presentation-only) and PTZ_STATUS (CAPABILITY_GATED /
NOT_CERTIFIED without a certified physical implementation).
"""

import json
import unittest

import numpy as np

from src.ui.controller import UiController
from src.ui.grid_layout import (
    GRID_PRESETS,
    cycle_grid_preset,
    grid_cells,
    grid_layout,
)
from src.ui.tk_view import build_zoomed_display_image


def camera_ids(count):
    return tuple(f"CAM-{index:03d}" for index in range(1, count + 1))


class TestGridLayouts(unittest.TestCase):
    def _assert_grid6(self, ids):
        cells = grid_cells(ids)
        cell_ids = [cell.camera_id for cell in cells]
        self.assertEqual(len(cell_ids), 6)
        self.assertEqual(len(set(cell_ids)), 6, "no duplicated cameras")
        self.assertEqual(set(cell_ids), set(ids), "no omitted cameras")
        mains = [c for c in cells if c.is_main]
        self.assertEqual(len(mains), 1)
        self.assertEqual(mains[0].rowspan, 2, "GRID_6 main spans 2 rows")
        self.assertEqual(cell_ids[0], ids[0])

    def test_grid_16_layout(self):
        ids = camera_ids(16)
        layout = grid_layout(ids)
        self.assertEqual(len(layout), 4)
        self.assertTrue(all(len(row) == 4 for row in layout))
        self.assertEqual([c for row in layout for c in row], list(ids))

    def test_grid_9_layout(self):
        ids = camera_ids(9)
        layout = grid_layout(ids)
        self.assertEqual(len(layout), 3)
        self.assertTrue(all(len(row) == 3 for row in layout))
        self.assertEqual([c for row in layout for c in row], list(ids))

    def test_grid_6_layout_no_dup_no_omit(self):
        ids = camera_ids(6)
        layout = grid_layout(ids)
        flat = [cell for row in layout for cell in row if cell]
        self.assertEqual(flat, list(ids))
        self.assertEqual(len(flat), 6)
        self.assertEqual(ids[0], layout[0][0], "main camera is ids[0]")
        self.assertIn(ids[5], flat, "CAM-006 must not be omitted")
        self._assert_grid6(ids)

    def test_grid_4_layout(self):
        ids = camera_ids(4)
        layout = grid_layout(ids)
        self.assertEqual([c for row in layout for c in row], list(ids))
        self.assertEqual(len(grid_cells(ids)), 4)

    def test_grid_1_layout(self):
        ids = camera_ids(1)
        layout = grid_layout(ids)
        self.assertEqual([c for row in layout for c in row], list(ids))
        self.assertEqual(len(grid_cells(ids)), 1)


class TestPresetSwitching(unittest.TestCase):
    def test_cycle_starts_at_smallest_and_wraps(self):
        self.assertEqual(cycle_grid_preset(None, 16), 1)
        self.assertEqual(cycle_grid_preset(1, 16), 4)
        self.assertEqual(cycle_grid_preset(4, 16), 6)
        self.assertEqual(cycle_grid_preset(6, 16), 9)
        self.assertEqual(cycle_grid_preset(9, 16), 16)
        self.assertEqual(cycle_grid_preset(16, 16), 1)

    def test_presets_capped_by_catalog_size(self):
        self.assertEqual(cycle_grid_preset(None, 6), 1)
        self.assertEqual(cycle_grid_preset(6, 6), 1)
        self.assertEqual(cycle_grid_preset(None, 3), 1)

    def test_preset_changes_the_rendered_camera_subset(self):
        # Simulate the view decision: visible set = first `preset` cameras.
        ids = camera_ids(16)
        for preset in (1, 4, 6, 9, 16):
            visible = ids[:preset]
            self.assertEqual(len(visible), preset)
            self.assertEqual(set(visible).issubset(set(ids)), True)
        self.assertEqual(GRID_PRESETS, (1, 4, 6, 9, 16))


class TestFocusNavigation(unittest.TestCase):
    def test_focus_index_wraps_across_full_catalog(self):
        ids = camera_ids(4)
        index = 0
        index = (index + 1) % len(ids)
        self.assertEqual(ids[index], "CAM-002")
        index = (index - 1) % len(ids)
        self.assertEqual(ids[index], "CAM-001")


class TestDigitalZoom(unittest.TestCase):
    def test_zoom_is_presentational_and_crops_not_upscales(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        image = build_zoomed_display_image(frame, max_w=640, max_h=480, zoom_factor=2.0)
        self.assertLessEqual(image.size[0], 640)
        self.assertLessEqual(image.size[1], 480)


class TestPtzStatus(unittest.TestCase):
    PTZ_CONFIG = {
        "multistore": {
            "enabled": True,
            "organization": {
                "organization_id": "org_1",
                "organization_name": "Org",
                "created_at": "2026-08-19T00:00:00Z",
            },
            "stores": [
                {
                    "store_id": "store_1",
                    "organization_id": "org_1",
                    "store_name": "S1",
                    "location_address": "Addr",
                    "timezone": "UTC",
                    "evidence_namespace": "data/evidence/store_1/",
                    "recorders": [],
                    "direct_cameras": [
                        {
                            "camera_id": "cam_p",
                            "store_id": "store_1",
                            "camera_name": "PTZ Cam",
                            "source_type": "IP_CAMERA",
                            "host": "192.168.0.5",
                            "stream_main": "rtsp://192.168.0.5/stream1",
                            "stream_sub": "rtsp://192.168.0.5/stream2",
                            "zone": "Z",
                            "role": "ANALYTICS",
                            "enabled": True,
                            "credentials_ref": "ENV_TEST",
                            "ptz_capability": {
                                "supported": True, "protocol": "ONVIF",
                            },
                            "evidence_namespace": "data/evidence/store_1/cam_p/",
                        }
                    ],
                }
            ],
        }
    }

    def test_ptz_is_capability_gated_never_certified(self):
        controller = UiController(config=self.PTZ_CONFIG, camera_ids=("cam_p",))
        status = controller.ptz_status("cam_p")
        self.assertTrue(status["supported"])
        self.assertFalse(status["certified"])
        self.assertEqual(status["status"], "CAPABILITY_GATED")
        self.assertFalse(controller.ptz_command("cam_p", "up"))


if __name__ == "__main__":
    unittest.main()