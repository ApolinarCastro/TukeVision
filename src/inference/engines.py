"""Backends de inferencia (LOOP-0018Q).

  - DeterministicInferenceEngine: backend determinista/fake SIN dependencia
    pesada. Genera detecciones deterministas a partir de marcadores de señal
    (brightness) en el frame o de un generador inyectable. Permite certificar
    contrato, política selectiva y pipeline de eventos sin YOLO.
  - YoloInferenceEngine: backend real que REUTILIZA PersonDetector del BASE por
    composición (ultralytics ya presente, modelo yolo11n.pt verificado). No
    instala ni actualiza Torch/Ultralytics/OpenCV/CUDA.

Ambos implementan el contrato InferenceEngine. La selección del backend se
gobierna por configuración (config/default.json -> inference.backend).
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from src.inference.contract import (
    InferenceDetection,
    InferenceEngine,
    InferenceError,
    InferenceConfigError,
    InferenceResult,
    InferenceValidationError,
)
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.inference")

# Tipos de señal para el backend determinista.
_SIGNAL_BRIGHTNESS = "brightness"


def _default_clock() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class DeterministicInferenceEngine(InferenceEngine):
    """Backend determinista/fake para certificación sintética.

    Sin YOLO/OpenCV: interpreta un frame como array NumPy (BGR o gris) y genera
    una detección determinista cuando la señal supera un umbral configurable.
    Opcionalmente acepta un `generator` inyectable (camera_id, frame_index) ->
    detecciones, para escenarios controlados sin frames reales.

    Latencia simulada configurable (default 0.0) para pruebas deterministas.
    """

    def __init__(
        self,
        signal: str = _SIGNAL_BRIGHTNESS,
        brightness_threshold: int = 200,
        confidence: float = 0.9,
        simulated_latency_ms: float = 0.0,
        generator: Optional[
            Callable[[str, int], List[Tuple[int, str, float, int, int, int, int]]]
        ] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._signal = signal
        self._brightness_threshold = int(brightness_threshold)
        self._confidence = confidence
        self._simulated_latency_ms = float(simulated_latency_ms)
        self._generator = generator
        self._clock = clock or _default_clock
        self._seq = 0
        self._closed = False

    @property
    def engine_name(self) -> str:
        return "deterministic"

    @property
    def model_name(self) -> str:
        return "deterministic:signal"

    @property
    def producer(self) -> str:
        return "deterministic:selective"

    def _next_id(self, camera_id: str) -> str:
        self._seq += 1
        return f"INF-{camera_id}-{self._seq:06d}"

    @staticmethod
    def _detect_brightness(frame: Any, threshold: int) -> List[InferenceDetection]:
        """Detección determinista por brillo: bbox del área que supera el umbral."""
        if frame is None:
            return []
        arr = np.asarray(frame)
        if arr.ndim == 0 or arr.size == 0:
            return []
        if arr.ndim == 3:
            # BGR -> luminancia aproximada (máximo de canales es suficiente y
            # determinista; evita dependencias de color).
            lum = arr.max(axis=2)
        else:
            lum = arr
        mask = lum >= threshold
        idx = np.argwhere(mask)
        if idx.size == 0:
            return []
        y1, x1 = int(idx.min(axis=0)[0]), int(idx.min(axis=0)[1])
        y2, x2 = int(idx.max(axis=0)[0]), int(idx.max(axis=0)[1])
        # Detección determinista: objeto genérico sobre el área brillante.
        return [InferenceDetection(0, "object", 0.9, x1, y1, x2, y2)]

    def infer(
        self,
        frame: Any,
        camera_id: str,
        observation_ref: Optional[str] = None,
        evidence_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InferenceResult:
        if self._closed:
            raise InferenceError("DeterministicInferenceEngine cerrado")
        camera_id = (camera_id or "").strip()
        if not camera_id:
            raise InferenceValidationError("camera_id es obligatorio")

        start = time.perf_counter()
        if self._generator is not None:
            raw = self._generator(camera_id, int((metadata or {}).get("frame_index", 0)))
            detections = []
            for item in raw or []:
                detections.append(InferenceDetection(*item))
        else:
            detections = self._detect_brightness(frame, self._brightness_threshold)
        latency = self._simulated_latency_ms
        if latency <= 0:
            latency = (time.perf_counter() - start) * 1000.0

        confidence = None
        if detections:
            confidence = max(d.confidence for d in detections)

        result = InferenceResult(
            inference_id=self._next_id(camera_id),
            camera_id=camera_id,
            timestamp=self._clock(),
            engine_name=self.engine_name,
            model_name=self.model_name,
            producer=self.producer,
            detections=tuple(detections),
            latency_ms=round(latency, 3),
            confidence=confidence,
            observation_ref=observation_ref,
            evidence_ref=evidence_ref,
            metadata=dict(metadata or {}),
        )
        logger.debug(
            "INFERENCE_DETERMINISTIC camera_id=%s detections=%d latency_ms=%.3f",
            camera_id,
            len(detections),
            result.latency_ms,
        )
        return result

    def close(self) -> None:
        self._closed = True


class YoloInferenceEngine(InferenceEngine):
    """Backend real de inferencia que REUTILIZA PersonDetector del BASE.

    Composición (no reescritura): delega en src.detection.person_detector y
    convierte DetectionResult -> InferenceResult canónico. Carga perezosa del
    modelo. Errores del backend se traducen a InferenceError para aislamiento.
    """

    def __init__(
        self,
        model_path: str = "models/yolo11n.pt",
        class_ids: Optional[List[int]] = None,
        confidence_threshold: float = 0.35,
        device: str = "cpu",
        image_size: int = 640,
        runtime: str = "pytorch",
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._model_path = model_path
        self._class_ids = class_ids or [0]
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._image_size = image_size
        self._runtime_name = (runtime or "pytorch").strip().lower()
        self._clock = clock or _default_clock
        self._detector = None
        self._seq = 0
        self._closed = False

    @property
    def engine_name(self) -> str:
        return f"yolo_{self._runtime_name}"

    @property
    def model_name(self) -> str:
        return self._model_path

    @property
    def producer(self) -> str:
        return f"yolo:{self._runtime_name}_detector"

    def _load_detector(self):
        if self._detector is not None:
            return self._detector
        from src.detection.person_detector import PersonDetector

        self._detector = PersonDetector(
            model_path=self._model_path,
            class_ids=self._class_ids,
            confidence_threshold=self._confidence_threshold,
            device=self._device,
            image_size=self._image_size,
            runtime=self._runtime_name,
        )
        return self._detector

    def _next_id(self, camera_id: str) -> str:
        self._seq += 1
        return f"INF-{camera_id}-{self._seq:06d}"

    def infer(
        self,
        frame: Any,
        camera_id: str,
        observation_ref: Optional[str] = None,
        evidence_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InferenceResult:
        if self._closed:
            raise InferenceError("YoloInferenceEngine cerrado")
        camera_id = (camera_id or "").strip()
        if not camera_id:
            raise InferenceValidationError("camera_id es obligatorio")

        detector = self._load_detector()
        try:
            detection_result = detector.detect(frame)
        except Exception as exc:
            raise InferenceError(f"Fallo del backend YOLO ({self._runtime_name}): {exc}") from exc

        detections = tuple(
            InferenceDetection(
                class_id=d.class_id,
                class_name=redact_rtsp_url(d.class_name),
                confidence=d.confidence,
                x1=d.x1,
                y1=d.y1,
                x2=d.x2,
                y2=d.y2,
            )
            for d in detection_result.detections
        )
        confidence = None
        if detections:
            confidence = max(d.confidence for d in detections)

        result = InferenceResult(
            inference_id=self._next_id(camera_id),
            camera_id=camera_id,
            timestamp=self._clock(),
            engine_name=self.engine_name,
            model_name=self.model_name,
            producer=self.producer,
            detections=detections,
            latency_ms=round(detection_result.inference_seconds * 1000.0, 3),
            confidence=confidence,
            observation_ref=observation_ref,
            evidence_ref=evidence_ref,
            metadata=dict(metadata or {}),
        )
        logger.debug(
            "INFERENCE_YOLO camera_id=%s detections=%d latency_ms=%.3f",
            camera_id,
            len(detections),
            result.latency_ms,
        )
        return result

    def close(self) -> None:
        if self._detector is not None:
            try:
                self._detector.close()
            except Exception as exc:  # close nunca debe romper el shutdown
                logger.warning("INFERENCE_YOLO_CLOSE_WARN err=%s", exc)
            self._detector = None
        self._closed = True


def build_engine(config: Optional[Dict[str, Any]]) -> InferenceEngine:
    """Construye el backend desde config `inference`.

    Reglas de fail-safe (G17/G18): backend ausente/inválido produce error
    explícito (nunca silencio peligroso). Backend `yolo` o `openvino` reutiliza
    PersonDetector. Soporta selección explícita de runtime ('pytorch' vs 'openvino').
    """
    if not isinstance(config, dict):
        raise InferenceConfigError("Config de inferencia inválida: no es dict")

    backend = str(config.get("backend", "yolo")).strip().lower()
    runtime = str(config.get("runtime", "pytorch")).strip().lower()

    if backend == "deterministic":
        return DeterministicInferenceEngine(
            confidence=float(config.get("confidence_threshold", 0.9)),
            simulated_latency_ms=float(config.get("simulated_latency_ms", 0.0)),
        )
    if backend in ("yolo", "openvino", "pytorch"):
        # Si backend es openvino explícito, runtime se deduce como openvino
        if backend == "openvino":
            runtime = "openvino"
        return YoloInferenceEngine(
            model_path=str(config.get("model", "models/yolo11n.pt")),
            class_ids=config.get("class_ids") or [0],
            confidence_threshold=float(config.get("confidence_threshold", 0.35)),
            device=str(config.get("device", "cpu")),
            image_size=int(config.get("image_size", 640)),
            runtime=runtime,
        )
    raise InferenceConfigError(f"Backend de inferencia desconocido: {backend!r}")