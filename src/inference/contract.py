"""Contrato mínimo de inferencia (LOOP-0018Q).

Separa el motor de inferencia (backend) del resto del sistema: la Observation
Layer y la generación de eventos solo conocen este contrato, nunca los detalles
de YOLO/OpenCV. Permite sustituir el backend sin modificar el pipeline.

    InferenceEngine: contrato mínimo del motor (interfaz pequeña).
    InferenceResult: resultado canónico, serializable y trazable.

Garantías del resultado:

  - No contiene objetos OpenCV ni frames (solo datos serializables).
  - No contiene credenciales (redact_rtsp_url en toda cadena).
  - Es inmutable, JSON-serializable y roundtrip-able (to_dict/from_dict).
  - La metadata es un dict JSON-serializable acotado en bytes.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.observability.logging_setup import redact_rtsp_url

# Límite sanitizador de la metadata del resultado (JSON, en bytes).
_METADATA_MAX_SERIALIZED_BYTES = 4096


def _utc_now_iso() -> str:
    """Timestamp UTC ISO-8601 (formato canónico del sistema)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class InferenceError(Exception):
    """Error base de la capa de inferencia."""
    pass


class InferenceConfigError(InferenceError):
    """Configuración de inferencia inválida o ausente."""
    pass


class InferenceValidationError(InferenceError):
    """Datos insuficientes o inválidos para construir un resultado."""
    pass


@dataclass(frozen=True)
class InferenceDetection:
    """Detección individual, serializable y sin dependencias de OpenCV."""

    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self) -> None:
        if self.class_id < 0:
            raise InferenceValidationError("class_id no puede ser negativo")
        if not self.class_name:
            raise InferenceValidationError("class_name es obligatorio")
        if not (0.0 <= self.confidence <= 1.0):
            raise InferenceValidationError("La confianza debe estar entre 0 y 1")
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise InferenceValidationError("Coordenadas de bbox inválidas")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": redact_rtsp_url(self.class_name),
            "confidence": self.confidence,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InferenceDetection":
        required = ("class_id", "class_name", "confidence", "x1", "y1", "x2", "y2")
        for key in required:
            if key not in data:
                raise InferenceValidationError(f"Falta campo: {key}")
        return cls(
            class_id=int(data["class_id"]),
            class_name=str(data["class_name"]),
            confidence=float(data["confidence"]),
            x1=int(data["x1"]),
            y1=int(data["y1"]),
            x2=int(data["x2"]),
            y2=int(data["y2"]),
        )


@dataclass(frozen=True)
class InferenceResult:
    """Resultado canónico de una ejecución de inferencia.

    Campos mínimos exigidos por el contrato LOOP-0018Q:
    camera/source_id, timestamp, tipo/modelo/productor, detecciones,
    confidence cuando exista, duración/latencia y metadatos acotados.
    """

    inference_id: str
    camera_id: str
    timestamp: str
    engine_name: str
    model_name: str
    producer: str
    detections: Tuple[InferenceDetection, ...]
    latency_ms: float
    confidence: Optional[float] = None
    observation_ref: Optional[str] = None
    evidence_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.inference_id:
            raise InferenceValidationError("inference_id es obligatorio")
        if not self.camera_id:
            raise InferenceValidationError("camera_id es obligatorio")
        if not self.timestamp:
            raise InferenceValidationError("El timestamp es obligatorio")
        if not self.engine_name:
            raise InferenceValidationError("engine_name es obligatorio")
        if not self.model_name:
            raise InferenceValidationError("model_name es obligatorio")
        if not self.producer:
            raise InferenceValidationError("producer es obligatorio")
        if not isinstance(self.detections, (tuple, list)):
            raise InferenceValidationError("detections debe ser una secuencia")
        if self.latency_ms < 0:
            raise InferenceValidationError("latency_ms no puede ser negativo")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InferenceValidationError("La confianza debe estar entre 0 y 1")
        if not isinstance(self.metadata, dict):
            raise InferenceValidationError("metadata debe ser un dict")

    def to_dict(self) -> Dict[str, Any]:
        """Representación JSON-serializable, sin secretos ni objetos OpenCV."""
        metadata = {}
        for key, value in self.metadata.items():
            if isinstance(value, str):
                value = redact_rtsp_url(value)
            metadata[key] = value
        try:
            serialized = json.dumps(metadata, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise InferenceValidationError(
                "La metadata no es JSON-serializable"
            ) from exc
        if len(serialized.encode("utf-8")) > _METADATA_MAX_SERIALIZED_BYTES:
            raise InferenceValidationError(
                "La metadata supera el límite acotado de bytes"
            )
        return {
            "inference_id": self.inference_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "engine_name": redact_rtsp_url(self.engine_name),
            "model_name": redact_rtsp_url(self.model_name),
            "producer": redact_rtsp_url(self.producer),
            "detections": [d.to_dict() for d in self.detections],
            "latency_ms": self.latency_ms,
            "confidence": self.confidence,
            "observation_ref": (
                redact_rtsp_url(self.observation_ref)
                if self.observation_ref is not None
                else None
            ),
            "evidence_ref": (
                redact_rtsp_url(self.evidence_ref)
                if self.evidence_ref is not None
                else None
            ),
            "metadata": metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InferenceResult":
        """Reconstruye un resultado desde su representación canónica."""
        required = (
            "inference_id",
            "camera_id",
            "timestamp",
            "engine_name",
            "model_name",
            "producer",
            "detections",
            "latency_ms",
        )
        for key in required:
            if key not in data:
                raise InferenceValidationError(f"Falta campo: {key}")
        detections = tuple(
            InferenceDetection.from_dict(d) for d in data["detections"]
        )
        return cls(
            inference_id=data["inference_id"],
            camera_id=data["camera_id"],
            timestamp=data["timestamp"],
            engine_name=data["engine_name"],
            model_name=data["model_name"],
            producer=data["producer"],
            detections=detections,
            latency_ms=float(data["latency_ms"]),
            confidence=data.get("confidence"),
            observation_ref=data.get("observation_ref"),
            evidence_ref=data.get("evidence_ref"),
            metadata=dict(data.get("metadata") or {}),
        )


class InferenceEngine(ABC):
    """Contrato mínimo de un motor de inferencia.

    El backend se sustituye sin modificar la Observation Layer ni la generación
    de eventos: ambos dependen únicamente de este contrato y de InferenceResult.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Tipo del motor (ej. 'yolo', 'deterministic')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Modelo/productor del backend (ej. 'yolo11n.pt')."""
        raise NotImplementedError

    @property
    @abstractmethod
    def producer(self) -> str:
        """Productor canónico del resultado (ej. 'yolo:person_detector')."""
        raise NotImplementedError

    @abstractmethod
    def infer(
        self,
        frame: Any,
        camera_id: str,
        observation_ref: Optional[str] = None,
        evidence_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> InferenceResult:
        """Ejecuta inferencia sobre un frame y devuelve el resultado canónico.

        El `frame` puede ser el tipo nativo del backend (nunca se serializa en
        InferenceResult). Errores del backend se propagan como InferenceError o
        excepciones derivadas; la capa selectiva los aísla por cámara.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Libera recursos del backend (opcional)."""

    def __enter__(self) -> "InferenceEngine":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()