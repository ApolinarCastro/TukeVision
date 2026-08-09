"""Pruebas del hook on_frame del pipeline (FrameSnapshot)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

from src.app.pipeline import Pipeline

from tests.test_pipeline import CONFIG, _detection


class TestPipelineSnapshotHook(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.output_path = str(Path(self.tmp.name) / "out.mp4")
        self.pipeline = Pipeline(config=CONFIG)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @patch("src.app.pipeline.PersonDetector")
    @patch("src.app.pipeline.PersonTracker")
    @patch("src.app.pipeline.VideoSource")
    def test_on_frame_recibe_snapshots(self, mock_source_cls, mock_tracker_cls, mock_detector_cls) -> None:
        """El hook recibe un FrameSnapshot por fotograma procesado."""
        mock_detector = mock_detector_cls.return_value
        mock_detector.detect.return_value = MagicMock(detections=[_detection()])
        self.pipeline._detector = mock_detector

        tracker_result = MagicMock()
        from src.tracking.person_tracker import TrackedObject
        tracker_result.tracked_objects = [
            TrackedObject(track_id=1, x1=200, y1=300, x2=300, y2=400,
                          confidence=0.9, class_id=0)
        ]
        mock_tracker = mock_tracker_cls.return_value
        mock_tracker.update.return_value = tracker_result
        self.pipeline._tracker = mock_tracker

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        source = mock_source_cls.return_value
        source.source_type = "FILE"
        source.metadata = MagicMock(path="data/input/video.mp4", fps=30.0)
        source.state = "OPEN"
        source.open.return_value = MagicMock(fps=30.0, width=640, height=480)
        source.frames.return_value = [(0, frame), (1, frame), (2, frame)]

        snapshots = []
        self.pipeline.process_source(source, on_frame=snapshots.append)

        self.assertEqual(len(snapshots), 3)
        s0 = snapshots[0]
        self.assertEqual(s0.frame_index, 0)
        self.assertEqual(s0.source_type, "FILE")
        self.assertEqual(s0.source_path, "data/input/video.mp4")
        self.assertEqual(s0.source_state, "OPEN")
        self.assertEqual(len(s0.tracked_objects), 1)
        self.assertEqual(s0.frames_processed, 1)
        self.assertIn(1, s0.stays_seconds)

    @patch("src.app.pipeline.PersonDetector")
    @patch("src.app.pipeline.PersonTracker")
    @patch("src.app.pipeline.VideoSource")
    def test_sin_hook_el_resumen_no_cambia(self, mock_source_cls, mock_tracker_cls, mock_detector_cls) -> None:
        """Sin on_frame el pipeline devuelve un resumen normal."""
        mock_detector = mock_detector_cls.return_value
        mock_detector.detect.return_value = MagicMock(detections=[_detection()])
        self.pipeline._detector = mock_detector

        tracker_result = MagicMock()
        from src.tracking.person_tracker import TrackedObject
        tracker_result.tracked_objects = [
            TrackedObject(track_id=1, x1=200, y1=300, x2=300, y2=400,
                          confidence=0.9, class_id=0)
        ]
        mock_tracker = mock_tracker_cls.return_value
        mock_tracker.update.return_value = tracker_result
        self.pipeline._tracker = mock_tracker

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        source = mock_source_cls.return_value
        source.source_type = "FILE"
        source.metadata = MagicMock(path="data/input/video.mp4", fps=30.0)
        source.state = "OPEN"
        source.open.return_value = MagicMock(fps=30.0, width=640, height=480)
        source.frames.return_value = [(0, frame)]

        summary = self.pipeline.process_source(source)
        self.assertEqual(summary.final_status, "OK")


if __name__ == "__main__":
    unittest.main()
