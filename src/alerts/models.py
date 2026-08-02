"""Modelos de alertas.

Una alerta es una notificación generada cuando el nivel de riesgo supera
las condiciones definidas por el negocio. No confirma incidentes.
"""

from dataclasses import dataclass

STATUS_NEW = "NEW"
STATUS_VIEWED = "VIEWED"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_CLOSED = "CLOSED"

VALID_STATUSES = (
    STATUS_NEW,
    STATUS_VIEWED,
    STATUS_UNDER_REVIEW,
    STATUS_CONFIRMED,
    STATUS_CLOSED,
)


@dataclass(frozen=True)
class Alert:
    """Alerta inmutable generada a partir de un riesgo."""
    alert_id: str
    event_id: str
    risk_score: int
    rule_id: str
    created_at: str
    status: str
    explanation: str
    evidence_id: str = ""
