"""Pruebas unitarias para src.observations (sin dependencias externas)."""

import unittest

from src.observations.engine import ObservationEngine, InvalidObservationError
from src.observations.models import (
    Observation,
    PERSON_ENTERED_ZONE,
    PERSON_REMAINED_IN_ZONE,
    PERSON_EXITED_ZONE,
)


class TestObservationEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = ObservationEngine()
        self.base = dict(
            timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001",
            camera_id="CAM-001",
            zone_id="ZONE-001",
            track_id=1,
            source_frame=10,
        )

    def test_creates_observation_with_required_fields(self) -> None:
        """Verifica que se crea una observación con todos los campos."""
        obs = self.engine.create_observation(
            observation_type=PERSON_ENTERED_ZONE, **self.base
        )
        self.assertIsInstance(obs, Observation)
        self.assertEqual(obs.store_id, "STORE-001")
        self.assertEqual(obs.camera_id, "CAM-001")
        self.assertEqual(obs.zone_id, "ZONE-001")
        self.assertEqual(obs.track_id, 1)
        self.assertEqual(obs.observation_type, PERSON_ENTERED_ZONE)

    def test_unique_identifier(self) -> None:
        """Verifica que los identificadores son únicos."""
        obs1 = self.engine.create_observation(
            observation_type=PERSON_ENTERED_ZONE, **self.base
        )
        obs2 = self.engine.create_observation(
            observation_type=PERSON_ENTERED_ZONE, **self.base
        )
        self.assertNotEqual(obs1.observation_id, obs2.observation_id)

    def test_observation_is_immutable(self) -> None:
        """Verifica que la observación es inmutable."""
        obs = self.engine.create_observation(
            observation_type=PERSON_ENTERED_ZONE, **self.base
        )
        with self.assertRaises(Exception):
            obs.track_id = 99

    def test_requires_timestamp(self) -> None:
        """Verifica rechazo sin fecha y hora."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "timestamp": ""}
            )

    def test_requires_store(self) -> None:
        """Verifica rechazo sin tienda."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "store_id": ""}
            )

    def test_requires_camera(self) -> None:
        """Verifica rechazo sin cámara."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "camera_id": ""}
            )

    def test_requires_zone(self) -> None:
        """Verifica rechazo sin zona."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "zone_id": ""}
            )

    def test_requires_track(self) -> None:
        """Verifica rechazo sin identificador temporal."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "track_id": None}
            )

    def test_rejects_invalid_type(self) -> None:
        """Verifica rechazo de tipo de observación inválido."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type="INVENTED", **self.base
            )

    def test_rejects_invalid_confidence(self) -> None:
        """Verifica rechazo de confianza fuera de rango."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "confidence": 1.5}
            )

    def test_rejects_negative_frame(self) -> None:
        """Verifica rechazo de fotograma de origen negativo."""
        with self.assertRaises(InvalidObservationError):
            self.engine.create_observation(
                observation_type=PERSON_ENTERED_ZONE,
                **{**self.base, "source_frame": -1}
            )

    def test_entered_transition(self) -> None:
        """Verifica conversión de transición ENTERED."""
        obs = self.engine.process_transition(
            "ENTERED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        self.assertIsNotNone(obs)
        self.assertEqual(obs.observation_type, PERSON_ENTERED_ZONE)

    def test_exited_transition(self) -> None:
        """Verifica conversión de transición EXITED."""
        obs = self.engine.process_transition(
            "EXITED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=20,
        )
        self.assertIsNotNone(obs)
        self.assertEqual(obs.observation_type, PERSON_EXITED_ZONE)

    def test_remained_transition(self) -> None:
        """Verifica conversión de transición REMAINED."""
        obs = self.engine.process_transition(
            "REMAINED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        self.assertIsNotNone(obs)
        self.assertEqual(obs.observation_type, PERSON_REMAINED_IN_ZONE)

    def test_remained_is_throttled(self) -> None:
        """Verifica que permanencia no se registra en cada fotograma."""
        engine = ObservationEngine(remain_interval_frames=30)
        first = engine.process_transition(
            "REMAINED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        second = engine.process_transition(
            "REMAINED", timestamp="2026-08-02T12:00:01Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=11,
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_outside_returns_none(self) -> None:
        """Verifica que OUTSIDE no produce observación."""
        obs = self.engine.process_transition(
            "OUTSIDE", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        self.assertIsNone(obs)

    def test_reset(self) -> None:
        """Verifica que reset reinicia el estado."""
        self.engine.process_transition(
            "ENTERED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        self.engine.reset()
        obs = self.engine.process_transition(
            "ENTERED", timestamp="2026-08-02T12:00:00Z",
            store_id="STORE-001", camera_id="CAM-001", zone_id="ZONE-001",
            track_id=1, source_frame=10,
        )
        self.assertEqual(obs.observation_id, "OBS-00001")


if __name__ == "__main__":
    unittest.main()
