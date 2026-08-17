import unittest
from types import SimpleNamespace

import numpy as np

from src.ui.multicamera import CAMERA_IDS, PANEL_LAYOUT, MultiCameraViewModel
from src.ui.controller import UiController


class TestMultiCameraView(unittest.TestCase):
    def test_controller_orchestrates_four_snapshots_without_capture(self):
        controller = UiController(config={})
        for index, camera_id in enumerate(CAMERA_IDS):
            controller.ingest_camera_snapshot(camera_id, SimpleNamespace(
                frame_index=index + 1, frame=np.full((2, 2, 3), index),
                source_state="OPEN", fps=2.0,
            ))
        panels = controller.poll_multicamera()
        self.assertEqual(tuple(panels), CAMERA_IDS)
        self.assertEqual(int(panels["CAM-003"].frame[0, 0, 0]), 2)

    def test_fixed_layout_and_mapping(self):
        view = MultiCameraViewModel()
        self.assertEqual(view.layout, PANEL_LAYOUT)
        self.assertEqual(tuple(view.snapshot()), CAMERA_IDS)

    def test_latest_wins_and_camera_isolation(self):
        view = MultiCameraViewModel()
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        view.update("CAM-001", SimpleNamespace(frame_index=2, frame=frame, source_state="OPEN", fps=3))
        view.update("CAM-001", SimpleNamespace(frame_index=1, frame=None, source_state="FAILED", fps=0))
        view.mark_state("CAM-003", "FAILED")
        self.assertEqual(view.panel("CAM-001").frame_index, 2)
        self.assertEqual(view.panel("CAM-001").source_state, "OPEN")
        self.assertEqual(view.panel("CAM-003").source_state, "FAILED")
        self.assertEqual(view.panel("CAM-002").source_state, "OFFLINE")

    def test_rejects_unknown_camera(self):
        view = MultiCameraViewModel()
        with self.assertRaises(ValueError):
            view.mark_state("CAM-999", "FAILED")


if __name__ == "__main__":
    unittest.main()
