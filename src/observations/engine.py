"""Motor de observaciones.

Responsabilidad única: transformar transiciones de zona y seguimiento en
observaciones oficiales, objetivas e inmutables.
"""

from typing import Optional

from src.observations.models import (
    Observation,
    PERSON_ENTERED_ZONE,
    PERSON_REMAINED_IN_ZONE,
    PERSON_EXITED_ZONE,
    VALID_OBSERVATION_TYPES,
)

TRANSITION_TO_TYPE = {
    "ENTERED": PERSON_ENTERED_ZONE,
    "REMAINED": PERSON_REMAINED_IN_ZONE,
    "EXITED": PERSON_EXITED_ZONE,
}


class ObservationError(Exception):
    """Excepción base para errores del motor de observaciones."""
    pass


class InvalidObservationError(ObservationError):
    """Datos insuficientes o inválidos para crear una observación."""
    pass


class ObservationEngine:
    """Genera observaciones objetivas desde transiciones de zona."""

    def __init__(self, remain_interval_frames: int = 30) -> None:
        self._counter = 0
        self._last_remain_frame = {}
        self._remain_interval_frames = remain_interval_frames

    def _next_id(self) -> str:
        self._counter += 1
        return f"OBS-{self._counter:05d}"

    def create_observation(
        self,
        timestamp: str,
        store_id: str,
        camera_id: str,
        zone_id: str,
        track_id: int,
        observation_type: str,
        value: float = 1.0,
        confidence: float = 1.0,
        source_frame: int = 0,
    ) -> Observation:
        """Crea una observación validando los campos obligatorios."""
        if not timestamp:
            raise InvalidObservationError("La fecha y hora son obligatorias")
        if not store_id:
            raise InvalidObservationError("El identificador de tienda es obligatorio")
        if not camera_id:
            raise InvalidObservationError("El identificador de cámara es obligatorio")
        if not zone_id:
            raise InvalidObservationError("La zona es obligatoria")
        if track_id is None:
            raise InvalidObservationError("El identificador temporal es obligatorio")
        if observation_type not in VALID_OBSERVATION_TYPES:
            raise InvalidObservationError(
                f"Tipo de observación inválido: {observation_type}"
            )
        if not (0.0 <= confidence <= 1.0):
            raise InvalidObservationError(
                "La confianza debe estar entre 0 y 1"
            )
        if source_frame < 0:
            raise InvalidObservationError(
                "El fotograma de origen no puede ser negativo"
            )

        return Observation(
            observation_id=self._next_id(),
            timestamp=timestamp,
            store_id=store_id,
            camera_id=camera_id,
            zone_id=zone_id,
            track_id=track_id,
            observation_type=observation_type,
            value=value,
            confidence=confidence,
            source_frame=source_frame,
        )

    def process_transition(
        self,
        transition: str,
        track_id: int,
        store_id: str,
        camera_id: str,
        zone_id: str,
        source_frame: int,
        timestamp: str,
        confidence: float = 1.0,
        value: float = 1.0,
    ) -> Optional[Observation]:
        """Convierte una transición de zona en una observación.

        Returns:
            Observation si la transición es observable, o None para la
            transición 'OUTSIDE'.
        """
        if transition not in TRANSITION_TO_TYPE:
            return None

        observation_type = TRANSITION_TO_TYPE[transition]

        if observation_type == PERSON_REMAINED_IN_ZONE:
            last = self._last_remain_frame.get(track_id, -1)
            if last >= 0 and (
                source_frame - last < self._remain_interval_frames
            ):
                return None
            self._last_remain_frame[track_id] = source_frame

        return self.create_observation(
            timestamp=timestamp,
            store_id=store_id,
            camera_id=camera_id,
            zone_id=zone_id,
            track_id=track_id,
            observation_type=observation_type,
            value=value,
            confidence=confidence,
            source_frame=source_frame,
        )

    def reset(self) -> None:
        """Reinicia el estado interno del motor."""
        self._counter = 0
        self._last_remain_frame = {}
