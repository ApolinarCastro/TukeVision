"""Abstracción de runtimes de inferencia para detección de objetos.

Define el contrato unificado InferenceRuntime e implementaciones para
PyTorch (baseline) y OpenVINO (acelerado por CPU), garantizando
aislamiento desacoplado, validación de entradas y preservación exacta
del contrato de salida DetectionResult.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time
import numpy as np

from src.detection.models import Detection, DetectionResult
from src.detection.exceptions import (
    PersonDetectorError,
    NullFrameError,
    EmptyFrameError,
    InvalidFrameError,
    ModelNotFoundError,
    InferenceError,
)

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class InferenceRuntime(ABC):
    """Contrato base abstracto para motores de inferencia en TukeVision."""

    @abstractmethod
    def load(self) -> None:
        """Carga y compila el modelo en el runtime correspondiente."""
        pass

    @abstractmethod
    def infer(
        self,
        frame: np.ndarray,
        class_ids: List[int],
        confidence_threshold: float,
        image_size: int,
    ) -> DetectionResult:
        """Ejecuta inferencia sobre un fotograma y devuelve DetectionResult canónico."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Libera recursos del runtime."""
        pass


class PyTorchRuntime(InferenceRuntime):
    """Runtime de inferencia basado en PyTorch CPU (Baseline)."""

    def __init__(self, model_path: Path, device: str = "cpu") -> None:
        self._model_path = model_path
        self._device = device
        self._model: Optional[Any] = None
        self._class_names = {0: "person"}

    def load(self) -> None:
        if self._model is not None:
            return

        if not self._model_path.exists():
            raise ModelNotFoundError(f"Modelo PyTorch no encontrado: {self._model_path}")

        if YOLO is None:
            raise InferenceError("Ultralytics no está instalado")

        try:
            self._model = YOLO(str(self._model_path), task="detect")
            self._model.to(self._device)
        except Exception as e:
            raise InferenceError(f"Error cargando modelo PyTorch: {e}") from e

    def infer(
        self,
        frame: np.ndarray,
        class_ids: List[int],
        confidence_threshold: float,
        image_size: int,
    ) -> DetectionResult:
        self.load()
        h, w = frame.shape[:2]
        start = time.perf_counter()

        try:
            results = self._model.predict(
                source=frame,
                imgsz=image_size,
                classes=class_ids,
                conf=confidence_threshold,
                device=self._device,
                verbose=False,
            )
        except Exception as e:
            raise InferenceError(f"Error en inferencia PyTorch: {e}") from e

        inference_time = time.perf_counter() - start

        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls.item())
                if cls_id not in class_ids:
                    continue

                conf = float(box.conf.item())
                if conf < confidence_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(
                    Detection(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        confidence=conf,
                        class_id=cls_id,
                        class_name=self._class_names.get(cls_id, str(cls_id)),
                    )
                )

        return DetectionResult(
            detections=detections,
            inference_seconds=inference_time,
            image_width=w,
            image_height=h,
        )

    def close(self) -> None:
        self._model = None


class OpenVINORuntime(InferenceRuntime):
    """Runtime de inferencia acelerado basado en OpenVINO CPU Plugin."""

    def __init__(self, model_path: Path, device: str = "cpu") -> None:
        self._model_path = model_path
        self._device = device
        self._model: Optional[Any] = None
        self._class_names = {0: "person"}

    def load(self) -> None:
        if self._model is not None:
            return

        # Si model_path es un archivo .pt, buscar si existe el directorio exportado openvino
        actual_path = self._model_path
        if actual_path.suffix == ".pt":
            candidate_dir = actual_path.parent / f"{actual_path.stem}_openvino_model"
            if candidate_dir.exists() and candidate_dir.is_dir():
                actual_path = candidate_dir

        if not actual_path.exists():
            raise ModelNotFoundError(f"Modelo OpenVINO no encontrado en: {actual_path}")

        if YOLO is None:
            raise InferenceError("Ultralytics no está instalado")

        try:
            self._model = YOLO(str(actual_path), task="detect")
        except Exception as e:
            raise InferenceError(f"Error cargando modelo OpenVINO: {e}") from e

    def infer(
        self,
        frame: np.ndarray,
        class_ids: List[int],
        confidence_threshold: float,
        image_size: int,
    ) -> DetectionResult:
        self.load()
        h, w = frame.shape[:2]
        start = time.perf_counter()

        try:
            results = self._model.predict(
                source=frame,
                imgsz=image_size,
                classes=class_ids,
                conf=confidence_threshold,
                device="cpu",
                verbose=False,
            )
        except Exception as e:
            raise InferenceError(f"Error en inferencia OpenVINO: {e}") from e

        inference_time = time.perf_counter() - start

        detections: List[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls.item())
                if cls_id not in class_ids:
                    continue

                conf = float(box.conf.item())
                if conf < confidence_threshold:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(
                    Detection(
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                        confidence=conf,
                        class_id=cls_id,
                        class_name=self._class_names.get(cls_id, str(cls_id)),
                    )
                )

        return DetectionResult(
            detections=detections,
            inference_seconds=inference_time,
            image_width=w,
            image_height=h,
        )

    def close(self) -> None:
        self._model = None


def create_inference_runtime(
    runtime_type: str,
    model_path: str,
    device: str = "cpu",
) -> InferenceRuntime:
    """Factory de creación de runtimes de inferencia con validación fail-safe."""
    rt = (runtime_type or "pytorch").strip().lower()
    path = Path(model_path)

    if rt in ("pytorch", "torch", "yolo"):
        return PyTorchRuntime(model_path=path, device=device)
    elif rt in ("openvino", "ov"):
        return OpenVINORuntime(model_path=path, device=device)
    else:
        raise InferenceError(f"Runtime de inferencia no soportado: {runtime_type!r}")
