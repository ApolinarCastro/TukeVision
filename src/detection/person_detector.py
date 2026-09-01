"""Módulo de detección de personas.

Responsabilidad única: recibir un fotograma y devolver detecciones de personas
en un formato interno estable, independiente del runtime de inferencia subyacente.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import time
import numpy as np

# Importado a nivel de módulo para permitir mocking en tests legacy
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
    """Factory de creación de runtimes de inferencia."""
    rt = (runtime_type or "pytorch").strip().lower()
    path = Path(model_path)

    if rt in ("pytorch", "torch", "yolo"):
        return PyTorchRuntime(model_path=path, device=device)
    elif rt in ("openvino", "ov"):
        return OpenVINORuntime(model_path=path, device=device)
    else:
        raise InferenceError(f"Runtime de inferencia no soportado: {runtime_type!r}")


class PersonDetector:
    """Detector de personas que delega en un InferenceRuntime desacoplado.

    Recibe un fotograma y devuelve detecciones de personas filtradas
    por confianza y clase, sin modificar el fotograma original.
    """

    def __init__(
        self,
        model_path: str,
        class_ids: List[int] = None,
        confidence_threshold: float = 0.35,
        device: str = "cpu",
        image_size: int = 640,
        runtime: Optional[Union[str, InferenceRuntime]] = None,
    ) -> None:
        """Inicializa el detector.

        Args:
            model_path: Ruta al modelo YOLO (.pt o directorio OpenVINO).
            class_ids: IDs de clase a detectar (por defecto [0] = persona).
            confidence_threshold: Umbral mínimo de confianza.
            device: Dispositivo de inferencia ('cpu' o 'cuda').
            image_size: Tamaño de entrada del modelo.
            runtime: Nombre del runtime ('pytorch', 'openvino') o instancia de InferenceRuntime.
        """
        self._model_path = Path(model_path)
        self._class_ids = class_ids or [0]
        self._confidence_threshold = confidence_threshold
        self._device = device
        self._image_size = image_size
        self._class_names = {0: "person"}

        if isinstance(runtime, InferenceRuntime):
            self._runtime = runtime
        elif isinstance(runtime, str):
            self._runtime = create_inference_runtime(runtime, str(self._model_path), device=self._device)
        else:
            self._runtime = PyTorchRuntime(model_path=self._model_path, device=self._device)

    @property
    def _model(self):
        """Propiedad legacy para compatibilidad con tests que inspeccionan _model."""
        if hasattr(self._runtime, "_model"):
            return self._runtime._model
        return None

    @_model.setter
    def _model(self, value):
        if hasattr(self._runtime, "_model"):
            self._runtime._model = value

    def _load_model(self) -> None:
        """Carga el modelo en el runtime correspondiente."""
        self._runtime.load()

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
        """Filtra y convierte resultados legacy."""
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                cls_id = int(box.cls.item())
                if cls_id not in self._class_ids:
                    continue

                conf = float(box.conf.item())
                if conf < self._confidence_threshold:
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
        return detections

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Ejecuta detección sobre un fotograma a través del runtime configurado."""
        self._validate_frame(frame)
        frame_copy = frame.copy()

        return self._runtime.infer(
            frame=frame_copy,
            class_ids=self._class_ids,
            confidence_threshold=self._confidence_threshold,
            image_size=self._image_size,
        )

    def close(self) -> None:
        """Libera recursos del detector y del runtime."""
        if self._runtime is not None:
            self._runtime.close()

    def __enter__(self) -> "PersonDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()