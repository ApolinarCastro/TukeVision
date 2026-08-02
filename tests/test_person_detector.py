"""Pruebas unitarias para src.detection.person_detector (sin inferencia real)."""

import unittest
from unittest.mock import Mock, patch
import numpy as np
from pathlib import Path

from src.detection.person_detector import (
    PersonDetector,
    Detection,
    DetectionResult,
    NullFrameError,
    EmptyFrameError,
    InvalidFrameError,
    ModelNotFoundError,
    InferenceError,
)


class TestPersonDetector(unittest.TestCase):
    """Pruebas para PersonDetector usando mocks."""

    def setUp(self) -> None:
        """Configuración común."""
        self.model_path = "models/yolo11n.pt"
        self.detector = PersonDetector(
            model_path=self.model_path,
            class_ids=[0],
            confidence_threshold=0.35,
            device="cpu",
            image_size=640
        )

    def _create_mock_frame(self, width: int = 640, height: int = 480) -> np.ndarray:
        """Crea un fotograma válido sintético."""
        return np.zeros((height, width, 3), dtype=np.uint8)

    def _create_mock_ultralytics_result(self, boxes_data: list) -> Mock:
        """Crea un mock de resultado de Ultralytics."""
        result = Mock()
        boxes = Mock()
        boxes.__iter__ = Mock(return_value=iter(boxes_data))
        result.boxes = boxes
        return result

    def _create_mock_box(self, cls_id: int, conf: float, xyxy: list) -> Mock:
        """Crea un mock de caja de detección."""
        box = Mock()
        box.cls.item.return_value = cls_id
        box.conf.item.return_value = conf
        # Simular tensor con método tolist()
        xyxy_tensor = Mock()
        xyxy_tensor.tolist.return_value = xyxy
        box.xyxy = [xyxy_tensor]
        return box

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_filters_only_person_class(self, mock_exists, mock_yolo) -> None:
        """Verifica que filtra únicamente la clase persona (ID 0)."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        # Mock box para persona (clase 0) y otra clase (ej. coche = 2)
        person_box = self._create_mock_box(cls_id=0, conf=0.8, xyxy=[100, 100, 200, 200])
        car_box = self._create_mock_box(cls_id=2, conf=0.9, xyxy=[300, 300, 400, 400])

        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([person_box, car_box])
        ]

        frame = self._create_mock_frame()
        result = self.detector.detect(frame)

        self.assertEqual(len(result.detections), 1)
        self.assertEqual(result.detections[0].class_id, 0)
        self.assertEqual(result.detections[0].class_name, "person")

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_discards_below_threshold(self, mock_exists, mock_yolo) -> None:
        """Verifica que descarta detecciones bajo el umbral de confianza."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        high_conf = self._create_mock_box(cls_id=0, conf=0.8, xyxy=[100, 100, 200, 200])
        low_conf = self._create_mock_box(cls_id=0, conf=0.2, xyxy=[300, 300, 400, 400])

        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([high_conf, low_conf])
        ]

        frame = self._create_mock_frame()
        result = self.detector.detect(frame)

        self.assertEqual(len(result.detections), 1)
        self.assertGreaterEqual(result.detections[0].confidence, 0.35)

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_converts_coordinates_correctly(self, mock_exists, mock_yolo) -> None:
        """Verifica conversión correcta de coordenadas."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        xyxy = [50.5, 60.7, 150.2, 180.9]
        box = self._create_mock_box(cls_id=0, conf=0.9, xyxy=xyxy)

        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([box])
        ]

        frame = self._create_mock_frame()
        result = self.detector.detect(frame)

        det = result.detections[0]
        self.assertEqual(det.x1, 50)
        self.assertEqual(det.y1, 60)
        self.assertEqual(det.x2, 150)
        self.assertEqual(det.y2, 180)

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_returns_immutable_structure(self, mock_exists, mock_yolo) -> None:
        """Verifica que el resultado es inmutable (dataclass frozen)."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        box = self._create_mock_box(cls_id=0, conf=0.9, xyxy=[100, 100, 200, 200])
        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([box])
        ]

        frame = self._create_mock_frame()
        result = self.detector.detect(frame)

        # Detection es frozen
        with self.assertRaises(Exception):
            result.detections[0].confidence = 0.0

        # DetectionResult es frozen
        with self.assertRaises(Exception):
            result.inference_seconds = 0.0

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_does_not_modify_original_frame(self, mock_exists, mock_yolo) -> None:
        """Verifica que no modifica el fotograma original."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        box = self._create_mock_box(cls_id=0, conf=0.9, xyxy=[100, 100, 200, 200])
        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([box])
        ]

        frame = self._create_mock_frame()
        frame_original = frame.copy()

        self.detector.detect(frame)

        np.testing.assert_array_equal(frame, frame_original)

    def test_rejects_null_frame(self) -> None:
        """Verifica rechazo de fotograma nulo."""
        with self.assertRaises(NullFrameError):
            self.detector.detect(None)

    def test_rejects_empty_frame(self) -> None:
        """Verifica rechazo de fotograma vacío."""
        empty_frame = np.array([], dtype=np.uint8)
        with self.assertRaises(EmptyFrameError):
            self.detector.detect(empty_frame)

    def test_rejects_invalid_format(self) -> None:
        """Verifica rechazo de formato inválido (no 3 canales)."""
        # 1 canal (gris)
        gray = np.zeros((100, 100), dtype=np.uint8)
        with self.assertRaises(InvalidFrameError):
            self.detector.detect(gray)

        # 4 canales (RGBA)
        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        with self.assertRaises(InvalidFrameError):
            self.detector.detect(rgba)

    @patch("pathlib.Path.exists", return_value=False)
    def test_translates_model_load_error(self, mock_exists) -> None:
        """Verifica traducción de error de carga de modelo."""
        bad_detector = PersonDetector(model_path="no_existe.pt")

        with self.assertRaises(ModelNotFoundError):
            bad_detector.detect(self._create_mock_frame())

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_translates_inference_error(self, mock_exists, mock_yolo) -> None:
        """Verifica traducción de error durante inferencia."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model
        mock_model.predict.side_effect = RuntimeError("CUDA out of memory")

        frame = self._create_mock_frame()
        with self.assertRaises(InferenceError):
            self.detector.detect(frame)

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_returns_empty_list_when_no_persons(self, mock_exists, mock_yolo) -> None:
        """Verifica lista vacía cuando no hay personas."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        # Solo detecciones de otras clases
        car_box = self._create_mock_box(cls_id=2, conf=0.9, xyxy=[100, 100, 200, 200])
        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([car_box])
        ]

        frame = self._create_mock_frame()
        result = self.detector.detect(frame)

        self.assertEqual(len(result.detections), 0)
        self.assertIsInstance(result.detections, list)

    @patch("src.detection.person_detector.YOLO")
    @patch("pathlib.Path.exists", return_value=True)
    def test_result_contains_metadata(self, mock_exists, mock_yolo) -> None:
        """Verifica que DetectionResult incluye metadatos esperados."""
        mock_model = Mock()
        mock_yolo.return_value = mock_model

        box = self._create_mock_box(cls_id=0, conf=0.9, xyxy=[100, 100, 200, 200])
        mock_model.predict.return_value = [
            self._create_mock_ultralytics_result([box])
        ]

        frame = self._create_mock_frame(640, 480)
        result = self.detector.detect(frame)

        self.assertEqual(result.image_width, 640)
        self.assertEqual(result.image_height, 480)
        self.assertGreater(result.inference_seconds, 0)


if __name__ == "__main__":
    unittest.main()