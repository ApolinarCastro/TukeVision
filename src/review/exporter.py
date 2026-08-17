"""Deterministic, memory-bounded JSONL signal review exporter."""

import json
import os
import tempfile
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Tuple

from .contracts import SignalReviewRecord


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
            os.replace(temporary_name, target)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
        return self.stats()
