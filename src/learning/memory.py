"""Learning Foundation (AG-06 / OC-15, OC-16, OC-17).

Closed-loop human feedback system:
SIGNAL -> EVIDENCE -> HUMAN REVIEW -> LABEL -> DATASET -> CANDIDATE -> VALIDATION -> PROMOTION

Governance guarantees:
  - No autonomous model/policy promotion (SDL-07, SDL-09, SDL-20).
  - ``INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT``: a candidate whose
    validation metrics do not beat the current policy is rejected at the
    promotion gate.
  - Every policy transition requires explicit human validation.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class CaseClassification(Enum):
    """Case classification per OC-15."""
    RAW_CASE = "RAW_CASE"
    REVIEWED_CASE = "REVIEWED_CASE"
    TRAINING_ELIGIBLE_CASE = "TRAINING_ELIGIBLE_CASE"


class SignalLabel(Enum):
    """Human review labels per QW-00."""
    USEFUL_SIGNAL = "USEFUL_SIGNAL"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class RawCase:
    """Raw case from signal generation (OC-15)."""
    case_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp_utc: str = field(default_factory=_utc_now_iso)
    signal_type: str = ""
    signal_metadata: dict = field(default_factory=dict)
    risk_score: float = 0.0
    camera_ids: Tuple[str, ...] = ()
    track_ids: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    scene_context: dict = field(default_factory=dict)
    classification: CaseClassification = CaseClassification.RAW_CASE


@dataclass(frozen=True)
class ReviewedCase:
    """Human-reviewed case (OC-15)."""
    case_id: str
    raw_case_id: str
    reviewed_at_utc: str = field(default_factory=_utc_now_iso)
    reviewer_id: str = ""
    label: SignalLabel = SignalLabel.INSUFFICIENT_EVIDENCE
    reviewer_notes: str = ""
    classification: CaseClassification = CaseClassification.REVIEWED_CASE


@dataclass(frozen=True)
class TrainingEligibleCase:
    """Case eligible for training dataset (OC-15, OC-16)."""
    case_id: str
    reviewed_case_id: str
    added_to_dataset_at_utc: str = field(default_factory=_utc_now_iso)
    dataset_version: str = ""
    classification: CaseClassification = CaseClassification.TRAINING_ELIGIBLE_CASE


@dataclass(frozen=True)
class CaseMemory:
    """Case memory store (OC-15).

    Maintains three partitions: RAW, REVIEWED, TRAINING_ELIGIBLE.
    Immutable - new cases create new entries.
    """
    raw_cases: Dict[str, RawCase] = field(default_factory=dict)
    reviewed_cases: Dict[str, ReviewedCase] = field(default_factory=dict)
    training_eligible: Dict[str, TrainingEligibleCase] = field(default_factory=dict)

    def add_raw(self, case: RawCase) -> "CaseMemory":
        new_raw = dict(self.raw_cases)
        new_raw[case.case_id] = case
        return replace(self, raw_cases=new_raw)

    def add_reviewed(self, case: ReviewedCase) -> "CaseMemory":
        new_reviewed = dict(self.reviewed_cases)
        new_reviewed[case.case_id] = case
        return replace(self, reviewed_cases=new_reviewed)

    def promote_to_training(self, reviewed_case_id: str, dataset_version: str) -> "CaseMemory":
        reviewed = self.reviewed_cases.get(reviewed_case_id)
        if not reviewed:
            return self
        if reviewed.label != SignalLabel.USEFUL_SIGNAL:
            return self
        training = TrainingEligibleCase(
            case_id=str(uuid4()),
            reviewed_case_id=reviewed_case_id,
            dataset_version=dataset_version,
        )
        new_training = dict(self.training_eligible)
        new_training[training.case_id] = training
        return replace(self, training_eligible=new_training)

    def get_raw_cases(self, signal_type: Optional[str] = None) -> Sequence[RawCase]:
        cases = self.raw_cases.values()
        if signal_type:
            cases = [c for c in cases if c.signal_type == signal_type]
        return tuple(cases)

    def get_reviewed_cases(self, label: Optional[SignalLabel] = None) -> Sequence[ReviewedCase]:
        cases = self.reviewed_cases.values()
        if label:
            cases = [c for c in cases if c.label == label]
        return tuple(cases)

    def get_training_eligible(self, dataset_version: Optional[str] = None) -> Sequence[TrainingEligibleCase]:
        cases = self.training_eligible.values()
        if dataset_version:
            cases = [c for c in cases if c.dataset_version == dataset_version]
        return tuple(cases)


@dataclass(frozen=True)
class DatasetManifest:
    """Dataset manifest with versioning and integrity (OC-16)."""
    version: str
    created_at_utc: str
    total_cases: int
    label_distribution: Dict[str, int] = field(default_factory=dict)
    case_ids: Tuple[str, ...] = ()
    manifest_hash: str = ""
    parent_version: Optional[str] = None


@dataclass(frozen=True)
class FeedbackDataset:
    """Versioned feedback dataset (OC-16).

    JSONL format with manifest. Immutable - new version = new dataset.
    """
    manifest: DatasetManifest
    records: Tuple[dict, ...] = ()

    def to_jsonl(self) -> str:
        return "\n".join(
            json.dumps(record, ensure_ascii=False) for record in self.records
        )

    @classmethod
    def from_cases(
        cls,
        cases: Sequence[TrainingEligibleCase],
        case_memory: CaseMemory,
        version: str,
        parent_version: Optional[str] = None,
    ) -> "FeedbackDataset":
        records: List[dict] = []
        label_dist: Dict[str, int] = defaultdict(int)
        for tc in cases:
            rc = case_memory.reviewed_cases.get(tc.reviewed_case_id)
            if not rc:
                continue
            raw = case_memory.raw_cases.get(rc.raw_case_id)
            if not raw:
                continue
            records.append({
                "case_id": tc.case_id,
                "raw_case_id": rc.raw_case_id,
                "reviewed_case_id": rc.case_id,
                "signal_type": raw.signal_type,
                "label": rc.label.value,
                "risk_score": raw.risk_score,
                "camera_ids": raw.camera_ids,
                "track_ids": raw.track_ids,
                "evidence_refs": raw.evidence_refs,
                "scene_context": raw.scene_context,
                "reviewed_at": rc.reviewed_at_utc,
                "reviewer_id": rc.reviewer_id,
            })
            label_dist[rc.label.value] += 1

        manifest = DatasetManifest(
            version=version,
            created_at_utc=_utc_now_iso(),
            total_cases=len(records),
            label_distribution=dict(label_dist),
            case_ids=tuple(tc.case_id for tc in cases),
            parent_version=parent_version,
        )
        manifest_json = json.dumps({
            "version": manifest.version,
            "created_at_utc": manifest.created_at_utc,
            "total_cases": manifest.total_cases,
            "label_distribution": manifest.label_distribution,
            "case_ids": manifest.case_ids,
            "parent_version": manifest.parent_version,
        }, sort_keys=True)
        manifest = replace(
            manifest,
            manifest_hash=hashlib.sha256(manifest_json.encode()).hexdigest()[:16],
        )
        return cls(manifest=manifest, records=tuple(records))


class FeedbackDatasetBuilder:
    """Builds versioned datasets from reviewed cases (OC-16)."""

    def __init__(self, case_memory: CaseMemory, dataset_root: str = "data/learning/datasets") -> None:
        self._case_memory = case_memory
        self._dataset_root = Path(dataset_root)

    def build_dataset(
        self,
        version: str,
        parent_version: Optional[str] = None,
    ) -> FeedbackDataset:
        """Build new dataset version from training-eligible cases."""
        eligible = self._case_memory.get_training_eligible()
        return FeedbackDataset.from_cases(
            eligible, self._case_memory, version, parent_version
        )

    def save_dataset(self, dataset: FeedbackDataset) -> Path:
        """Persist dataset to disk (JSONL + manifest)."""
        version_dir = self._dataset_root / dataset.manifest.version
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "dataset.jsonl").write_text(
            dataset.to_jsonl(), encoding="utf-8"
        )
        (version_dir / "manifest.json").write_text(
            json.dumps({
                "version": dataset.manifest.version,
                "created_at_utc": dataset.manifest.created_at_utc,
                "total_cases": dataset.manifest.total_cases,
                "label_distribution": dataset.manifest.label_distribution,
                "case_ids": dataset.manifest.case_ids,
                "manifest_hash": dataset.manifest.manifest_hash,
                "parent_version": dataset.manifest.parent_version,
            }, indent=2),
            encoding="utf-8",
        )
        return version_dir


@dataclass(frozen=True)
class CurrentPolicy:
    """Current production policy (OC-17).

    Immutable - changes create a CandidatePolicy that must be validated and
    explicitly promoted. ``validation_metrics`` holds the metrics that earned
    this policy its current slot (used as the promotion gate baseline).
    """
    policy_id: str
    version: str
    behavior_thresholds: Dict[str, float] = field(default_factory=dict)
    risk_weights: Dict[str, float] = field(default_factory=dict)
    zone_configs: Dict[str, dict] = field(default_factory=dict)
    created_at_utc: str = field(default_factory=_utc_now_iso)
    effective_since_utc: str = field(default_factory=_utc_now_iso)
    validation_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "behavior_thresholds": self.behavior_thresholds,
            "risk_weights": self.risk_weights,
            "zone_configs": self.zone_configs,
            "created_at_utc": self.created_at_utc,
            "effective_since_utc": self.effective_since_utc,
            "validation_metrics": self.validation_metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CurrentPolicy":
        return CurrentPolicy(
            policy_id=str(data["policy_id"]),
            version=str(data["version"]),
            behavior_thresholds=dict(data.get("behavior_thresholds", {})),
            risk_weights=dict(data.get("risk_weights", {})),
            zone_configs=dict(data.get("zone_configs", {})),
            created_at_utc=str(data.get("created_at_utc") or _utc_now_iso()),
            effective_since_utc=str(data.get("effective_since_utc") or _utc_now_iso()),
            validation_metrics=dict(data.get("validation_metrics", {})),
        )


class PolicyValidationError(Exception):
    """Candidate policy validation failed."""
    pass


class PolicyRejectionError(Exception):
    """Candidate policy cannot replace the current policy.

    Raised at the promotion gate when the candidate is inferior
    (``INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT``).
    """
    pass


@dataclass(frozen=True)
class CandidatePolicy:
    """Candidate policy change (OC-17).

    Never auto-promoted. Requires explicit promotion after validation.
    """
    candidate_id: str = field(default_factory=lambda: str(uuid4()))
    base_policy_version: str = ""
    proposed_changes: Dict[str, Any] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "DRAFT"  # DRAFT, VALIDATING, VALIDATED, REJECTED, PROMOTED
    created_at_utc: str = field(default_factory=_utc_now_iso)
    validated_at_utc: Optional[str] = None
    promoted_at_utc: Optional[str] = None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self, dataset: FeedbackDataset) -> Dict[str, float]:
        """Run offline validation on the dataset. Returns metrics.

        Deterministic evaluation of the proposed risk threshold against
        human-reviewed labels:

          predicted positive = risk_score >= risk_threshold
          ground-truth positive = label == USEFUL_SIGNAL

        The threshold is read from ``proposed_changes["risk_weights"]
        ["risk_threshold"]`` (default 60.0), mirroring the certified alert
        threshold. Metrics: precision, recall, f1_score, false_positive_rate.
        """
        records = list(dataset.records)
        weights = dict(self.proposed_changes.get("risk_weights") or {})
        try:
            threshold = float(weights.get("risk_threshold", 60.0))
        except (TypeError, ValueError):
            threshold = 60.0

        tp = fp = fn = tn = 0
        for record in records:
            label = str(record.get("label") or "")
            risk = float(record.get("risk_score") or 0.0)
            predicted_positive = risk >= threshold
            actual_positive = label == SignalLabel.USEFUL_SIGNAL.value
            if predicted_positive and actual_positive:
                tp += 1
            elif predicted_positive and not actual_positive:
                fp += 1
            elif not predicted_positive and actual_positive:
                fn += 1
            else:
                tn += 1

        denom_precision = tp + fp
        denom_recall = tp + fn
        precision = (tp / denom_precision) if denom_precision else 0.0
        recall = (tp / denom_recall) if denom_recall else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )
        fpr = (fp / (fp + tn)) if (fp + tn) else 0.0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "total_records": len(records),
        }

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------
    def apply_to_policy(self, base: CurrentPolicy) -> CurrentPolicy:
        """Apply proposed changes to base policy, returning new policy."""
        new_thresholds = dict(base.behavior_thresholds)
        new_thresholds.update(self.proposed_changes.get("behavior_thresholds", {}))
        new_weights = dict(base.risk_weights)
        new_weights.update(self.proposed_changes.get("risk_weights", {}))
        new_zones = dict(base.zone_configs)
        new_zones.update(self.proposed_changes.get("zone_configs", {}))
        return CurrentPolicy(
            policy_id=str(uuid4()),
            version=_bump_version(base.version),
            behavior_thresholds=new_thresholds,
            risk_weights=new_weights,
            zone_configs=new_zones,
            created_at_utc=base.created_at_utc,
            effective_since_utc=_utc_now_iso(),
            validation_metrics=dict(self.validation_metrics),
        )

    def as_promoted(self) -> "CandidatePolicy":
        """Return the candidate marked as promoted (immutable transition)."""
        return replace(
            self,
            status="PROMOTED",
            promoted_at_utc=_utc_now_iso(),
        )

    def as_validated(self, metrics: Dict[str, float]) -> "CandidatePolicy":
        """Return the candidate marked as validated with metrics."""
        return replace(
            self,
            status="VALIDATED",
            validation_metrics=metrics,
            validated_at_utc=_utc_now_iso(),
        )

    def as_rejected(self, reason: str) -> "CandidatePolicy":
        """Return the candidate marked as rejected."""
        return replace(
            self,
            status="REJECTED",
            validation_metrics={**self.validation_metrics, "rejection_reason": reason},
        )


def _bump_version(version: str) -> str:
    """Increment the numeric tail of a policy version (``v1`` -> ``v2``)."""
    version = str(version or "v0")
    head = version
    tail = ""
    digits = version[::-1]
    count = 0
    for ch in digits:
        if ch.isdigit():
            count += 1
        else:
            break
    if count:
        head = version[:-count]
        tail = version[-count:]
        number = int(tail) + 1
    else:
        head = version + "-"
        number = 1
    return f"{head}{number}"


class PolicyManager:
    """Manages CurrentPolicy and CandidatePolicy lifecycle (OC-17).

    Promotion gate enforces ``INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT``:
    a candidate is only promoted when its validation metrics beat the current
    policy's baseline metrics; otherwise ``PolicyRejectionError`` is raised.
    """

    def __init__(self, policy_root: str = "data/learning/policies") -> None:
        self._policy_root = Path(policy_root)
        self._current: Optional[CurrentPolicy] = None
        self._candidates: Dict[str, CandidatePolicy] = {}

    # ------------------------------------------------------------------
    # Current policy
    # ------------------------------------------------------------------
    def load_current(self, version: Optional[str] = None) -> Optional[CurrentPolicy]:
        """Load current production policy from disk."""
        if version:
            path = self._policy_root / version / "policy.json"
        else:
            versions = sorted(
                d.name for d in self._policy_root.iterdir() if d.is_dir()
            )
            if not versions:
                return None
            path = self._policy_root / versions[-1] / "policy.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self._current = CurrentPolicy.from_dict(data)
        return self._current

    def save_current(self, policy: CurrentPolicy) -> Path:
        """Persist current policy."""
        version_dir = self._policy_root / policy.version
        version_dir.mkdir(parents=True, exist_ok=True)
        path = version_dir / "policy.json"
        path.write_text(json.dumps(policy.to_dict(), indent=2), encoding="utf-8")
        self._current = policy
        return path

    def current(self) -> Optional[CurrentPolicy]:
        return self._current

    def set_current(self, policy: CurrentPolicy) -> None:
        """Set the current policy in memory (no auto-promotion involved)."""
        self._current = policy

    # ------------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------------
    def create_candidate(
        self,
        base_version: str,
        proposed_changes: Dict[str, Any],
    ) -> CandidatePolicy:
        """Create a candidate policy from a base version."""
        if self._current is None or self._current.version != base_version:
            base_path = self._policy_root / base_version / "policy.json"
            if not base_path.exists():
                raise PolicyValidationError(
                    f"política base no disponible: {base_version}"
                )
            loaded = self.load_current(base_version)
            if loaded is None:
                raise PolicyValidationError(
                    f"política base no disponible: {base_version}"
                )
        candidate = CandidatePolicy(
            base_policy_version=base_version,
            proposed_changes=dict(proposed_changes),
        )
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def get_candidate(self, candidate_id: str) -> Optional[CandidatePolicy]:
        return self._candidates.get(candidate_id)

    def validate_candidate(
        self,
        candidate_id: str,
        dataset: FeedbackDataset,
    ) -> CandidatePolicy:
        """Run offline validation on a candidate; marks VALIDATED/REJECTED."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise PolicyValidationError(f"Candidate {candidate_id} not found")
        if candidate.status in ("PROMOTED",):
            raise PolicyValidationError("promoted candidates cannot be re-validated")
        if dataset.manifest.total_cases == 0:
            raise PolicyValidationError("cannot validate an empty dataset")
        metrics = candidate.validate(dataset)
        if metrics.get("total_records", 0) == 0:
            validated = candidate.as_rejected("empty_validation_records")
        else:
            validated = candidate.as_validated(metrics)
        self._candidates[candidate_id] = validated
        return validated

    def reject_candidate(self, candidate_id: str, reason: str) -> CandidatePolicy:
        """Explicitly reject a candidate (human decision)."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise PolicyValidationError(f"Candidate {candidate_id} not found")
        rejected = candidate.as_rejected(reason)
        self._candidates[candidate_id] = rejected
        return rejected

    # ------------------------------------------------------------------
    # Promotion gate
    # ------------------------------------------------------------------
    def promote_candidate(self, candidate_id: str) -> CurrentPolicy:
        """Promote a validated candidate to production.

        Promotion gate: only VALIDATED candidates may be promoted, and an
        inferior candidate must never replace the current policy
        (``INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT``).
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            raise PolicyValidationError(f"Candidate {candidate_id} not found")
        if candidate.status != "VALIDATED":
            raise PolicyValidationError(
                f"only validated candidates can be promoted (status={candidate.status})"
            )
        if self._current is None:
            raise PolicyValidationError("no current policy to base promotion on")
        if candidate.base_policy_version != self._current.version:
            raise PolicyValidationError(
                f"candidate base {candidate.base_policy_version} does not match "
                f"current {self._current.version}"
            )

        current_metrics = self._current.validation_metrics
        candidate_metrics = candidate.validation_metrics
        if current_metrics:
            self._assert_superior_or_equal(candidate_metrics, current_metrics)

        new_policy = candidate.apply_to_policy(self._current)
        self.save_current(new_policy)
        self._candidates[candidate_id] = candidate.as_promoted()
        return new_policy

    @staticmethod
    def _assert_superior_or_equal(
        candidate_metrics: Dict[str, float],
        current_metrics: Dict[str, float],
    ) -> None:
        """Raise PolicyRejectionError when the candidate is inferior.

        Compares the primary metric (f1_score), then precision/recall as
        tie-breakers. A candidate that only matches the current policy is
        accepted (equal is not strictly inferior); only strictly inferior
        metrics block promotion.
        """
        keys = ("f1_score", "precision", "recall")
        for key in keys:
            c_val = candidate_metrics.get(key)
            cur_val = current_metrics.get(key)
            if c_val is None or cur_val is None:
                continue
            if c_val < cur_val:
                raise PolicyRejectionError(
                    f"INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT: "
                    f"{key} candidate={c_val} < current={cur_val}"
                )