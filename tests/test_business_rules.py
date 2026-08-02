"""Pruebas unitarias para src.business.rules (sin dependencias externas)."""

import unittest

from src.business.rules import Rule, RuleEngine, InvalidRuleError, default_rule
from src.events.models import Event, PERMANENCIA_PROLONGADA


def _event(duration=60.0, event_type=PERMANENCIA_PROLONGADA, event_id="EVT-00001"):
    return Event(
        event_id=event_id,
        event_type=event_type,
        timestamp="2026-08-02T12:00:00Z",
        store_id="STORE-001",
        camera_id="CAM-001",
        zone_id="ZONE-001",
        track_id=1,
        observation_ids=("OBS-00001", "OBS-00002"),
        duration_seconds=duration,
    )


class TestBusinessRules(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = RuleEngine()
        self.rule = default_rule()
        self.engine.add_rule(self.rule)

    def test_default_rule_definition(self) -> None:
        """Verifica que la regla inicial tiene los valores definidos."""
        self.assertEqual(self.rule.rule_id, "RULE-PERMANENCIA-001")
        self.assertEqual(self.rule.event_type, PERMANENCIA_PROLONGADA)
        self.assertEqual(self.rule.max_stay_seconds, 30.0)
        self.assertTrue(self.rule.enabled)

    def test_matching_rule(self) -> None:
        """Verifica que la regla coincide con el tipo de evento."""
        rules = self.engine.matching_rules(_event())
        self.assertEqual(len(rules), 1)

    def test_no_matching_for_other_event(self) -> None:
        """Verifica que no hay coincidencia para otro tipo de evento."""
        rules = self.engine.matching_rules(_event(event_type="OTRO"))
        self.assertEqual(len(rules), 0)

    def test_rule_activates_above_threshold(self) -> None:
        """Verifica que la regla se activa sobre el umbral."""
        matched = self.engine.evaluate(_event(duration=31.0))
        self.assertIsNotNone(matched)
        self.assertEqual(matched.rule_id, "RULE-PERMANENCIA-001")

    def test_rule_does_not_activate_below_threshold(self) -> None:
        """Verifica que la regla no se activa bajo el umbral."""
        matched = self.engine.evaluate(_event(duration=29.0))
        self.assertIsNone(matched)

    def test_rule_is_configurable(self) -> None:
        """Verifica que el umbral es configurable."""
        custom = Rule(
            rule_id="RULE-CUSTOM",
            name="Custom",
            description="Custom rule",
            event_type=PERMANENCIA_PROLONGADA,
            max_stay_seconds=60.0,
        )
        engine = RuleEngine([custom])
        matched = engine.evaluate(_event(duration=61.0))
        self.assertIsNotNone(matched)
        self.assertIsNone(engine.evaluate(_event(duration=59.0)))

    def test_disabled_rule_not_applied(self) -> None:
        """Verifica que una regla desactivada no se aplica."""
        disabled = Rule(
            rule_id="RULE-OFF",
            name="Off",
            description="Off",
            event_type=PERMANENCIA_PROLONGADA,
            max_stay_seconds=30.0,
            enabled=False,
        )
        engine = RuleEngine([disabled])
        self.assertIsNone(engine.evaluate(_event(duration=100.0)))

    def test_rejects_none_event(self) -> None:
        """Verifica rechazo de evento nulo."""
        with self.assertRaises(InvalidRuleError):
            self.engine.evaluate(None)

    def test_rejects_rule_without_id(self) -> None:
        """Verifica rechazo de regla sin identificador."""
        with self.assertRaises(InvalidRuleError):
            self.engine.add_rule(Rule(
                rule_id="", name="X", description="X",
                event_type=PERMANENCIA_PROLONGADA, max_stay_seconds=30.0,
            ))

    def test_rejects_negative_stay(self) -> None:
        """Verifica rechazo de tiempo máximo negativo."""
        with self.assertRaises(InvalidRuleError):
            self.engine.add_rule(Rule(
                rule_id="RULE-X", name="X", description="X",
                event_type=PERMANENCIA_PROLONGADA, max_stay_seconds=-1.0,
            ))


if __name__ == "__main__":
    unittest.main()
