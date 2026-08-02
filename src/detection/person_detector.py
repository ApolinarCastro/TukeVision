"""Módulo de detección de personas.

Responsabilidad única: recibir un fotograma y devolver detecciones de personas
en un formato interno estable, independiente de Ultralytics.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from dataclasses import field as dataclass_field

# Importado a nivel de módulo para permitir mocking en tests
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


@dataclass(frozen=True)
class Detection:
    """Representa una detección de persona."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int
    class_name: str


@dataclass(frozen=True)
class DetectionResult:
    """Resultado de la detección sobre un fotograma."""
    detections: List[Detection]
    inference_seconds: float
    image_width: int
    image_height: int


class PersonDetectorError(Exception):
    """Excepción base para errores del detector."""
    pass


class NullFrameError(PersonDetectorError):
    """Fotograma nulo recibido."""
    pass


class EmptyFrameError(PersonDetectorError):
    """Fotograma vacío (sin dimensiones)."""
    pass


class InvalidFrameError(PersonDetectorError):
    """Formato de fotograma inválido."""
    pass


class ModelNotFoundError(PersonDetectorError):
    """Modelo no disponible."""
    pass


class InferenceError(PersonDetectorError):
    """Fallo durante la inferencia."""
    pass


class PersonDetector:
    """Detector de personas usando YOLO Nano.

    Recibe un fotograma y devuelve detecciones de personas filtradas
    por confianza y clase, sin modificar el fotograma original.
    """

    def __init__(
        self,
        model_path: str,
        class_ids: List[int] = None,
        confidence_threshold: float = 0.35,
        device: str = "cpu",
        image_size: int = 640
    ) -> None:
        """Inicializa el detector.

        Args:
            model_path: Ruta al modelo YOLO (.pt).
            class_ids: IDs de clase a detectar (por defecto [0] = persona).
            confidence_threshold: Umbral mínimo de confianza.
            device: Dispositivo de inferencia ('cpu' o 'cuda').
            image_size: Tamaño de entrada del modelo.
        """
        self._model_path = Path(model_path)
        self._class_ids = class_ids or [0]
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._image_size = image_size
        self._model = None
        self._class_names = {0: "person"}  # COCO class 0 = person

    def _load_model(self) -> None:
        """Carga el modelo YOLO de forma perezosa."""
        if self._model is not None:
            return

        if not self._model_path.exists():
            raise ModelNotFoundError(f"Modelo no encontrado: {self._model_path}")

        if YOLO is None:
            raise InferenceError("Ultralytics no está instalado")

        try:
            self._model = YOLO(str(self._model_path))
            self._model.to(self._device)
        except Exception as e:
            raise InferenceError(f"Error cargando modelo: {e}")

    def _validate_frame(self, frame: np.ndarray) -> None:
        """Valida que el fotograma sea correcto."""
        if frame is None:
            raise NullFrameError("Fotograma nulo")

        if frame.size == 0:
            raise EmptyFrameError("Fotograma vacío (0 bytes)")

        if len(frame.shape) != 3 or frame.shape[2] != 3:
            raise InvalidFrameError(
                f"Fotograma debe ser BGR 3 canales, recibido shape={frame.shape}"
            )

    def _filter_detections(self, results) -> List[Detection]:
        """Filtra y convierte resultados de Ultralytics a formato interno."""
        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # Obtener clase
                cls_id = int(box.cls.item())
                if cls_id not in self._class_ids:
                    continue

                # Obtener confianza
                conf = float(box.conf.item())
                if conf < self._confidence_threshold:
                    continue

                # Obtener coordenadas (xyxy)
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                detections.append(Detection(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                    class_id=cls_id,
                    class_name=self._class_names.get(cls_id, str(cls_id))
                ))

        return detections

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Ejecuta detección sobre un fotograma.

        Args:
            frame: Fotograma BGR como array NumPy.

        Returns:
            DetectionResult con detecciones filtradas.

        Raises:
            PersonDetectorError: Si hay errores de validación o inferencia.
        """
        import time

        self._validate_frame(frame)

        # Copia para no modificar el original
        frame_copy = frame.copy()

        self._load_model()

        h, w = frame_copy.shape[:2]

        start = time.perf_counter()
        try:
            results = self._model.predict(
                source=frame_copy,
                imgsz=self._image_size,
                classes=self._class_ids,
                conf=self._confidence_threshold,
                device=self._device,
                verbose=False
            )
        except Exception as e:
            raise InferenceError(f"Error en inferencia: {e}")
        inference_time = time.perf_counter() - start

        detections = self._filter_detections(results)

        return DetectionResult(
            detections=detections,
            inference_seconds=inference_time,
            image_width=w,
            image_height=h
        )

    def close(self) -> None:
        """Libera recursos (modelo)."""
        self._model = None

    def __enter__(self) -> "PersonDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()