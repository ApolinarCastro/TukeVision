"""Seguimiento temporal de personas.

Responsabilidad única: asignar identificadores temporales a detecciones
de personas mediante ByteTrack, sin exponer los objetos internos de la
librería `trackers`.
"""

import numpy as np
import supervision as sv
from dataclasses import dataclass
from typing import List

try:
    from trackers import ByteTrackTracker
except ImportError:
    ByteTrackTracker = None


@dataclass(frozen=True)
class TrackedObject:
    """Objeto detectado con identificador temporal."""
    track_id: int
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int


@dataclass(frozen=True)
class TrackingResult:
    """Resultado del seguimiento sobre un fotograma."""
    tracked_objects: List[TrackedObject]


class PersonTrackerError(Exception):
    """Excepción base para errores del rastreador."""
    pass


class InvalidDetectionsError(PersonTrackerError):
    """Detecciones inválidas recibidas."""
    pass


class TrackerNotAvailableError(PersonTrackerError):
    """La librería trackers no está disponible."""
    pass


class TrackingError(PersonTrackerError):
    """Fallo durante el seguimiento."""
    pass


class PersonTracker:
    """Asigna identificadores temporales mediante ByteTrack."""

    def __init__(
        self,
        lost_track_buffer: int = 30,
        frame_rate: float = 30.0,
        track_activation_threshold: float = 0.5,
        minimum_consecutive_frames: int = 2,
        minimum_iou_threshold: float = 0.1,
        high_conf_det_threshold: float = 0.6,
    ) -> None:
        if ByteTrackTracker is None:
            raise TrackerNotAvailableError(
                "La librería trackers no está instalada"
            )
        self._tracker = ByteTrackTracker(
            lost_track_buffer=lost_track_buffer,
            frame_rate=frame_rate,
            track_activation_threshold=track_activation_threshold,
            minimum_consecutive_frames=minimum_consecutive_frames,
            minimum_iou_threshold=minimum_iou_threshold,
            high_conf_det_threshold=high_conf_det_threshold,
        )

    def _validate_detections(self, detections) -> None:
        if detections is None:
            raise InvalidDetectionsError("Detecciones nulas")
        for det in detections:
            for attr in ("x1", "y1", "x2", "y2", "confidence", "class_id"):
                if not hasattr(det, attr):
                    raise InvalidDetectionsError(
                        f"Elemento inválido en detecciones: {type(det).__name__}"
                    )

    def _build_sv_detections(self, detections) -> sv.Detections:
        if not detections:
            return sv.Detections(
                xyxy=np.empty((0, 4), dtype=np.float32),
                confidence=np.empty((0,), dtype=np.float32),
                class_id=np.empty((0,), dtype=int),
            )
        xyxy = np.array(
            [[d.x1, d.y1, d.x2, d.y2] for d in detections],
            dtype=np.float32,
        )
        confidence = np.array([d.confidence for d in detections], dtype=np.float32)
        class_id = np.array([d.class_id for d in detections], dtype=int)
        return sv.Detections(
            xyxy=xyxy,
            confidence=confidence,
            class_id=class_id,
        )

    def _to_tracked_objects(self, result: sv.Detections) -> List[TrackedObject]:
        tracked = []
        if len(result) == 0 or result.tracker_id is None:
            return tracked
        for i in range(len(result)):
            track_id = int(result.tracker_id[i])
            if track_id < 0:
                continue
            x1, y1, x2, y2 = map(int, result.xyxy[i])
            confidence = (
                float(result.confidence[i])
                if result.confidence is not None else 0.0
            )
            class_id = (
                int(result.class_id[i])
                if result.class_id is not None else -1
            )
            tracked.append(TrackedObject(
                track_id=track_id,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                confidence=confidence,
                class_id=class_id,
            ))
        return tracked

    def update(self, detections) -> TrackingResult:
        """Actualiza el seguimiento con las detecciones de un fotograma.

        Args:
            detections: Detecciones internas del detector de personas.

        Returns:
            TrackingResult con los objetos confirmados y su identificador.

        Raises:
            PersonTrackerError: Si las detecciones son inválidas o falla el
                seguimiento.
        """
        self._validate_detections(detections)
        sv_detections = self._build_sv_detections(detections)
        try:
            result = self._tracker.update(sv_detections)
        except Exception as e:
            raise TrackingError(f"Error en seguimiento: {e}")
        return TrackingResult(tracked_objects=self._to_tracked_objects(result))

    def reset(self) -> None:
        """Reinicia el estado del rastreador (nuevo video o escena)."""
        self._tracker.reset()

    def close(self) -> None:
        """Libera recursos del rastreador."""
        self.reset()

    def __enter__(self) -> "PersonTracker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
