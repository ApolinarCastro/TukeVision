"""Prueba funcional acotada con el backend real YOLO (LOOP-0018Q).

SEPARADA de los tests deterministas. Reutiliza el PersonDetector del BASE y el
modelo yolo11n.pt ya presente en el entorno (no descarga ni instala nada) sobre
una imagen local autorizada de prueba (data/temp/zidane.jpg, con personas).

Se ejecuta SOLO cuando el modelo y la imagen existen localmente (entorno real).
Si no están disponibles, la prueba se marca SKIP (no es un fallo de la
arquitectura): el contrato + política selectiva + pipeline de eventos quedan
certificados por los tests deterministas.
"""

import json
import unittest
from pathlib import Path

import numpy as np

from src.inference.engines import YoloInferenceEngine
from src.inference.events import (
    EventDetector,
    OBJECT_DETECTED,
    PERSON_DETECTED,
)
from src.inference.selective import SelectiveInferencePipeline
from src.observations.activity import PROFILE_BALANCED

MODEL_PATH = Path("models/yolo11n.pt")
IMAGE_PATH = Path("data/temp/zidane.jpg")

FIXED_TS = "2026-08-16T17:00:00.000000Z"

_REAL_AVAILABLE = MODEL_PATH.exists() and IMAGE_PATH.exists()


@unittest.skipUnless(
    _REAL_AVAILABLE,
    "Backend real no disponible (falta modelo o imagen de prueba local)",
)
class TestRealYoloBackend(unittest.TestCase):
    """Prueba funcional acotada con el backend real (exigida por la directiva)."""

    @classmethod
    def setUpClass(cls) -> None:
        import cv2

        cls._frame = cv2.imread(str(IMAGE_PATH))
        cls._engine = YoloInferenceEngine(
            model_path=str(MODEL_PATH),
            class_ids=[0],
            confidence_threshold=0.35,
            device="cpu",
            image_size=640,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._engine.close()

    def test_real_inference_produces_result(self) -> None:
        result = self._engine.infer(self._frame, "CAM-07")
        self.assertEqual(result.camera_id, "CAM-07")
        self.assertTrue(result.timestamp.endswith("Z"))
        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertEqual(result.engine_name, "yolo")
        # La imagen de prueba contiene personas: al menos una detección real.
        self.assertGreaterEqual(len(result.detections), 1)

    def test_real_inference_result_serializable(self) -> None:
        result = self._engine.infer(self._frame, "CAM-07")
        data = result.to_dict()
        json.dumps(data)
        self.assertIn("detections", data)
        self.assertIn("latency_ms", data)

    def test_real_result_to_event(self) -> None:
        detector = EventDetector(
            rules=[
                {"type": OBJECT_DETECTED, "min_confidence": 0.35},
                {
                    "type": PERSON_DETECTED,
                    "min_confidence": 0.35,
                    "class_name": "person",
                },
            ]
        )
        result = self._engine.infer(self._frame, "CAM-07")
        event = detector.detect(result)
        self.assertIsNotNone(event)
        self.assertIn(event.event_type, (PERSON_DETECTED, OBJECT_DETECTED))

    def test_real_selective_pipeline_synthetic_frames(self) -> None:
        # 4 cámaras lógicas con frames sintéticos (negros), política BALANCED.
        pipeline = SelectiveInferencePipeline(
            engine=self._engine,
            event_detector=EventDetector(
                rules=[
                    {"type": OBJECT_DETECTED, "min_confidence": 0.35},
                    {
                        "type": PERSON_DETECTED,
                        "min_confidence": 0.35,
                        "class_name": "person",
                    },
                ]
            ),
            clock=lambda: FIXED_TS,
        )
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            pipeline.register_camera(cam)
        black = np.zeros((480, 640, 3), dtype=np.uint8)
        for cam in pipeline.list_cameras():
            for i in range(8):
                pipeline.feed(cam, i, fps=15.0, frame=black)
        metrics = pipeline.metrics()
        for cam in pipeline.list_cameras():
            self.assertEqual(metrics[cam]["profile"], PROFILE_BALANCED)
            self.assertEqual(
                metrics[cam]["considered"],
                metrics[cam]["processed"] + metrics[cam]["skipped_by_policy"],
            )
            self.assertEqual(metrics[cam]["inference_errors"], 0)
        pipeline.close()


if __name__ == "__main__":
    unittest.main()