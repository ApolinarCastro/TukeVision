"""Deterministic behavior features, signals and explainable review candidates."""

from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Iterable, Optional, Tuple

from src.behavior.contracts import BehaviorFeature, BehaviorResult, BehaviorSignal, RiskEvent


DEFAULT_RULES = {
    "prolonged_dwell": {"enabled": True, "min_seconds": 30.0, "score": 25.0},
    "repeated_activity": {"enabled": True, "min_events": 3, "score": 20.0},
    "multi_camera_sequence": {"enabled": True, "min_transitions": 2, "score": 30.0},
    "repeated_zone_activity": {"enabled": True, "min_visits": 3, "score": 20.0},
}


def _seconds(start: str, end: str) -> float:
    def parse(value: str) -> datetime:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    return max(0.0, (parse(end) - parse(start)).total_seconds())


def _unique(values: Iterable[Any]) -> Tuple[str, ...]:
    result = []
    for value in values:
        if value and str(value) not in result:
            result.append(str(value))
    return tuple(result)


def _id(prefix: str, *parts: Any) -> str:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest.upper()}"


class BehaviorEngine:
    """Config-driven and bounded. A result is an operational hypothesis only."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        block = (config or {}).get("behavior", config or {})
        if not isinstance(block, dict):
            raise ValueError("behavior debe ser un dict")
        self._enabled = bool(block.get("enabled", True))
        retention = block.get("retention", {}) or {}
        self._max_results = int(retention.get("max_results", 64))
        if self._max_results < 1 or self._max_results > 4096:
            raise ValueError("behavior.retention.max_results debe estar entre 1 y 4096")
        self._history = deque(maxlen=self._max_results)
        self._rules = {name: dict(values) for name, values in DEFAULT_RULES.items()}
        for name, values in (block.get("rules", {}) or {}).items():
            if name in self._rules and isinstance(values, dict):
                self._rules[name].update(values)
        risk = block.get("risk", {}) or {}
        self._min_signals = int(risk.get("min_signal_count", 2))
        self._review_threshold = float(risk.get("review_threshold", 60.0))
        self._evaluated = 0
        self._risk_events = 0

    def evaluate(self, observation: Any = None, event: Any = None, track: Any = None,
                 activity: Any = None, trajectory: Any = None,
                 metadata: Optional[Dict[str, Any]] = None) -> BehaviorResult:
        subject = str(getattr(trajectory, "trajectory_id", None) or
                      getattr(track, "track_id", None) or
                      getattr(event, "event_id", None) or
                      getattr(observation, "observation_id", None) or "UNBOUND")
        camera_ids = tuple(getattr(trajectory, "camera_sequence", ()) or ())
        if not camera_ids:
            camera = getattr(track, "camera_id", None) or getattr(event, "camera_id", None) or getattr(observation, "camera_id", None)
            camera_ids = (str(camera),) if camera else ()
        if not self._enabled:
            return BehaviorResult(subject, camera_ids)

        start = str(getattr(trajectory, "start_time", None) or getattr(activity, "started_at", None) or getattr(track, "started_at", None) or getattr(event, "timestamp", ""))
        end = str(getattr(trajectory, "latest_time", None) or getattr(activity, "last_seen_at", None) or getattr(track, "last_seen_at", None) or getattr(event, "timestamp", ""))
        refs = getattr(track, "evidence_refs", {}) or {}
        evidence = list(refs.values()) + list(getattr(trajectory, "evidence_refs", ()) or ())
        evidence += [getattr(event, "evidence_ref", None), getattr(observation, "evidence_ref", None)]
        evidence_refs = _unique(evidence)
        source_refs = _unique((getattr(observation, "observation_id", None), getattr(event, "event_id", None), getattr(track, "track_id", None), getattr(trajectory, "trajectory_id", None)))

        raw = []
        if track is not None and start and end:
            raw.append(("track_duration_seconds", _seconds(track.started_at, track.last_seen_at)))
            raw.append(("event_count", int(getattr(track, "event_count", 0))))
        if activity is not None:
            raw.append(("dwell_seconds", float(getattr(activity, "duration_ms", 0)) / 1000.0))
        elif track is not None:
            raw.append(("dwell_seconds", _seconds(track.started_at, track.last_seen_at)))
        if trajectory is not None:
            raw.extend((("trajectory_duration_seconds", _seconds(trajectory.start_time, trajectory.latest_time)),
                        ("camera_count", len(camera_ids)), ("transition_count", len(trajectory.edges))))
        meta = metadata or {}
        if "zone_visits" in meta:
            try:
                raw.append(("zone_visits", max(0, int(meta["zone_visits"]))))
            except (TypeError, ValueError):
                pass
        features = tuple(BehaviorFeature(_id("BF", subject, name, value, start, end), name, value,
                         subject, camera_ids, start, end, source_refs, evidence_refs) for name, value in raw)
        feature_map = {item.feature_type: item for item in features}
        signals = []
        checks = (("prolonged_dwell", "dwell_seconds", "min_seconds", "PROLONGED_DWELL"),
                  ("repeated_activity", "event_count", "min_events", "REPEATED_ACTIVITY"),
                  ("multi_camera_sequence", "transition_count", "min_transitions", "MULTI_CAMERA_SEQUENCE"),
                  ("repeated_zone_activity", "zone_visits", "min_visits", "REPEATED_ZONE_ACTIVITY"))
        for rule_id, feature_name, threshold_name, signal_type in checks:
            rule = self._rules[rule_id]
            feature = feature_map.get(feature_name)
            if rule.get("enabled", True) and feature is not None and feature.value >= float(rule[threshold_name]):
                signals.append(BehaviorSignal(
                    _id("BS", subject, rule_id, feature.feature_id), signal_type, rule_id,
                    float(rule.get("score", 0)), subject, (feature.feature_id,), camera_ids,
                    start, end, evidence_refs,
                    "AMBIGUOUS" if getattr(trajectory, "status", None) == "AMBIGUOUS" else "CANDIDATE"))
        ambiguous = getattr(trajectory, "status", None) == "AMBIGUOUS"
        risk_event = None
        if not ambiguous and len(signals) >= self._min_signals:
            score = min(100.0, sum(item.rule_score for item in signals))
            status = "REVIEW_REQUIRED" if score >= self._review_threshold else "CANDIDATE"
            rules = tuple(item.rule_id for item in signals)
            risk_event = RiskEvent(
                _id("RISK", subject, *rules, start, end), "BEHAVIOR_RISK_CANDIDATE", score,
                status, subject, tuple(item.signal_id for item in signals), rules, camera_ids,
                start, end, evidence_refs,
                (("basis", "deterministic_configured_rules"), ("signal_count", len(signals)),
                 ("human_review_required", True), ("non_accusatory", True)))
            self._risk_events += 1
        result = BehaviorResult(subject, camera_ids, features, tuple(signals), risk_event, evidence_refs, ambiguous)
        self._history.append(result)
        self._evaluated += 1
        return result

    def metrics(self) -> Dict[str, int]:
        return {"evaluated": self._evaluated, "risk_events": self._risk_events,
                "retained_results": len(self._history), "max_results": self._max_results}

    def close(self) -> Dict[str, int]:
        return self.metrics()


def build_behavior_engine(config: Dict[str, Any]) -> BehaviorEngine:
    return BehaviorEngine(config)
