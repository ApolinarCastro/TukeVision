"""Pruebas unitarias para src.tracking.person_tracker (sin modelo real)."""

import unittest
from unittest.mock import patch

import numpy as np
import supervision as sv

from src.tracking.person_tracker import (
    PersonTracker,
    TrackedObject,
    TrackingResult,
    InvalidDetectionsError,
    TrackingError,
)
from src.detection.person_detector import Detection


def _detection(x1=100, y1=100, x2=200, y2=200, conf=0.9, cls=0):
    return Detection(
        x1=x1, y1=y1, x2=x2, y2=y2,
        confidence=conf, class_id=cls, class_name="person",
    )


def _sv_result(track_ids, boxes, confs, cls):
    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        confidence=np.array(confs, dtype=np.float32),
        class_id=np.array(cls, dtype=int),
        tracker_id=np.array(track_ids, dtype=int),
    )


def _sv_empty():
    return sv.Detections(
        xyxy=np.empty((0, 4), dtype=np.float32),
        confidence=np.empty((0,), dtype=np.float32),
        class_id=np.empty((0,), dtype=int),
        tracker_id=np.empty((0,), dtype=int),
    )


class TestPersonTracker(unittest.TestCase):

    def setUp(self) -> None:
        self.tracker = PersonTracker(
            lost_track_buffer=30,
            frame_rate=30.0,
            track_activation_threshold=0.5,
            minimum_consecutive_frames=1,
        )
        self.update_patcher = patch.object(
            self.tracker._tracker, "update"
        )
        self.mock_update = self.update_patcher.start()
        self.addCleanup(self.update_patcher.stop)

    def test_assigns_identifier(self) -> None:
        """Verifica que asigna un identificador temporal."""
        self.mock_update.return_value = _sv_result(
            [0], [[100, 100, 200, 200]], [0.9], [0]
        )
        result = self.tracker.update([_detection()])
        self.assertEqual(len(result.tracked_objects), 1)
        self.assertEqual(result.tracked_objects[0].track_id, 0)

    def test_maintains_id_between_close_frames(self) -> None:
        """Verifica que mantiene el identificador entre cuadros cercanos."""
        self.mock_update.return_value = _sv_result(
            [7], [[105, 100, 205, 200]], [0.9], [0]
        )
        first = self.tracker.update([_detection()])
        second = self.tracker.update([_detection(x1=105, x2=205)])
        self.assertEqual(first.tracked_objects[0].track_id, 7)
        self.assertEqual(second.tracked_objects[0].track_id, 7)

    def test_discards_unconfirmed_tracks(self) -> None:
        """Verifica que descarta detecciones sin identificador confirmado."""
        self.mock_update.return_value = _sv_result(
            [-1], [[100, 100, 200, 200]], [0.9], [0]
        )
        result = self.tracker.update([_detection()])
        self.assertEqual(len(result.tracked_objects), 0)

    def test_removes_expired_tracks(self) -> None:
        """Verifica que elimina trayectorias vencidas."""
        self.mock_update.side_effect = [
            _sv_result([3], [[100, 100, 200, 200]], [0.9], [0]),
            _sv_empty(),
            _sv_empty(),
        ]
        r1 = self.tracker.update([_detection()])
        r2 = self.tracker.update([])
        r3 = self.tracker.update([])
        self.assertEqual(len(r1.tracked_objects), 1)
        self.assertEqual(len(r2.tracked_objects), 0)
        self.assertEqual(len(r3.tracked_objects), 0)

    def test_empty_input_produces_empty_output(self) -> None:
        """Verifica que entrada vacía produce salida vacía."""
        self.mock_update.return_value = _sv_empty()
        result = self.tracker.update([])
        self.assertEqual(len(result.tracked_objects), 0)
        self.assertIsInstance(result, TrackingResult)

    def test_rejects_none_detections(self) -> None:
        """Verifica error controlado para entrada nula."""
        with self.assertRaises(InvalidDetectionsError):
            self.tracker.update(None)

    def test_rejects_invalid_elements(self) -> None:
        """Verifica error controlado para elementos no válidos."""
        with self.assertRaises(InvalidDetectionsError):
            self.tracker.update([{"not": "a detection"}])

    def test_does_not_modify_input(self) -> None:
        """Verifica que no modifica los datos de entrada."""
        self.mock_update.return_value = _sv_result(
            [0], [[100, 100, 200, 200]], [0.9], [0]
        )
        detections = [_detection()]
        original = [
            (d.x1, d.y1, d.x2, d.y2, d.confidence, d.class_id)
            for d in detections
        ]
        self.tracker.update(detections)
        after = [
            (d.x1, d.y1, d.x2, d.y2, d.confidence, d.class_id)
            for d in detections
        ]
        self.assertEqual(original, after)

    def test_output_is_stable_and_immutable(self) -> None:
        """Verifica que la salida es estable e inmutable."""
        self.mock_update.return_value = _sv_result(
            [0], [[100, 100, 200, 200]], [0.9], [0]
        )
        result = self.tracker.update([_detection()])
        self.assertIsInstance(result.tracked_objects[0], TrackedObject)
        with self.assertRaises(Exception):
            result.tracked_objects[0].track_id = 99

    def test_translates_tracking_error(self) -> None:
        """Verifica traducción de error durante el seguimiento."""
        self.mock_update.side_effect = RuntimeError("tracker exploded")
        with self.assertRaises(TrackingError):
            self.tracker.update([_detection()])


if __name__ == "__main__":
    unittest.main()
