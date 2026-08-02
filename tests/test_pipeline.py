"""Pruebas unitarias para src.app.pipeline (sin modelo ni video reales)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

from src.app.pipeline import (
    Pipeline,
    PipelineSummary,
    PipelineConfigError,
    load_config,
)


CONFIG = {
    "video": {"max_width": 640, "process_every_n_frames": 1},
    "detection": {
        "model": "yolo11n.pt",
        "class_ids": [0],
        "confidence_threshold": 0.35,
        "device": "cpu",
        "image_size": 640,
    },
    "zone": {
        "id": "ZONE-001",
        "name": "Zona piloto",
        "polygon": [[100, 100], [540, 100], [540, 420], [100, 420]],
    },
    "business": {
        "store_id": "STORE-001",
        "camera_id": "CAM-001",
        "max_stay_seconds": 30.0,
        "remain_interval_frames": 30,
    },
    "alerts": {"risk_threshold": 60},
}


def _detection(x1=200, y1=300, x2=300, y2=400, conf=0.9, cls=0):
    from src.detection.person_detector import Detection
    return Detection(
        x1=x1, y1=y1, x2=x2, y2=y2,
        confidence=conf, class_id=cls, class_name="person",
    )


class TestPipeline(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.video_path = str(Path(self.tmp.name) / "input.mp4")
        self.output_path = str(Path(self.tmp.name) / "out.mp4")
        self.pipeline = Pipeline(config=CONFIG)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_load_config_missing_file(self) -> None:
        """Verifica error controlado si la configuración no existe."""
        with self.assertRaises(PipelineConfigError):
            load_config(str(Path(self.tmp.name) / "nope.json"))

    def test_requires_zone(self) -> None:
        """Verifica error si la zona no está definida."""
        bad_config = dict(CONFIG)
        bad_config["zone"] = {}
        with self.assertRaises(PipelineConfigError):
            Pipeline(config=bad_config)

    @patch("src.app.pipeline.PersonDetector")
    @patch("src.app.pipeline.PersonTracker")
    @patch("src.app.pipeline.VideoSource")
    def test_process_returns_summary(self, mock_source_cls, mock_tracker_cls, mock_detector_cls) -> None:
        """Verifica que el pipeline devuelve un resumen."""
        mock_detector = mock_detector_cls.return_value
        mock_detector.detect.return_value = MagicMock(
            detections=[_detection()]
        )
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
        source.__enter__.return_value = source
        source.open.return_value = MagicMock(fps=30.0, width=640, height=480)
        source.frames.return_value = [(0, frame), (1, frame), (2, frame)]
        source.metadata = MagicMock(fps=30.0)

        summary = self.pipeline.process(self.video_path, self.output_path)
        self.assertIsInstance(summary, PipelineSummary)
        self.assertEqual(summary.frames_processed, 3)
        self.assertEqual(summary.persons_detected, 3)
        self.assertEqual(summary.tracks_created, 1)
        self.assertEqual(summary.final_status, "OK")

    def test_stay_seconds_computation(self) -> None:
        """Verifica el cálculo de tiempo de permanencia."""
        self.pipeline._entry_frame[5] = 0
        self.assertAlmostEqual(
            self.pipeline._stay_seconds(5, 30, 30.0), 1.0
        )
        # Primera vez: registra entrada y devuelve 0
        self.assertAlmostEqual(self.pipeline._stay_seconds(9, 10, 30.0), 0.0)
        self.assertIn(9, self.pipeline._entry_frame)


if __name__ == "__main__":
    unittest.main()
