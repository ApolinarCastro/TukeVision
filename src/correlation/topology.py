"""Explicit config-driven camera topology contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

TRANSITION_ALLOWED = "TRANSITION_ALLOWED"
TRANSITION_DISABLED = "TRANSITION_DISABLED"
TRANSITION_NOT_CONFIGURED = "TRANSITION_NOT_CONFIGURED"


@dataclass(frozen=True)
class TransitionRule:
    source_camera: str
    target_camera: str
    min_transition_seconds: float
    max_transition_seconds: float
    enabled: bool = True
    direction: Optional[str] = None
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_camera or not self.target_camera:
            raise ValueError("source_camera/target_camera son obligatorios")
        if self.source_camera == self.target_camera:
            raise ValueError("una transición cross-camera requiere cámaras distintas")
        if self.min_transition_seconds < 0:
            raise ValueError("min_transition_seconds no puede ser negativo")
        if self.max_transition_seconds < self.min_transition_seconds:
            raise ValueError("ventana temporal inválida")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight debe estar entre 0 y 1")


class CameraTopology:
    """Immutable lookup of configured directed camera transitions."""

    def __init__(self, rules: Tuple[TransitionRule, ...]) -> None:
        pairs = [(rule.source_camera, rule.target_camera) for rule in rules]
        if len(set(pairs)) != len(pairs):
            raise ValueError("transición topológica duplicada")
        self._rules = {pair: rule for pair, rule in zip(pairs, rules)}

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "CameraTopology":
        block = config.get("correlation") if isinstance(config, dict) else None
        if not isinstance(block, dict):
            raise ValueError("config.correlation es obligatorio")
        raw_rules = block.get("transitions")
        if not isinstance(raw_rules, list):
            raise ValueError("correlation.transitions debe ser una lista")
        rules = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                raise ValueError("cada transición debe ser un objeto")
            rules.append(TransitionRule(
                source_camera=str(raw.get("source_camera", "")).strip(),
                target_camera=str(raw.get("target_camera", "")).strip(),
                min_transition_seconds=float(raw.get("min_transition_seconds", 0.0)),
                max_transition_seconds=float(raw.get("max_transition_seconds", 0.0)),
                enabled=bool(raw.get("enabled", True)),
                direction=(str(raw["direction"]) if raw.get("direction") else None),
                weight=float(raw.get("weight", 1.0)),
            ))
        return cls(tuple(rules))

    def transition_state(self, source_camera: str, target_camera: str) -> str:
        rule = self._rules.get((source_camera, target_camera))
        if rule is None:
            return TRANSITION_NOT_CONFIGURED
        return TRANSITION_ALLOWED if rule.enabled else TRANSITION_DISABLED

    def rule(self, source_camera: str, target_camera: str) -> Optional[TransitionRule]:
        return self._rules.get((source_camera, target_camera))

    def to_dict(self) -> Dict[str, Any]:
        return {"transitions": [
            {
                "source_camera": rule.source_camera,
                "target_camera": rule.target_camera,
                "min_transition_seconds": rule.min_transition_seconds,
                "max_transition_seconds": rule.max_transition_seconds,
                "enabled": rule.enabled,
                "direction": rule.direction,
                "weight": rule.weight,
            }
            for rule in self._rules.values()
        ]}
