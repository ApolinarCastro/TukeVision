"""Resumable local operator review for QW-00 JSONL records."""
from __future__ import annotations
import csv, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
EVIDENCE = BASE / "evidence" / "loop_0018z"
ALLOWED = {"1":"USEFUL_SIGNAL", "2":"BENIGN_ACTIVITY", "3":"AMBIGUOUS", "4":"INSUFFICIENT_EVIDENCE", "5":"SYSTEM_ERROR"}
FIELDS = ("review_id", "signal_id", "camera_id", "track_id", "classification", "review_timestamp", "evidence_ref")

def dataset_path():
    for name in ("signal_review_records.jsonl", "signal_review_export.jsonl"):
        path = EVIDENCE / name
        if path.is_file() and path.stat().st_size:
            return path
    return None

def load_existing(path):
    if not path.is_file(): return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["review_id"]: row for row in csv.DictReader(handle) if row.get("review_id") and row.get("classification")}

def save(path, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)

def main():
    source = dataset_path()
    if source is None:
        print("REVIEW_DATA_NOT_READY")
        return 2
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    matrix = EVIDENCE / "human_review_matrix.csv"
    existing = load_existing(matrix)
    rows = [existing[r["review_id"]] for r in records if r.get("review_id") in existing]
    done = set(existing)
    pending = [r for r in records if r.get("review_id") not in done]
    print(f"QW-00 review dataset: {len(records)} records; already reviewed: {len(rows)}")
    for index, record in enumerate(pending, len(rows) + 1):
        print(json.dumps({k: record.get(k) for k in ("review_id","signal_id","camera_id","track_id","signal_type","rule_id","rule_score","timestamp_start","timestamp_end","evidence_refs","structured_explanation")}, ensure_ascii=False, default=list))
        while True:
            choice = input(f"[{index}/{len(records)}] 1 useful, 2 benign, 3 ambiguous, 4 insufficient, 5 system, S skip, Q save: ").strip().upper()
            if choice == "Q":
                save(matrix, rows); print("REVIEW_SAVED_AND_EXIT"); return 0
            if choice == "S":
                break
            if choice in ALLOWED:
                rows.append({"review_id": record.get("review_id", ""), "signal_id": record.get("signal_id", ""),
                             "camera_id": record.get("camera_id", ""), "track_id": record.get("track_id", ""),
                             "classification": ALLOWED[choice], "review_timestamp": datetime.now(timezone.utc).isoformat(),
                             "evidence_ref": (record.get("evidence_refs") or [""])[-1]})
                break
            print("Entrada inválida")
    save(matrix, rows)
    print(f"REVIEW_COMPLETED {len(rows)}/{len(records)}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
