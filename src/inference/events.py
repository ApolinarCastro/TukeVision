"""Evento canónico y detección de eventos (LOOP-0018Q).

Un InferenceResult que satisface una regla/threshold configurable se convierte
en un InferenceEvent canónico, serializable, trazable y sin credenciales.

    InferenceEvent: schema canónico del evento.
    EventDetector: regla mínima config-driven (threshold por tipo de evento).
    BoundedEventQueue: cola FIFO acotada de eventos con overflow explícito.

No se implementa un motor complejo de reglas: solo la regla mínima necesaria
para demostrar el pipeline (OBJECT_DETECTED / PERSON_DETECTED según el backend).
Los thresholds son CONFIG-DRIVEN (nunca hardcodeados en lógica de negocio).
"""

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.inference.contract import InferenceResult
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.inference")

# Tipos de evento canónicos mínimos.
OBJECT_DETECTED = "OBJECT_DETECTED"
PERSON_DETECTED = "PERSON_DETECTED"

VALID_EVENT_TYPES = (OBJECT_DETECTED, PERSON_DETECTED)

# Límites sanitizadores de la metadata del evento.
_METADATA_MAX_SERIALIZED_BYTES = 4096
_MAX_EVENT_BBOXES = 16

DROP_OLDEST = "drop_oldest"
DROP_NEWEST = "drop_newest"
_VALID_OVERFLOW = (DROP_OLDEST, DROP_NEWEST)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class InferenceEventError(Exception):
    """Error base de eventos de inferencia."""
    pass


class InvalidInferenceEventError(InferenceEventError):
    """Datos insuficientes o inválidos para crear un evento."""
    pass


@dataclass(frozen=True)
class InferenceEvent:
    """Evento canónico generado a partir de un InferenceResult.

    Contiene: event_id, camera_id, timestamp UTC, event_type, confidence,
    producer/model, observation_ref (origen), inference_ref (trazabilidad al
    resultado) y evidence_reference opcional. Serializable, sin credenciales.
    """

    event_id: str
    camera_id: str
    timestamp: str
    event_type: str
    confidence: Optional[float]
    producer: str
    model: str
    observation_ref: Optional[str]
    inference_ref: str
    evidence_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id:
            raise InvalidInferenceEventError("event_id es obligatorio")
        if not self.camera_id:
            raise InvalidInferenceEventError("camera_id es obligatorio")
        if not self.timestamp:
            raise InvalidInferenceEventError("El timestamp es obligatorio")
        if self.event_type not in VALID_EVENT_TYPES:
            raise InvalidInferenceEventError(
                f"Tipo de evento inválido: {self.event_type}"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InvalidInferenceEventError(
                "La confianza debe estar entre 0 y 1"
            )
        if not self.producer:
            raise InvalidInferenceEventError("producer es obligatorio")
        if not self.model:
            raise InvalidInferenceEventError("model es obligatorio")
        if not self.inference_ref:
            raise InvalidInferenceEventError("inference_ref es obligatorio")
        if not isinstance(self.metadata, dict):
            raise InvalidInferenceEventError("metadata debe ser un dict")

    def to_dict(self) -> Dict[str, Any]:
        metadata = {}
        for key, value in self.metadata.items():
            if isinstance(value, str):
                value = redact_rtsp_url(value)
            metadata[key] = value
        try:
            serialized = json.dumps(metadata, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise InvalidInferenceEventError(
                "La metadata no es JSON-serializable"
            ) from exc
        if len(serialized.encode("utf-8")) > _METADATA_MAX_SERIALIZED_BYTES:
            raise InvalidInferenceEventError(
                "La metadata supera el límite acotado de bytes"
            )
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "confidence": self.confidence,
            "producer": redact_rtsp_url(self.producer),
            "model": redact_rtsp_url(self.model),
            "observation_ref": (
                redact_rtsp_url(self.observation_ref)
                if self.observation_ref is not None
                else None
            ),
            "inference_ref": redact_rtsp_url(self.inference_ref),
            "evidence_ref": (
                redact_rtsp_url(self.evidence_ref)
                if self.evidence_ref is not None
                else None
            ),
            "metadata": metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InferenceEvent":
        required = (
            "event_id",
            "camera_id",
            "timestamp",
            "event_type",
            "confidence",
            "producer",
            "model",
            "inference_ref",
        )
        for key in required:
            if key not in data:
                raise InvalidInferenceEventError(f"Falta campo: {key}")
        return cls(
            event_id=data["event_id"],
            camera_id=data["camera_id"],
            timestamp=data["timestamp"],
            event_type=data["event_type"],
            confidence=data.get("confidence"),
            producer=data["producer"],
            model=data["model"],
            observation_ref=data.get("observation_ref"),
            inference_ref=data["inference_ref"],
            evidence_ref=data.get("evidence_ref"),
            metadata=dict(data.get("metadata") or {}),
        )


class EventDetector:
    """Convierte InferenceResult -> InferenceEvent según reglas config-driven.

    Regla mínima: cada evento se define por `type` y `min_confidence`.
    Un resultado produce un evento si al menos una detección supera el umbral
    del tipo. Si `class_name` se define, solo aplica a esa clase.

    Config inválida -> fail-safe conocido (sin eventos) y warning; nunca un
    error silencioso peligroso en runtime.
    """

    def __init__(
        self,
        rules: Optional[List[Dict[str, Any]]] = None,
        clock: Optional[callable] = None,
    ) -> None:
        self._rules: List[Dict[str, Any]] = []
        if isinstance(rules, list):
            for rule in rules:
                normalized = self._normalize_rule(rule)
                if normalized is not None:
                    self._rules.append(normalized)
        self._clock = clock or _utc_now_iso
        self._seq = 0

    @staticmethod
    def _normalize_rule(rule: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(rule, dict):
            return None
        event_type = rule.get("type")
        if event_type not in VALID_EVENT_TYPES:
            return None
        try:
            min_conf = float(rule.get("min_confidence", 0.0))
        except (TypeError, ValueError):
            return None
        if not (0.0 <= min_conf <= 1.0):
            return None
        class_name = rule.get("class_name")
        if class_name is not None:
            class_name = str(class_name).strip() or None
        return {
            "type": event_type,
            "min_confidence": min_conf,
            "class_name": class_name,
        }

    @property
    def rules(self) -> List[Dict[str, Any]]:
        return list(self._rules)

    def _next_id(self, camera_id: str) -> str:
        self._seq += 1
        return f"EVT-{camera_id}-{self._seq:06d}"

    def detect(self, result: InferenceResult) -> Optional[InferenceEvent]:
        """Genera el evento si el resultado satisface alguna regla."""
        if result is None:
            raise InvalidInferenceEventError("El resultado es obligatorio")
        if not self._rules:
            logger.warning("EVENT_DETECTOR_NO_RULES resultado sin evento")
            return None

        best_confidence: Optional[float] = None
        best_rule: Optional[Dict[str, Any]] = None
        best_detection = None
        best_specific = False
        for detection in result.detections:
            for rule in self._rules:
                if rule["class_name"] and rule["class_name"] != detection.class_name:
                    continue
                if detection.confidence < rule["min_confidence"]:
                    continue
                specific = bool(rule["class_name"])
                if (
                    best_confidence is None
                    or detection.confidence > best_confidence
                    or (
                        detection.confidence == best_confidence
                        and specific
                        and not best_specific
                    )
                ):
                    best_confidence = detection.confidence
                    best_rule = rule
                    best_detection = detection
                    best_specific = specific

        if best_rule is None:
            return None

        # La metadata del evento propaga (acotada y sin credenciales) la
        # metadata del resultado, que se sanitiza en la serialización.
        event_metadata: Dict[str, Any] = dict(result.metadata or {})
        ranked_detections = sorted(
            result.detections,
            key=lambda item: item.confidence,
            reverse=True,
        )
        event_metadata.update(
            {
                "detections": len(result.detections),
                "engine": result.engine_name,
                "bboxes": [
                    [
                        item.x1, item.y1, item.x2, item.y2,
                        round(float(item.confidence), 6), item.class_id,
                    ]
                    for item in ranked_detections[:_MAX_EVENT_BBOXES]
                ],
                "primary_bbox": [
                    best_detection.x1, best_detection.y1,
                    best_detection.x2, best_detection.y2,
                ],
            }
        )
        return InferenceEvent(
            event_id=self._next_id(result.camera_id),
            camera_id=result.camera_id,
            timestamp=result.timestamp,
            event_type=best_rule["type"],
            confidence=best_confidence,
            producer=result.producer,
            model=result.model_name,
            observation_ref=result.observation_ref,
            inference_ref=result.inference_id,
            evidence_ref=result.evidence_ref,
            metadata=event_metadata,
        )


class BoundedEventQueue:
    """Cola FIFO acotada de eventos con política de overflow explícita.

    - drop_oldest (default): si la cola está llena se descarta el más antiguo.
    - drop_newest: si la cola está llena NO se encola el nuevo.
    Memoria siempre <= maxlen. Conteo determinista de descartados.
    """

    def __init__(self, maxlen: int = 16, overflow: str = DROP_OLDEST) -> None:
        if maxlen < 1:
            raise InferenceEventError("maxlen debe ser >= 1")
        if overflow not in _VALID_OVERFLOW:
            raise InferenceEventError(f"overflow inválido: {overflow!r}")
        self._maxlen = maxlen
        self._overflow = overflow
        self._queue: Deque[InferenceEvent] = deque(maxlen=maxlen)
        self._dropped = 0

    @property
    def maxlen(self) -> int:
        return self._maxlen

    @property
    def overflow(self) -> str:
        return self._overflow

    @property
    def dropped(self) -> int:
        return self._dropped

    def push(self, event: InferenceEvent) -> None:
        if not isinstance(event, InferenceEvent):
            raise InferenceEventError("Solo se aceptan InferenceEvent")
        if self._overflow == DROP_NEWEST and len(self._queue) >= self._maxlen:
            self._dropped += 1
            return
        if self._overflow == DROP_OLDEST and len(self._queue) >= self._maxlen:
            self._dropped += 1
        self._queue.append(event)

    def drain(self, limit: Optional[int] = None) -> List[InferenceEvent]:
        result: List[InferenceEvent] = []
        count = 0
        while self._queue and (limit is None or count < limit):
            result.append(self._queue.popleft())
            count += 1
        return result

    def peek(self) -> Optional[InferenceEvent]:
        if not self._queue:
            return None
        return self._queue[0]

    def __len__(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()
