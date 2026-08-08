"""Motor de eventos.

Responsabilidad única: relacionar observaciones y crear el evento
PERMANENCIA_PROLONGADA cuando una persona permanece en la zona más
tiempo del permitido. No genera alertas ni confirma incidentes.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.observations.models import (
    Observation,
    PERSON_ENTERED_ZONE,
    PERSON_REMAINED_IN_ZONE,
    PERSON_EXITED_ZONE,
)
from src.events.models import Event, PERMANENCIA_PROLONGADA


class EventError(Exception):
    """Excepción base para errores del motor de eventos."""
    pass


class InvalidEventError(EventError):
    """Datos insuficientes o inválidos para crear un evento."""
    pass


def _parse_timestamp(value: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError as e:
        raise InvalidEventError(f"Fecha y hora inválida: {value}")


class EventEngine:
    """Crea eventos de permanencia prolongada desde observaciones."""

    def __init__(self, max_stay_seconds: float = 30.0) -> None:
        self._max_stay_seconds = max_stay_seconds
        self._entry_observations: Dict[int, Observation] = {}
        self._emitted: Dict[int, bool] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"EVT-{self._counter:05d}"

    def process(self, observation: Observation) -> Optional[Event]:
        """Procesa una observación y devuelve un evento si corresponde."""
        if observation is None:
            raise InvalidEventError("La observación es obligatoria")

        key = observation.track_id

        if observation.observation_type == PERSON_ENTERED_ZONE:
            self._entry_observations[key] = observation
            self._emitted[key] = False
            return None

        if observation.observation_type == PERSON_REMAINED_IN_ZONE:
            # Solo validamos si ya superó el umbral, pero no emitimos hasta la salida
            return self._check_threshold(observation)

        if observation.observation_type == PERSON_EXITED_ZONE:
            return self._evaluate(observation, exited=True)

        return None

    def _check_threshold(self, observation: Observation) -> Optional[Event]:
        """Verifica si se superó el umbral en una observación de permanencia, sin emitir."""
        key = observation.track_id
        entry = self._entry_observations.get(key)
        if entry is None:
            return None
        if self._emitted.get(key, False):
            return None

        duration = (
            _parse_timestamp(observation.timestamp) - _parse_timestamp(entry.timestamp)
        ).total_seconds()

        if duration <= self._max_stay_seconds:
            return None
        # Superó el umbral: marcamos como pendiente de emitir en la salida
        self._emitted[key] = "pending"
        return None

    def _evaluate(self, latest: Observation, exited: bool = False) -> Optional[Event]:
        key = latest.track_id
        entry = self._entry_observations.get(key)
        if entry is None:
            return None

        # Si ya se emitió definitivamente, no volver a emitir
        if self._emitted.get(key) is True:
            return None

        duration = (
            _parse_timestamp(latest.timestamp) - _parse_timestamp(entry.timestamp)
        ).total_seconds()

        if duration <= self._max_stay_seconds:
            if exited:
                self._entry_observations.pop(key, None)
                self._emitted.pop(key, None)
            return None

        # Emitimos el evento con la duración total de la estancia
        self._emitted[key] = True
        self._entry_observations.pop(key, None)

        return Event(
            event_id=self._next_id(),
            event_type=PERMANENCIA_PROLONGADA,
            timestamp=latest.timestamp,
            store_id=entry.store_id,
            camera_id=entry.camera_id,
            zone_id=entry.zone_id,
            track_id=key,
            observation_ids=(entry.observation_id, latest.observation_id),
            duration_seconds=duration,
        )

    def finalize(self, current_timestamp: str) -> List[Event]:
        """Finaliza eventos pendientes para trayectorias que siguen en la zona al finalizar el video."""
        events = []
        for key, entry in list(self._entry_observations.items()):
            if self._emitted.get(key) is True:
                continue
            duration = (
                _parse_timestamp(current_timestamp) - _parse_timestamp(entry.timestamp)
            ).total_seconds()
            if duration > self._max_stay_seconds:
                self._emitted[key] = True
                self._entry_observations.pop(key, None)
                events.append(Event(
                    event_id=self._next_id(),
                    event_type=PERMANENCIA_PROLONGADA,
                    timestamp=current_timestamp,
                    store_id=entry.store_id,
                    camera_id=entry.camera_id,
                    zone_id=entry.zone_id,
                    track_id=key,
                    observation_ids=(entry.observation_id,),
                    duration_seconds=duration,
                ))
        return events

    def reset(self) -> None:
        """Reinicia el estado interno del motor."""
        self._entry_observations.clear()
        self._emitted.clear()
        self._counter = 0
