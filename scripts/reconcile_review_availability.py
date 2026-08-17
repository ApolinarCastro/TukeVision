"""Mark unavailable bounded-retention evidence explicitly in QW-00 JSONL."""
import json, os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "data" / "runtime_evidence"
TARGET = BASE / "evidence" / "loop_0018z" / "signal_review_records.jsonl"
rows = []
for line in TARGET.read_text(encoding="utf-8").splitlines():
    if not line.strip(): continue
    row = json.loads(line)
    row["evidence_available"] = all((ROOT / ref.replace("/", "\\")).is_file() for ref in row.get("evidence_refs", []))
    rows.append(row)
tmp = TARGET.with_suffix(".jsonl.tmp")
with tmp.open("w", encoding="utf-8", newline="\n") as handle:
    for row in rows:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    handle.flush(); os.fsync(handle.fileno())
os.replace(tmp, TARGET)
print(f"RECONCILED_RECORDS={len(rows)}")
