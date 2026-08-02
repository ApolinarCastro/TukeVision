"""Pruebas unitarias para src.events (sin dependencias externas)."""

import unittest

from src.events.engine import EventEngine, InvalidEventError
from src.events.models import Event, PERMANENCIA_PROLONGADA
from src.observations.engine import ObservationEngine
from src.observations.models import (
    PERSON_ENTERED_ZONE,
    PERSON_REMAINED_IN_ZONE,
    PERSON_EXITED_ZONE,
)


class TestEventEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.obs_engine = ObservationEngine()
        self.event_engine = EventEngine(max_stay_seconds=30.0)
        self.store = "STORE-001"
        self.camera = "CAM-001"
        self.zone = "ZONE-001"

    def _obs(self, obs_type, ts, frame, track=1, value=1.0):
        return self.obs_engine.create_observation(
            timestamp=ts,
            store_id=self.store,
            camera_id=self.camera,
            zone_id=self.zone,
            track_id=track,
            observation_type=obs_type,
            value=value,
            source_frame=frame,
        )

    def test_entered_observation_starts_window(self) -> None:
        """Verifica que la entrada inicia el seguimiento sin evento."""
        obs = self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        result = self.event_engine.process(obs)
        self.assertIsNone(result)

    def test_no_event_under_threshold(self) -> None:
        """Verifica que no hay evento bajo el umbral."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        result = self.event_engine.process(
            self._obs(PERSON_EXITED_ZONE, "2026-08-02T12:00:20Z", 600)
        )
        self.assertIsNone(result)

    def test_event_on_prolonged_stay(self) -> None:
        """Verifica que se crea PERMANENCIA_PROLONGADA al superar 30s."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        result = self.event_engine.process(
            self._obs(PERSON_EXITED_ZONE, "2026-08-02T12:01:00Z", 1800)
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Event)
        self.assertEqual(result.event_type, PERMANENCIA_PROLONGADA)
        self.assertEqual(result.track_id, 1)
        self.assertGreaterEqual(result.duration_seconds, 60.0)

    def test_event_fires_during_stay_on_remained(self) -> None:
        """Verifica que el evento se crea durante la permanencia."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        result = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, PERMANENCIA_PROLONGADA)

    def test_event_preserves_observation_ids(self) -> None:
        """Verifica que conserva los identificadores de las observaciones."""
        entry = self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        stay = self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900)
        self.event_engine.process(entry)
        result = self.event_engine.process(stay)
        self.assertIn(entry.observation_id, result.observation_ids)
        self.assertIn(stay.observation_id, result.observation_ids)

    def test_event_is_immutable(self) -> None:
        """Verifica que el evento es inmutable."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        result = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900)
        )
        with self.assertRaises(Exception):
            result.event_type = "OTHER"

    def test_event_emitted_only_once(self) -> None:
        """Verifica que el evento se emite una sola vez por trayectoria."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        first = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900)
        )
        second = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:02:00Z", 1800)
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_event_for_another_track(self) -> None:
        """Verifica que cada trayectoria se evalúa por separado."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0, track=1)
        )
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0, track=2)
        )
        result = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900, track=2)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.track_id, 2)

    def test_rejects_none_observation(self) -> None:
        """Verifica rechazo de observación nula."""
        with self.assertRaises(InvalidEventError):
            self.event_engine.process(None)

    def test_reset(self) -> None:
        """Verifica que reset reinicia el estado."""
        self.event_engine.process(
            self._obs(PERSON_ENTERED_ZONE, "2026-08-02T12:00:00Z", 0)
        )
        self.event_engine.reset()
        result = self.event_engine.process(
            self._obs(PERSON_REMAINED_IN_ZONE, "2026-08-02T12:01:00Z", 900)
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
