"""Pruebas unitarias para src.risk.calculator (sin dependencias externas)."""

import unittest

from src.risk.calculator import RiskCalculator, InvalidRiskInputError, RiskScore
from src.business.rules import Rule, default_rule
from src.events.models import Event, PERMANENCIA_PROLONGADA


def _event(duration=60.0):
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


class TestRiskCalculator(unittest.TestCase):

    def setUp(self) -> None:
        self.calculator = RiskCalculator()
        self.rule = default_rule()

    def test_under_30_seconds_risk_zero(self) -> None:
        """Verifica puntaje 0 para menos de 30 segundos."""
        # 29s no supera el umbral, pero el cálculo exige superarlo;
        # usamos una regla con umbral menor para validar el rango 0.
        rule = Rule(
            rule_id="RULE-0", name="R0", description="R0",
            event_type=PERMANENCIA_PROLONGADA, max_stay_seconds=1.0,
        )
        result = self.calculator.calculate(_event(duration=20.0), rule)
        self.assertEqual(result.score, 0)

    def test_30_to_45_seconds_risk_40(self) -> None:
        """Verifica puntaje 40 entre 30 y 45 segundos."""
        rule = Rule(
            rule_id="RULE-40", name="R40", description="R40",
            event_type=PERMANENCIA_PROLONGADA, max_stay_seconds=1.0,
        )
        result = self.calculator.calculate(_event(duration=40.0), rule)
        self.assertEqual(result.score, 40)

    def test_46_to_60_seconds_risk_60(self) -> None:
        """Verifica puntaje 60 entre 46 y 60 segundos."""
        result = self.calculator.calculate(_event(duration=50.0), self.rule)
        self.assertEqual(result.score, 60)

    def test_over_60_seconds_risk_80(self) -> None:
        """Verifica puntaje 80 para más de 60 segundos."""
        result = self.calculator.calculate(_event(duration=90.0), self.rule)
        self.assertEqual(result.score, 80)

    def test_exact_60_seconds_risk_80(self) -> None:
        """Verifica que 60 segundos exactos caen en el rango de 80."""
        result = self.calculator.calculate(_event(duration=60.0), self.rule)
        self.assertEqual(result.score, 80)

    def test_risk_is_explainable(self) -> None:
        """Verifica que el riesgo incluye explicación y regla aplicada."""
        result = self.calculator.calculate(_event(duration=90.0), self.rule)
        self.assertIsInstance(result, RiskScore)
        self.assertIn("RULE-PERMANENCIA-001", result.rule_ids)
        self.assertIn("90.0", result.explanation)

    def test_risk_is_immutable(self) -> None:
        """Verifica que el resultado de riesgo es inmutable."""
        result = self.calculator.calculate(_event(duration=90.0), self.rule)
        with self.assertRaises(Exception):
            result.score = 0

    def test_rejects_none_event(self) -> None:
        """Verifica rechazo de evento nulo."""
        with self.assertRaises(InvalidRiskInputError):
            self.calculator.calculate(None, self.rule)

    def test_rejects_none_rule(self) -> None:
        """Verifica rechazo de regla nula."""
        with self.assertRaises(InvalidRiskInputError):
            self.calculator.calculate(_event(duration=90.0), None)

    def test_rejects_event_under_rule_threshold(self) -> None:
        """Verifica rechazo si el evento no supera el umbral de la regla."""
        with self.assertRaises(InvalidRiskInputError):
            self.calculator.calculate(_event(duration=10.0), self.rule)


if __name__ == "__main__":
    unittest.main()
