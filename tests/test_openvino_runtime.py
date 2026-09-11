"""Pruebas unitarias para la integración de OpenVINORuntime y abstracción de runtime."""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import numpy as np

from src.detection.person_detector import (
    PersonDetector,
    Detection,
    DetectionResult,
    InferenceRuntime,
    PyTorchRuntime,
    OpenVINORuntime,
    create_inference_runtime,
    ModelNotFoundError,
    InferenceError,
)
from src.inference.engines import build_engine, YoloInferenceEngine


class TestOpenVINOIntegration(unittest.TestCase):
    """Pruebas del runtime OpenVINO y la selección dinámica."""

    def test_factory_creates_pytorch_runtime(self):
        rt = create_inference_runtime("pytorch", "models/yolo11n.pt")
        self.assertIsInstance(rt, PyTorchRuntime)

    def test_factory_creates_openvino_runtime(self):
        rt = create_inference_runtime("openvino", "models/yolo11n.pt")
        self.assertIsInstance(rt, OpenVINORuntime)

    def test_factory_rejects_unknown_runtime(self):
        with self.assertRaises(InferenceError):
            create_inference_runtime("unknown_tensorrt", "models/yolo11n.pt")

    def test_detector_accepts_openvino_runtime_param(self):
        detector = PersonDetector(
            model_path="models/yolo11n.pt",
            runtime="openvino",
        )
        self.assertIsInstance(detector._runtime, OpenVINORuntime)
        detector.close()

    def test_detector_accepts_runtime_instance(self):
        custom_rt = PyTorchRuntime(Path("models/yolo11n.pt"))
        detector = PersonDetector(
            model_path="models/yolo11n.pt",
            runtime=custom_rt,
        )
        self.assertIs(detector._runtime, custom_rt)
        detector.close()

    def test_build_engine_with_openvino_runtime(self):
        config = {
            "backend": "yolo",
            "runtime": "openvino",
            "model": "models/yolo11n.pt",
            "confidence_threshold": 0.4,
        }
        engine = build_engine(config)
        self.assertIsInstance(engine, YoloInferenceEngine)
        self.assertEqual(engine._runtime_name, "openvino")
        self.assertEqual(engine.engine_name, "yolo_openvino")
        engine.close()

    def test_build_engine_with_openvino_backend_directly(self):
        config = {
            "backend": "openvino",
            "model": "models/yolo11n.pt",
        }
        engine = build_engine(config)
        self.assertIsInstance(engine, YoloInferenceEngine)
        self.assertEqual(engine._runtime_name, "openvino")
        engine.close()

    def test_build_engine_rollback_to_pytorch(self):
        config = {
            "backend": "yolo",
            "runtime": "pytorch",
            "model": "models/yolo11n.pt",
        }
        engine = build_engine(config)
        self.assertIsInstance(engine, YoloInferenceEngine)
        self.assertEqual(engine._runtime_name, "pytorch")
        self.assertEqual(engine.engine_name, "yolo_pytorch")
        engine.close()

    def test_openvino_missing_model_raises_model_not_found(self):
        rt = OpenVINORuntime(Path("models/non_existent_model_12345.pt"))
        with self.assertRaises(ModelNotFoundError):
            rt.load()

    def test_openvino_real_inference_on_sample_frame(self):
        # Inferencia real con el modelo OpenVINO exportado
        detector = PersonDetector(
            model_path="models/yolo11n.pt",
            runtime="openvino",
            confidence_threshold=0.35,
        )
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.detect(dummy_frame)
        self.assertIsInstance(result, DetectionResult)
        self.assertEqual(result.image_width, 640)
        self.assertEqual(result.image_height, 480)
        self.assertGreater(result.inference_seconds, 0.0)
        self.assertIsInstance(result.detections, list)
        detector.close()


if __name__ == "__main__":
    unittest.main()
