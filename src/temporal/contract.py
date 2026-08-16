"""Contrato mínimo de tracking LOCAL y actividad temporal (LOOP-0018R).

Separa el seguimiento temporal/actividad del resto del sistema: consume
eventos canónicos (duck-typing compatible con InferenceEvent) y los convierte
en LocalTrack y TemporalActivity serializables, deterministas y sin
credenciales ni objetos OpenCV.

Garantías:

  - `track_id` es identidad temporal/LOCAL dentro de UNA cámara y una ventana
    de observación. NO es identidad real de una persona, NO es facial, NO es
    re-identificación entre cámaras. Dos tracks de cámaras distintas NUNCA se
    correlacionan como la misma persona.
  - LocalTrack / TemporalActivity no contienen frames, objetos OpenCV,
    credenciales ni estructuras ilimitadas (refs acotadas).
  - Serializable (to_dict/from_dict) y JSON-compatible.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from src.observability.logging_setup import redact_rtsp_url

# Límites sanitizadores (JSON en bytes).
_METADATA_MAX_SERIALIZED_BYTES = 4096

# Estados del ciclo de tracking/actividad.
STARTED = "STARTED"
ACTIVE = "ACTIVE"
ENDED = "ENDED"

VALID_TRACK_STATUSES = (STARTED, ACTIVE, ENDED)

# Tipos de actividad permitidos en LOOP-0018R (genéricos, sin semántica de
# comportamiento: NO se clasifican robo/sospecha/intención/amenaza).
PERSON_PRESENCE = "PERSON_PRESENCE"
OBJECT_PRESENCE = "OBJECT_PRESENCE"


class TemporalError(Exception):
    """Error base de la capa temporal (tracking/actividad)."""
    pass


class TemporalConfigError(TemporalError):
    """Configuración temporal inválida o ausente."""
    pass


class TemporalValidationError(TemporalError):
    """Datos insuficientes o inválidos para construir un track/actividad."""
    pass


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def parse_iso_utc(timestamp: str) -> datetime:
    """Parsea el timestamp canónico UTC (Z) a datetime aware."""
    if not timestamp:
        raise TemporalValidationError("El timestamp es obligatorio")
    value = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TemporalValidationError(
            f"Timestamp inválido: {timestamp!r}"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def duration_ms(started_at: str, ended_at: str) -> int:
    """Duración en ms entre dos timestamps canónicos UTC (redondeada a int)."""
    delta = parse_iso_utc(ended_at) - parse_iso_utc(started_at)
    return int(round(delta.total_seconds() * 1000.0))


@dataclass
class LocalTrack:
    """Track temporal/LOCAL de un objeto en una cámara (contrato mínimo).

    Identidad LOCAL: vale solo para la cámara y la ventana de observación.
    NUNCA implica identidad real de persona ni correlación cross-camera.

    Campos mínimos exigidos por LOOP-0018R: track_id, source_id/camera_id,
    object_type/categoría, started_at, last_seen_at, estado, contador de
    observaciones, confidence agregada/última y referencias acotadas a
    eventos/evidencias.
    """

    track_id: str
    camera_id: str
    object_type: str
    started_at: str
    last_seen_at: str
    status: str = STARTED
    event_count: int = 0
    confidence: Optional[float] = None
    last_bbox: Optional[Tuple[int, int, int, int]] = None
    event_refs: Tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"first": None, "latest": None, "best": None}
    )

    def __post_init__(self) -> None:
        if not self.track_id:
            raise TemporalValidationError("track_id es obligatorio")
        if not self.camera_id:
            raise TemporalValidationError("camera_id es obligatorio")
        if not self.object_type:
            raise TemporalValidationError("object_type es obligatorio")
        if not self.started_at or not self.last_seen_at:
            raise TemporalValidationError("started_at/last_seen_at son obligatorios")
        if self.status not in VALID_TRACK_STATUSES:
            raise TemporalValidationError(f"Estado de track inválido: {self.status!r}")
        if self.event_count < 0:
            raise TemporalValidationError("event_count no puede ser negativo")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise TemporalValidationError("La confianza debe estar entre 0 y 1")
        if self.last_bbox is not None:
            x1, y1, x2, y2 = self.last_bbox
            if x2 < x1 or y2 < y1:
                raise TemporalValidationError("Coordenadas de bbox inválidas")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": redact_rtsp_url(self.track_id),
            "camera_id": redact_rtsp_url(self.camera_id),
            "object_type": redact_rtsp_url(self.object_type),
            "started_at": self.started_at,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
            "event_count": self.event_count,
            "confidence": self.confidence,
            "last_bbox": list(self.last_bbox) if self.last_bbox else None,
            "event_refs": [redact_rtsp_url(r) for r in self.event_refs],
            "evidence_refs": {
                key: (redact_rtsp_url(value) if value else None)
                for key, value in self.evidence_refs.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocalTrack":
        required = (
            "track_id",
            "camera_id",
            "object_type",
            "started_at",
            "last_seen_at",
            "status",
        )
        for key in required:
            if key not in data:
                raise TemporalValidationError(f"Falta campo: {key}")
        bbox = data.get("last_bbox")
        return cls(
            track_id=str(data["track_id"]),
            camera_id=str(data["camera_id"]),
            object_type=str(data["object_type"]),
            started_at=str(data["started_at"]),
            last_seen_at=str(data["last_seen_at"]),
            status=str(data["status"]),
            event_count=int(data.get("event_count", 0)),
            confidence=data.get("confidence"),
            last_bbox=tuple(bbox) if bbox else None,
            event_refs=tuple(str(r) for r in (data.get("event_refs") or [])),
            evidence_refs=dict(data.get("evidence_refs") or {}),
        )


@dataclass
class TemporalActivity:
    """Actividad temporal sobre uno o varios eventos de un mismo track.

    Actividad GENÉRICA (PERSON_PRESENCE/OBJECT_PRESENCE o equivalente). NO se
    clasifica comportamiento (robo, sospecha, intención, amenaza): esas
    capacidades pertenecen a capas posteriores.
    """

    activity_id: str
    track_id: str
    source_id: str
    activity_type: str
    started_at: str
    last_seen_at: str
    status: str = STARTED
    ended_at: Optional[str] = None
    duration_ms: int = 0
    event_count: int = 0
    confidence: Optional[float] = None
    evidence_refs: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"first": None, "latest": None, "best": None}
    )

    def __post_init__(self) -> None:
        if not self.activity_id:
            raise TemporalValidationError("activity_id es obligatorio")
        if not self.track_id:
            raise TemporalValidationError("track_id es obligatorio")
        if not self.source_id:
            raise TemporalValidationError("source_id es obligatorio")
        if not self.activity_type:
            raise TemporalValidationError("activity_type es obligatorio")
        if not self.started_at or not self.last_seen_at:
            raise TemporalValidationError("started_at/last_seen_at son obligatorios")
        if self.status not in VALID_TRACK_STATUSES:
            raise TemporalValidationError(
                f"Estado de actividad inválido: {self.status!r}"
            )
        if self.duration_ms < 0:
            raise TemporalValidationError("duration_ms no puede ser negativo")
        if self.event_count < 0:
            raise TemporalValidationError("event_count no puede ser negativo")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise TemporalValidationError("La confianza debe estar entre 0 y 1")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_id": redact_rtsp_url(self.activity_id),
            "track_id": redact_rtsp_url(self.track_id),
            "source_id": redact_rtsp_url(self.source_id),
            "activity_type": redact_rtsp_url(self.activity_type),
            "started_at": self.started_at,
            "last_seen_at": self.last_seen_at,
            "status": self.status,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "event_count": self.event_count,
            "confidence": self.confidence,
            "evidence_refs": {
                key: (redact_rtsp_url(value) if value else None)
                for key, value in self.evidence_refs.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalActivity":
        required = (
            "activity_id",
            "track_id",
            "source_id",
            "activity_type",
            "started_at",
            "last_seen_at",
            "status",
        )
        for key in required:
            if key not in data:
                raise TemporalValidationError(f"Falta campo: {key}")
        return cls(
            activity_id=str(data["activity_id"]),
            track_id=str(data["track_id"]),
            source_id=str(data["source_id"]),
            activity_type=str(data["activity_type"]),
            started_at=str(data["started_at"]),
            last_seen_at=str(data["last_seen_at"]),
            status=str(data["status"]),
            ended_at=data.get("ended_at"),
            duration_ms=int(data.get("duration_ms", 0)),
            event_count=int(data.get("event_count", 0)),
            confidence=data.get("confidence"),
            evidence_refs=dict(data.get("evidence_refs") or {}),
        )