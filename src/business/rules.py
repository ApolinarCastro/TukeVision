"""Motor del negocio.

Responsabilidad única: definir y aplicar reglas del negocio sobre eventos
para evaluar si requieren atención. No confirma incidentes.
"""

from dataclasses import dataclass
from typing import Optional

from src.events.models import Event, PERMANENCIA_PROLONGADA


class RuleError(Exception):
    """Excepción base para errores de reglas del negocio."""
    pass


class InvalidRuleError(RuleError):
    """Datos insuficientes o inválidos para definir una regla."""
    pass


@dataclass(frozen=True)
class Rule:
    """Regla del negocio auditable y configurable."""
    rule_id: str
    name: str
    description: str
    event_type: str
    max_stay_seconds: float
    enabled: bool = True


class RuleEngine:
    """Aplica reglas del negocio sobre eventos."""

    def __init__(self, rules: Optional[list] = None) -> None:
        self._rules = list(rules) if rules else []

    def add_rule(self, rule: Rule) -> None:
        if rule is None:
            raise InvalidRuleError("La regla es obligatoria")
        if not rule.rule_id:
            raise InvalidRuleError("El identificador de la regla es obligatorio")
        if not rule.name:
            raise InvalidRuleError("El nombre de la regla es obligatorio")
        if not rule.event_type:
            raise InvalidRuleError("El tipo de evento es obligatorio")
        if rule.max_stay_seconds < 0:
            raise InvalidRuleError(
                "El tiempo máximo de permanencia no puede ser negativo"
            )
        self._rules.append(rule)

    @property
    def rules(self) -> tuple:
        return tuple(self._rules)

    def matching_rules(self, event: Event) -> list:
        """Devuelve las reglas activas aplicables al evento."""
        if event is None:
            raise InvalidRuleError("El evento es obligatorio")
        return [
            rule for rule in self._rules
            if rule.enabled and rule.event_type == event.event_type
        ]

    def evaluate(self, event: Event) -> Optional[Rule]:
        """Devuelve la regla aplicable que se activa con el evento.

        Returns:
            La regla que evalúa el evento, o None si ninguna aplica.
        """
        rules = self.matching_rules(event)
        if not rules:
            return None
        for rule in rules:
            if event.duration_seconds > rule.max_stay_seconds:
                return rule
        return None


def default_rule() -> Rule:
    """Regla inicial del prototipo."""
    return Rule(
        rule_id="RULE-PERMANENCIA-001",
        name="Permanencia prolongada",
        description=(
            "Si una persona permanece dentro de la zona durante más de "
            "30 segundos, evaluar el evento."
        ),
        event_type=PERMANENCIA_PROLONGADA,
        max_stay_seconds=30.0,
        enabled=True,
    )
