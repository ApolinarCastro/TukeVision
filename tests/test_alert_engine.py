"""Pruebas unitarias para src.alerts (sin dependencias externas)."""

import unittest

from src.alerts.engine import AlertEngine, InvalidAlertError
from src.alerts.models import Alert, STATUS_NEW, VALID_STATUSES
from src.events.models import Event, PERMANENCIA_PROLONGADA
from src.risk.calculator import RiskScore


def _event(duration=90.0):
    return Event(
        event_id="EVT-00001",
        event_type=PERMANENCIA_PROLONGADA,
        timestamp="2026-08-02T12:00:00Z",
        store_id="STORE-001",
        camera_id="CAM-001",
        zone_id="ZONE-001",
        track_id=1,
        observation_ids=("OBS-00001", "OBS-00002"),
        duration_seconds=duration,
    )


def _risk(score=80, event_id="EVT-00001"):
    return RiskScore(
        score=score,
        event_id=event_id,
        rule_ids=("RULE-PERMANENCIA-001",),
        explanation="Permanencia de 90.0 segundos.",
        duration_seconds=90.0,
    )


class TestAlertEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = AlertEngine(risk_threshold=60)
        self.event = _event()

    def test_alert_created_when_risk_above_threshold(self) -> None:
        """Verifica que se crea alerta con riesgo >= 60."""
        alert = self.engine.evaluate(self.event, _risk(score=60))
        self.assertIsNotNone(alert)
        self.assertIsInstance(alert, Alert)
        self.assertEqual(alert.risk_score, 60)
        self.assertEqual(alert.status, STATUS_NEW)

    def test_alert_created_at_80(self) -> None:
        """Verifica que se crea alerta con riesgo 80."""
        alert = self.engine.evaluate(self.event, _risk(score=80))
        self.assertIsNotNone(alert)
        self.assertEqual(alert.risk_score, 80)

    def test_no_alert_below_threshold(self) -> None:
        """Verifica que no hay alerta bajo el umbral."""
        alert = self.engine.evaluate(self.event, _risk(score=40))
        self.assertIsNone(alert)

    def test_alert_explains_origin(self) -> None:
        """Verifica que la alerta explica su origen."""
        alert = self.engine.evaluate(self.event, _risk())
        self.assertIn("RULE-PERMANENCIA-001", alert.rule_id)
        self.assertIn("Permanencia de 90.0", alert.explanation)

    def test_alert_links_event_and_risk(self) -> None:
        """Verifica que la alerta conserva el evento y el riesgo."""
        alert = self.engine.evaluate(self.event, _risk())
        self.assertEqual(alert.event_id, "EVT-00001")

    def test_alert_status_is_new(self) -> None:
        """Verifica que el estado inicial es NEW."""
        alert = self.engine.evaluate(self.event, _risk())
        self.assertEqual(alert.status, STATUS_NEW)
        self.assertIn(alert.status, VALID_STATUSES)

    def test_alert_is_immutable(self) -> None:
        """Verifica que la alerta es inmutable."""
        alert = self.engine.evaluate(self.event, _risk())
        with self.assertRaises(Exception):
            alert.status = STATUS_CLOSED

    def test_rejects_none_event(self) -> None:
        """Verifica rechazo de evento nulo."""
        with self.assertRaises(InvalidAlertError):
            self.engine.evaluate(None, _risk())

    def test_rejects_none_risk(self) -> None:
        """Verifica rechazo de riesgo nulo."""
        with self.assertRaises(InvalidAlertError):
            self.engine.evaluate(self.event, None)

    def test_rejects_mismatched_risk(self) -> None:
        """Verifica rechazo si el riesgo no corresponde al evento."""
        with self.assertRaises(InvalidAlertError):
            self.engine.evaluate(self.event, _risk(event_id="EVT-OTRO"))

    def test_rejects_invalid_score(self) -> None:
        """Verifica rechazo de puntaje fuera de rango."""
        with self.assertRaises(InvalidAlertError):
            self.engine.evaluate(self.event, _risk(score=150))

    def test_unique_alert_ids(self) -> None:
        """Verifica que los identificadores de alerta son únicos."""
        a1 = self.engine.evaluate(self.event, _risk())
        a2 = self.engine.evaluate(self.event, _risk())
        self.assertNotEqual(a1.alert_id, a2.alert_id)


if __name__ == "__main__":
    unittest.main()
