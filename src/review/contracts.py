"""Signal-level review records. These describe evidence, never guilt."""

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from src.behavior.contracts import BehaviorFeature, BehaviorSignal
from src.observability.logging_setup import redact_rtsp_url


ALLOWED_CLASSIFICATIONS = (
    "NOT_REVIEWED",
    "USEFUL_SIGNAL",
    "BENIGN_ACTIVITY",
    "AMBIGUOUS",
    "INSUFFICIENT_EVIDENCE",
    "SYSTEM_ERROR",
)


def _safe(value: Any) -> Any:
    if isinstance(value, str):
        return redact_rtsp_url(value)
    if isinstance(value, tuple):
        return [_safe(item) for item in value]
    if isinstance(value, list):
        return [_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class SignalReviewRecord:
    review_id: str
    signal_id: str
    signal_type: str
    camera_id: str
    track_id: Optional[str]
    trajectory_id: Optional[str]
    rule_id: str
    timestamp_start: str
    timestamp_end: str
    rule_score: float
    source_refs: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    structured_explanation: Mapping[str, Any]
    human_classification: str = "NOT_REVIEWED"
    review_notes: str = ""
    created_at: str = ""
    evidence_available: bool = True

    def __post_init__(self) -> None:
        if self.human_classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError(f"unsupported human classification: {self.human_classification}")
        if not self.camera_id:
            raise ValueError("camera_id is required")

    def with_review(self, classification: str, notes: str = "") -> "SignalReviewRecord":
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise ValueError(f"unsupported human classification: {classification}")
        return replace(self, human_classification=classification, review_notes=notes)

    def to_dict(self) -> Dict[str, Any]:
        return _safe(dict(self.__dict__))


def _unique(items: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def record_from_signal(
    signal: BehaviorSignal,
    features: Iterable[BehaviorFeature],
    *,
    created_at: str,
    track_id: Optional[str] = None,
    trajectory_id: Optional[str] = None,
    thresholds: Optional[Mapping[str, Any]] = None,
) -> SignalReviewRecord:
    """Create a review record without inventing absent evidence or conclusions."""
    matching = tuple(feature for feature in features if feature.feature_id in signal.feature_refs)
    source_refs = _unique(ref for feature in matching for ref in feature.source_refs)
    observed = tuple(
        {
            "feature_id": feature.feature_id,
            "feature_type": feature.feature_type,
            "value": feature.value,
        }
        for feature in matching
    )
    subject = signal.subject_ref
    if trajectory_id is None and subject.startswith("TRAJ-"):
        trajectory_id = subject
    elif track_id is None:
        track_id = subject
    explanation = {
        "rule_id": signal.rule_id,
        "rule_score": signal.rule_score,
        "threshold": (thresholds or {}).get(signal.rule_id, "configured_rule"),
        "observed_facts": observed,
    }
    digest = sha256(f"signal-review-v1\0{signal.signal_id}".encode("utf-8")).hexdigest()[:20]
    return SignalReviewRecord(
        review_id=f"SRR-{digest}",
        signal_id=signal.signal_id,
        signal_type=signal.signal_type,
        camera_id=signal.camera_ids[0] if signal.camera_ids else "UNKNOWN",
        track_id=track_id,
        trajectory_id=trajectory_id,
        rule_id=signal.rule_id,
        timestamp_start=signal.window_start,
        timestamp_end=signal.window_end,
        rule_score=signal.rule_score,
        source_refs=source_refs,
        evidence_refs=tuple(signal.evidence_refs),
        structured_explanation=explanation,
        created_at=created_at,
        evidence_available=bool(signal.evidence_refs),
    )
