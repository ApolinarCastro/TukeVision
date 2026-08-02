"""Cálculo de riesgo.

Responsabilidad única: evaluar el nivel de atención que requiere un evento
según las reglas del negocio, con un puntaje explicable de 0 a 100.
No confirma incidentes.
"""

from dataclasses import dataclass
from typing import List

from src.events.models import Event
from src.business.rules import Rule


class RiskError(Exception):
    """Excepción base para errores del cálculo de riesgo."""
    pass


class InvalidRiskInputError(RiskError):
    """Datos insuficientes o inválidos para calcular el riesgo."""
    pass


@dataclass(frozen=True)
class RiskScore:
    """Evaluación de riesgo explicable."""
    score: int
    event_id: str
    rule_ids: tuple
    explanation: str
    duration_seconds: float


class RiskCalculator:
    """Calcula el puntaje de riesgo según rangos de permanencia."""

    def __init__(self) -> None:
        self._ranges = (
            (0.0, 30.0, 0),
            (30.0, 45.0, 40),
            (45.0, 60.0, 60),
            (60.0, float("inf"), 80),
        )

    def _score_for(self, duration: float) -> int:
        for lower, upper, score in self._ranges:
            if lower <= duration < upper:
                return score
        return 0

    def calculate(self, event: Event, rule: Rule) -> RiskScore:
        """Calcula el riesgo del evento aplicando la regla indicada."""
        if event is None:
            raise InvalidRiskInputError("El evento es obligatorio")
        if rule is None:
            raise InvalidRiskInputError("La regla aplicada es obligatoria")

        if event.duration_seconds <= rule.max_stay_seconds:
            raise InvalidRiskInputError(
                "El evento no supera el tiempo máximo de la regla"
            )

        score = self._score_for(event.duration_seconds)
        explanation = (
            f"La persona permaneció {event.duration_seconds:.1f} segundos "
            f"en la zona, superando los {rule.max_stay_seconds:.0f} segundos "
            f"permitidos por la regla {rule.rule_id}."
        )

        return RiskScore(
            score=score,
            event_id=event.event_id,
            rule_ids=(rule.rule_id,),
            explanation=explanation,
            duration_seconds=event.duration_seconds,
        )
