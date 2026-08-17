"""LOOP-0018Z validation adapter over the certified LOOP-0018Y harness."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
EVIDENCE = BASE / "evidence" / "loop_0018z"
sys.path.insert(0, str(BASE))

from src.evidence.persistent import PersistentEvidenceStore
from src.review import BoundedReviewExporter, record_from_signal


def load_parent():
    path = BASE / "evidence" / "loop_0018y" / "validate_real_behavior.py"
    spec = importlib.util.spec_from_file_location("loop_0018y_harness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.EVIDENCE = EVIDENCE
    return module


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def write_json(name: str, value: object) -> None:
    (EVIDENCE / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def human_review(records, evidence_store: PersistentEvidenceStore):
    choices = {
        "1": "USEFUL_SIGNAL",
        "2": "BENIGN_ACTIVITY",
        "3": "AMBIGUOUS",
        "4": "INSUFFICIENT_EVIDENCE",
        "5": "SYSTEM_ERROR",
    }
    reviewed = []
    print("\nHUMAN_REVIEW: 1=USEFUL 2=BENIGN 3=AMBIGUOUS 4=INSUFFICIENT_EVIDENCE 5=SYSTEM_ERROR")
    for index, record in enumerate(records, 1):
        existing = [ref for ref in record.evidence_refs if evidence_store.resolve(ref).is_file()]
        if existing:
            try:
                os.startfile(evidence_store.resolve(existing[-1]))
            except OSError:
                pass
        print(json.dumps({
            "index": index,
            "review_id": record.review_id,
            "camera_id": record.camera_id,
            "signal_type": record.signal_type,
            "rule_id": record.rule_id,
            "rule_score": record.rule_score,
            "evidence_available": bool(existing),
            "structured_explanation": record.structured_explanation,
        }, ensure_ascii=False, default=list))
        while True:
            answer = input(f"Clasificacion humana [{index}/{len(records)}] (1-5): ").strip()
            if answer in choices:
                break
            print("Entrada invalida; use 1, 2, 3, 4 o 5.")
        note = input("Nota breve opcional (sin datos personales): ").strip()
        reviewed.append(record.with_review(choices[answer], note))
    return tuple(reviewed)


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    config = json.loads((BASE / "config" / "default.json").read_text(encoding="utf-8"))
    frozen_keys = ("observation", "inference", "temporal", "correlation", "behavior", "evidence", "review_export")
    frozen = {key: config[key] for key in frozen_keys}
    baseline_hash = canonical_hash(frozen)
    write_json("validation_baseline.json", {
        "execution_id": "LOOP-0018Z",
        "frozen_blocks": frozen,
        "fingerprint_sha256": baseline_hash,
        "threshold_changes_during_validation": 0,
    })

    review_config = config["review_export"]
    exporter = BoundedReviewExporter(
        max_records_total=review_config["max_records_total"],
        max_records_per_camera=review_config["max_records_per_camera"],
        max_records_per_signal_type=review_config["max_records_per_signal_type"],
        max_records_per_rule=review_config["max_records_per_rule"],
        max_candidates=review_config["max_candidates"],
    )
    live_dataset = EVIDENCE / "signal_review_records.jsonl"
    state = {"stage": "", "started": 0.0, "duration": 0, "available": 0}
    parent = load_parent()
    original_run_stage = parent.run_stage
    original_feed = parent.AdvanceChain.feed

    def wrapped_run_stage(label, camera_count, duration, *args, **kwargs):
        state.update(stage=label, started=time.monotonic(), duration=duration)
        return original_run_stage(label, camera_count, duration, *args, **kwargs)

    def wrapped_feed(chain, camera_id, *args, **kwargs):
        result = original_feed(chain, camera_id, *args, **kwargs)
        behavior = result.get("behavior")
        if state["stage"] == "MAIN" and behavior is not None:
            state["available"] += len(behavior.signals)
            elapsed = time.monotonic() - state["started"]
            if elapsed >= state["duration"] - review_config["capture_window_seconds"]:
                track = result.get("track")
                correlation = result.get("correlation")
                trajectory = getattr(correlation, "trajectory", None)
                event = result.get("event")
                observation = result.get("observation")
                created_at = getattr(event, "timestamp", None) or getattr(observation, "timestamp", None) or ""
                for signal in behavior.signals:
                    exporter.offer(record_from_signal(
                        signal,
                        behavior.features,
                        created_at=created_at,
                        track_id=getattr(track, "track_id", None),
                        trajectory_id=getattr(trajectory, "trajectory_id", None),
                    ))
                    # Persist the bounded selected set immediately; do not
                    # wait for MAIN shutdown or evidence-retention cleanup.
                    exporter.export_jsonl(live_dataset)
        return result

    parent.run_stage = wrapped_run_stage
    parent.AdvanceChain.feed = wrapped_feed
    result = parent.main()
    if result != 0:
        return result

    if canonical_hash({key: config[key] for key in frozen_keys}) != baseline_hash:
        write_json("validation_status.json", {"status": "FROZEN_BASELINE_DIVERGENCE"})
        return 5

    records = exporter.select()
    evidence_store = PersistentEvidenceStore.from_config(config)
    assert evidence_store is not None
    broken = 0
    mismatches = 0
    evidence_index = []
    for record in records:
        for ref in record.evidence_refs:
            target = evidence_store.resolve(ref)
            if not target.is_file() or not target.with_name("metadata.json").is_file():
                broken += 1
                continue
            metadata = json.loads(target.with_name("metadata.json").read_text(encoding="utf-8"))
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != metadata.get("sha256"):
                mismatches += 1
            evidence_index.append({"review_id": record.review_id, "evidence_ref": ref,
                                   "sha256": actual, "verified": actual == metadata.get("sha256")})
    write_json("evidence_index.json", evidence_index)
    if broken or mismatches:
        write_json("validation_status.json", {"status": "EVIDENCE_TRACEABILITY_DIVERGENCE",
                                               "broken_evidence_refs": broken,
                                               "evidence_hash_mismatch": mismatches})
        return 6

    reviewed = human_review(records, evidence_store) if records else ()
    target = EVIDENCE / "signal_review_records.jsonl"
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for record in reviewed:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    with (EVIDENCE / "human_review_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("review_id", "signal_id", "camera_id", "signal_type",
                                                     "rule_id", "human_classification", "review_notes"))
        writer.writeheader()
        for record in reviewed:
            writer.writerow({key: record.to_dict()[key] for key in writer.fieldnames})
    counts = Counter(record.human_classification for record in reviewed)
    rule_counts = defaultdict(Counter)
    for record in reviewed:
        rule_counts[record.rule_id][record.human_classification] += 1
    stats = exporter.stats()
    stats.update({"available_signals": state["available"], "reviewed_signals": len(reviewed),
                  "classification_counts": dict(counts), "rule_classifications": {k: dict(v) for k, v in rule_counts.items()},
                  "broken_evidence_refs": broken, "evidence_hash_mismatch": mismatches,
                  "baseline_fingerprint": baseline_hash})
    write_json("review_metrics.json", stats)
    write_json("validation_status.json", {"status": "VALIDATION_AND_HUMAN_REVIEW_COMPLETED",
                                           "config_sha256": baseline_hash})
    print("VALIDATION_AND_HUMAN_REVIEW_COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
