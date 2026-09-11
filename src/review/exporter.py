"""Deterministic, memory-bounded JSONL signal review exporter.

The selected JSONL and its human-review matrix are also the durable source of
truth used by evidence retention.  Keeping that reader here avoids a second
review-state store and makes pending protection reconstructible after restart.
"""

import csv
import json
import os
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Dict, FrozenSet, List, Optional, Tuple

from .contracts import SignalReviewRecord


RETENTION_OK = "RETENTION_OK"
RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS = (
    "RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS"
)


def _safe_reference(value: object) -> Optional[str]:
    if value is None:
        return None
    reference = PurePosixPath(str(value).replace("\\", "/"))
    if not reference.parts or reference.is_absolute() or ".." in reference.parts:
        return None
    return reference.as_posix()


@dataclass(frozen=True)
class ReviewRetentionState:
    """Persistent pending-review references relevant to bounded retention."""

    review_ids: FrozenSet[str] = frozenset()
    signal_ids: FrozenSet[str] = frozenset()
    static_refs: FrozenSet[str] = frozenset()
    clip_refs: FrozenSet[str] = frozenset()
    indeterminate: bool = False

    def protects_static(self, reference: str) -> bool:
        normalized = _safe_reference(reference)
        return self.indeterminate or (
            normalized is not None and normalized in self.static_refs
        )

    def protects_clip(self, reference: str, signal_id: str = "") -> bool:
        normalized = _safe_reference(reference)
        return self.indeterminate or (
            normalized is not None and normalized in self.clip_refs
        ) or (bool(signal_id) and str(signal_id) in self.signal_ids)


def load_review_retention_state(
    review_target: str | Path | None,
) -> ReviewRetentionState:
    """Load pending/selected review protection without keeping runtime locks.

    A row in the selected dataset remains protected until the adjacent official
    human-review matrix contains a completed classification for the same review
    or signal.  A malformed state is treated conservatively: callers must not
    evict evidence while the durable review contract is indeterminate.
    """
    if review_target is None:
        return ReviewRetentionState()
    target = Path(review_target)
    if not target.is_file():
        return ReviewRetentionState()

    completed_reviews: set[str] = set()
    completed_signals: set[str] = set()
    matrix = target.parent / "human_review_matrix.csv"
    if matrix.is_file():
        try:
            with matrix.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    classification = str(row.get("classification") or "").strip().upper()
                    if classification and classification != "NOT_REVIEWED":
                        completed_reviews.add(str(row.get("review_id") or ""))
                        completed_signals.add(str(row.get("signal_id") or ""))
        except (OSError, csv.Error, UnicodeError):
            return ReviewRetentionState(indeterminate=True)

    review_ids: set[str] = set()
    signal_ids: set[str] = set()
    static_refs: set[str] = set()
    clip_refs: set[str] = set()
    indeterminate = False
    try:
        with target.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (TypeError, ValueError):
                    indeterminate = True
                    continue
                if not isinstance(row, dict):
                    indeterminate = True
                    continue
                review_id = str(row.get("review_id") or "")
                signal_id = str(row.get("signal_id") or "")
                classification = str(
                    row.get("human_classification") or ""
                ).strip().upper()
                review_state = str(row.get("review_state") or "").strip().upper()
                if (
                    review_id in completed_reviews
                    or signal_id in completed_signals
                    or classification not in {"", "NOT_REVIEWED"}
                    or review_state in {"REVIEWED", "COMPLETED", "CLOSED", "RELEASED"}
                ):
                    continue
                if review_id:
                    review_ids.add(review_id)
                if signal_id:
                    signal_ids.add(signal_id)
                references = row.get("evidence_refs") or ()
                if not isinstance(references, (list, tuple)):
                    references = (references,)
                references = tuple(references) + (
                    row.get("static_evidence_ref"),
                    row.get("evidence_ref"),
                )
                for value in references:
                    reference = _safe_reference(value)
                    if reference:
                        static_refs.add(reference)
                clip_reference = _safe_reference(row.get("clip_evidence_ref"))
                if clip_reference:
                    clip_refs.add(clip_reference)
    except (OSError, UnicodeError):
        return ReviewRetentionState(indeterminate=True)

    return ReviewRetentionState(
        review_ids=frozenset(review_ids),
        signal_ids=frozenset(signal_ids),
        static_refs=frozenset(static_refs),
        clip_refs=frozenset(clip_refs),
        indeterminate=indeterminate,
    )


class BoundedReviewExporter:
    def __init__(
        self,
        *,
        max_records_total: int = 8,
        max_records_per_camera: int = 2,
        max_records_per_signal_type: int = 4,
        max_records_per_rule: int = 4,
        max_candidates: int = 64,
    ) -> None:
        bounds = (
            max_records_total,
            max_records_per_camera,
            max_records_per_signal_type,
            max_records_per_rule,
            max_candidates,
        )
        if any(value < 1 for value in bounds):
            raise ValueError("all review export bounds must be positive")
        if max_candidates < max_records_total:
            raise ValueError("max_candidates must cover max_records_total")
        self.max_records_total = max_records_total
        self.max_records_per_camera = max_records_per_camera
        self.max_records_per_signal_type = max_records_per_signal_type
        self.max_records_per_rule = max_records_per_rule
        self.max_candidates = max_candidates
        self._candidates: Dict[str, SignalReviewRecord] = {}
        self._seen = set()
        self._available = 0
        self._duplicates = 0

    @staticmethod
    def _priority(record: SignalReviewRecord) -> Tuple[str, str]:
        value = sha256(f"bounded-review-v1\0{record.review_id}".encode("utf-8")).hexdigest()
        return value, record.review_id

    def offer(self, record: SignalReviewRecord) -> bool:
        if record.signal_id in self._seen:
            self._duplicates += 1
            return False
        self._seen.add(record.signal_id)
        self._available += 1
        self._candidates[record.review_id] = record
        if len(self._candidates) > self.max_candidates:
            evicted = max(self._candidates.values(), key=self._priority)
            del self._candidates[evicted.review_id]
        return record.review_id in self._candidates

    def candidates(self) -> Tuple[SignalReviewRecord, ...]:
        return tuple(sorted(self._candidates.values(), key=self._priority))

    def select(self) -> Tuple[SignalReviewRecord, ...]:
        groups = defaultdict(list)
        for record in self._candidates.values():
            groups[(record.camera_id, record.signal_type, record.rule_id)].append(record)
        for records in groups.values():
            records.sort(key=self._priority)

        selected: List[SignalReviewRecord] = []
        camera_counts: Counter = Counter()
        type_counts: Counter = Counter()
        rule_counts: Counter = Counter()
        keys = sorted(groups)
        progressed = True
        while len(selected) < self.max_records_total and progressed:
            progressed = False
            for key in keys:
                records = groups[key]
                while records:
                    record = records.pop(0)
                    if camera_counts[record.camera_id] >= self.max_records_per_camera:
                        continue
                    if type_counts[record.signal_type] >= self.max_records_per_signal_type:
                        continue
                    if rule_counts[record.rule_id] >= self.max_records_per_rule:
                        continue
                    selected.append(record)
                    camera_counts[record.camera_id] += 1
                    type_counts[record.signal_type] += 1
                    rule_counts[record.rule_id] += 1
                    progressed = True
                    break
                if len(selected) >= self.max_records_total:
                    break
        return tuple(selected)

    def stats(self) -> dict:
        selected = self.select()
        return {
            "total_available": self._available,
            "retained_candidates": len(self._candidates),
            "selected": len(selected),
            "excluded": max(0, self._available - len(selected)),
            "duplicates": self._duplicates,
            "per_camera": dict(Counter(item.camera_id for item in selected)),
            "per_signal_type": dict(Counter(item.signal_type for item in selected)),
            "per_rule": dict(Counter(item.rule_id for item in selected)),
        }

    def export_jsonl(self, target: Path) -> dict:
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                for record in self.select():
                    stream.write(json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":")))
                    stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            last_exc = None
            for attempt in range(5):
                try:
                    os.replace(temporary_name, target)
                    last_exc = None
                    break
                except (PermissionError, OSError) as exc:
                    last_exc = exc
                    time.sleep(0.02 * (2 ** attempt))
            if last_exc:
                raise last_exc
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
        return self.stats()
