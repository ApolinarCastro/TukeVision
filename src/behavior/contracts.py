"""Explainable behavior/risk contracts. Signals are hypotheses, never guilt."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.observability.logging_setup import redact_rtsp_url


def _safe(value: Any) -> Any:
    if isinstance(value, str):
        return redact_rtsp_url(value)
    if isinstance(value, tuple):
        return [_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class BehaviorFeature:
    feature_id: str
    feature_type: str
    value: Any
    subject_ref: str
    camera_ids: Tuple[str, ...]
    window_start: str
    window_end: str
    source_refs: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    status: str = "FACT"

    def to_dict(self) -> Dict[str, Any]:
        return _safe(self.__dict__)


@dataclass(frozen=True)
class BehaviorSignal:
    signal_id: str
    signal_type: str
    rule_id: str
    rule_score: float
    subject_ref: str
    feature_refs: Tuple[str, ...]
    camera_ids: Tuple[str, ...]
    window_start: str
    window_end: str
    evidence_refs: Tuple[str, ...] = ()
    status: str = "CANDIDATE"

    def to_dict(self) -> Dict[str, Any]:
        return _safe(self.__dict__)


@dataclass(frozen=True)
class RiskEvent:
    risk_event_id: str
    risk_event_type: str
    risk_score: float
    status: str
    subject_ref: str
    signal_refs: Tuple[str, ...]
    rules_triggered: Tuple[str, ...]
    camera_ids: Tuple[str, ...]
    window_start: str
    window_end: str
    evidence_refs: Tuple[str, ...]
    explanation: Tuple[Tuple[str, Any], ...]

    def to_dict(self) -> Dict[str, Any]:
        data = dict(self.__dict__)
        data["explanation"] = dict(self.explanation)
        return _safe(data)


@dataclass(frozen=True)
class BehaviorResult:
    subject_ref: str
    camera_ids: Tuple[str, ...]
    features: Tuple[BehaviorFeature, ...] = ()
    signals: Tuple[BehaviorSignal, ...] = ()
    risk_event: Optional[RiskEvent] = None
    evidence_refs: Tuple[str, ...] = ()
    ambiguous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_ref": redact_rtsp_url(self.subject_ref),
            "camera_ids": list(self.camera_ids),
            "features": [item.to_dict() for item in self.features],
            "signals": [item.to_dict() for item in self.signals],
            "risk_event": self.risk_event.to_dict() if self.risk_event else None,
            "evidence_refs": [redact_rtsp_url(item) for item in self.evidence_refs],
            "ambiguous": self.ambiguous,
        }
