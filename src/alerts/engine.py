"""Motor de alertas.

Responsabilidad única: generar alertas cuando el riesgo alcanza el umbral
definido. No todo evento genera alerta. No envía mensajería ni confirma
incidentes.
"""

from typing import Optional

from src.risk.calculator import RiskScore
from src.events.models import Event
from src.alerts.models import (
    Alert,
    STATUS_NEW,
    VALID_STATUSES,
)


class AlertError(Exception):
    """Excepción base para errores del motor de alertas."""
    pass


class InvalidAlertError(AlertError):
    """Datos insuficientes o inválidos para crear una alerta."""
    pass


class AlertEngine:
    """Genera alertas a partir de riesgos que superan el umbral."""

    def __init__(self, risk_threshold: int = 60) -> None:
        self._risk_threshold = risk_threshold
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"ALR-{self._counter:05d}"

    def evaluate(self, event: Event, risk: RiskScore) -> Optional[Alert]:
        """Evalúa un riesgo y devuelve una alerta si corresponde.

        Returns:
            Alert si risk.score >= umbral, o None en caso contrario.
        """
        if event is None:
            raise InvalidAlertError("El evento es obligatorio")
        if risk is None:
            raise InvalidAlertError("El riesgo es obligatorio")
        if risk.event_id != event.event_id:
            raise InvalidAlertError(
                "El riesgo no corresponde al evento indicado"
            )
        if not (0 <= risk.score <= 100):
            raise InvalidAlertError(
                "El puntaje de riesgo debe estar entre 0 y 100"
            )

        if risk.score < self._risk_threshold:
            return None

        rule_id = risk.rule_ids[0] if risk.rule_ids else ""

        return Alert(
            alert_id=self._next_id(),
            event_id=event.event_id,
            risk_score=risk.score,
            rule_id=rule_id,
            created_at=event.timestamp,
            status=STATUS_NEW,
            explanation=risk.explanation,
        )

    def reset(self) -> None:
        """Reinicia el contador de alertas."""
        self._counter = 0
