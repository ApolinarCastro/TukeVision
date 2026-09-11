import unittest
from types import SimpleNamespace

import numpy as np

from src.ui.controller import UiController
from src.ui.grid_layout import grid_layout
from src.ui.multicamera import MultiCameraViewModel

CAMERA_IDS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")


class TestMultiCameraView(unittest.TestCase):
    def test_controller_orchestrates_four_snapshots_without_capture(self):
        controller = UiController(config={}, camera_ids=CAMERA_IDS)
        for index, camera_id in enumerate(CAMERA_IDS):
            controller.ingest_camera_snapshot(camera_id, SimpleNamespace(
                frame_index=index + 1, frame=np.full((2, 2, 3), index),
                source_state="OPEN", fps=2.0,
            ))
        panels = controller.poll_multicamera()
        self.assertEqual(tuple(panels), CAMERA_IDS)
        self.assertEqual(int(panels["CAM-003"].frame[0, 0, 0]), 2)

    def test_layout_is_computed_from_the_config_driven_camera_set(self):
        view = MultiCameraViewModel(CAMERA_IDS)
        self.assertEqual(
            view.layout,
            tuple(tuple(row) for row in grid_layout(CAMERA_IDS)),
        )
        self.assertEqual(tuple(view.snapshot()), CAMERA_IDS)

    def test_layout_supports_sixteen_cameras(self):
        ids = tuple(f"CAM-{index:03d}" for index in range(1, 17))
        view = MultiCameraViewModel(ids)
        self.assertEqual(len(tuple(view.snapshot())), 16)
        self.assertEqual(len(view.layout), 4)
        self.assertTrue(all(len(row) == 4 for row in view.layout))

    def test_latest_wins_and_camera_isolation(self):
        view = MultiCameraViewModel(CAMERA_IDS)
        frame = np.zeros((2, 2, 3), dtype=np.uint8)
        view.update("CAM-001", SimpleNamespace(frame_index=2, frame=frame, source_state="OPEN", fps=3))
        view.update("CAM-001", SimpleNamespace(frame_index=1, frame=None, source_state="FAILED", fps=0))
        view.mark_state("CAM-003", "FAILED")
        self.assertEqual(view.panel("CAM-001").frame_index, 2)
        self.assertEqual(view.panel("CAM-001").source_state, "OPEN")
        self.assertEqual(view.panel("CAM-003").source_state, "FAILED")
        self.assertEqual(view.panel("CAM-002").source_state, "OFFLINE")

    def test_rejects_unknown_camera(self):
        view = MultiCameraViewModel(CAMERA_IDS)
        with self.assertRaises(ValueError):
            view.mark_state("CAM-999", "FAILED")

    def test_sparse_analytics_survive_a_later_video_only_frame(self):
        view = MultiCameraViewModel(CAMERA_IDS)
        analytics_frame = np.full((2, 2, 3), 7, dtype=np.uint8)
        live_frame = np.zeros((2, 2, 3), dtype=np.uint8)
        view.update("CAM-001", SimpleNamespace(
            frame_index=10, frame=analytics_frame, source_state="OPEN", fps=3,
            detections=2, track_id="TRK-1", temporal="PERSON_PRESENCE ACTIVE 1.2s",
            behavior="PROLONGED_DWELL", risk="REVIEW 65", evidence="CAM-001/EVD/frame.jpg",
            bboxes=((1, 2, 10, 20, 0.9, "person"),), track_bbox=(1, 2, 10, 20),
            event_type="PERSON_DETECTED", track_status="ACTIVE", resolution="640x360",
        ))
        view.update("CAM-001", SimpleNamespace(
            frame_index=11, frame=live_frame, source_state="OPEN", fps=3,
            detections=None, track_id=None, temporal=None, behavior=None,
            risk=None, evidence=None,
            bboxes=None, track_bbox=None, event_type=None, track_status=None,
            resolution="640x360",
        ))
        panel = view.panel("CAM-001")
        self.assertEqual(panel.frame_index, 11)
        self.assertEqual(panel.detections, 2)
        self.assertEqual(panel.track_id, "TRK-1")
        self.assertEqual(panel.temporal, "PERSON_PRESENCE ACTIVE 1.2s")
        self.assertEqual(panel.behavior, "PROLONGED_DWELL")
        self.assertEqual(panel.evidence, "CAM-001/EVD/frame.jpg")
        self.assertEqual(panel.bboxes[0][:4], (1, 2, 10, 20))
        self.assertEqual(panel.track_bbox, (1, 2, 10, 20))
        self.assertEqual(panel.event_type, "PERSON_DETECTED")
        self.assertEqual(panel.analytics_frame_index, 10)
        self.assertIs(panel.analytics_frame, analytics_frame)
        self.assertIs(panel.frame, live_frame)


if __name__ == "__main__":
    unittest.main()