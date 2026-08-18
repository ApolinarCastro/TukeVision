"""Resumable local operator review for QW-00 static and temporal evidence."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional


BASE = Path(__file__).resolve().parents[1]
RUNTIME_EVIDENCE = BASE / "data" / "runtime_evidence"
DEFAULT_EVIDENCE = BASE / "evidence" / "loop_0019a_qw04_r2"
EVIDENCE = DEFAULT_EVIDENCE
ALLOWED = {
    "1": "USEFUL_SIGNAL",
    "2": "BENIGN_ACTIVITY",
    "3": "AMBIGUOUS",
    "4": "INSUFFICIENT_EVIDENCE",
    "5": "SYSTEM_ERROR",
}
FIELDS = (
    "review_id",
    "signal_id",
    "camera_id",
    "track_id",
    "classification",
    "review_timestamp",
    "evidence_ref",
    "clip_evidence_ref",
    "clip_sha256",
    "static_evidence_sufficient",
    "temporal_evidence_sufficient",
    "comparison_notes",
)


def evidence_directories() -> tuple[Path, ...]:
    explicit = os.environ.get("TUKEVISION_REVIEW_ROOT", "").strip()
    if not explicit and Path(EVIDENCE).resolve() != DEFAULT_EVIDENCE.resolve():
        return (Path(EVIDENCE).resolve(),)
    values = []
    if explicit:
        values.append(Path(explicit))
    values.extend((
        EVIDENCE,
        BASE / "evidence" / "loop_0019a" / "real_run",
        BASE / "evidence" / "loop_0018z",
    ))
    return tuple(dict.fromkeys(path.resolve() for path in values))


def dataset_path(search_roots: Optional[Iterable[Path]] = None) -> Optional[Path]:
    roots = evidence_directories() if search_roots is None else tuple(search_roots)
    for root in roots:
        for name in ("signal_review_records.jsonl", "signal_review_export.jsonl"):
            path = Path(root) / name
            if path.is_file() and path.stat().st_size:
                return path
    return None


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        records = {}
        for source in csv.DictReader(handle):
            if source.get("review_id") and source.get("classification"):
                records[source["review_id"]] = {
                    field: source.get(field, "") for field in FIELDS
                }
        return records


def save(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in FIELDS})
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_metrics(path: Path, rows: Iterable[dict[str, str]]) -> dict:
    rows = tuple(rows)
    static_counts = Counter(row.get("static_evidence_sufficient", "") for row in rows)
    temporal_counts = Counter(row.get("temporal_evidence_sufficient", "") for row in rows)
    metrics = {
        "reviewed_records": len(rows),
        "classification_counts": dict(Counter(row.get("classification", "") for row in rows)),
        "static_evidence_sufficiency": dict(static_counts),
        "temporal_evidence_sufficiency": dict(temporal_counts),
        "human_review_evidence_sufficiency_measured": bool(rows),
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }
    target = path.parent / "operator_review_metrics.json"
    handle, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(metrics, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return metrics


def resolve_evidence(reference: str, root: Path = RUNTIME_EVIDENCE) -> Optional[Path]:
    if not reference:
        return None
    root = Path(root).resolve()
    candidate = (root / reference).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def open_evidence(
    reference: str,
    *,
    root: Path = RUNTIME_EVIDENCE,
    opener: Optional[Callable[[str], object]] = None,
) -> bool:
    path = resolve_evidence(reference, root)
    if path is None:
        return False
    selected_opener = opener or getattr(os, "startfile", None)
    if selected_opener is None:
        return False
    try:
        selected_opener(str(path))
        return True
    except OSError:
        return False


def prompt_sufficiency(label: str) -> str:
    while True:
        answer = input(f"{label} suficiente? Y=si, N=no, U=incierto: ").strip().upper()
        if answer in {"Y", "N", "U"}:
            return {"Y": "YES", "N": "NO", "U": "UNCERTAIN"}[answer]
        print("Entrada inválida")


def persist_review(matrix: Path, rows: list[dict[str, str]]) -> None:
    save(matrix, rows)
    write_metrics(matrix, rows)


def main() -> int:
    source = dataset_path()
    if source is None:
        print("REVIEW_DATA_NOT_READY")
        return 2
    records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matrix = source.parent / "human_review_matrix.csv"
    existing = load_existing(matrix)
    rows = [existing[record["review_id"]] for record in records if record.get("review_id") in existing]
    done = set(existing)
    pending = [record for record in records if record.get("review_id") not in done]
    print(f"QW-00 review dataset: {len(records)} records; already reviewed: {len(rows)}")
    print("Comandos: J abrir JPEG, C abrir clip, S omitir, Q guardar/salir, 1-5 clasificar")
    for index, record in enumerate(pending, len(rows) + 1):
        fields = (
            "review_id", "signal_id", "camera_id", "track_id", "signal_type",
            "rule_id", "rule_score", "timestamp_start", "timestamp_end",
            "evidence_refs", "evidence_available", "clip_evidence_ref",
            "clip_available", "clip_sha256", "clip_duration_seconds",
            "structured_explanation",
        )
        print(json.dumps(
            {key: record.get(key) for key in fields},
            ensure_ascii=False,
            default=list,
        ))
        static_reference = (record.get("evidence_refs") or [""])[-1]
        clip_reference = record.get("clip_evidence_ref") or ""
        while True:
            choice = input(
                f"[{index}/{len(records)}] J JPEG, C clip, 1 useful, 2 benign, "
                "3 ambiguous, 4 insufficient, 5 system, S skip, Q save: "
            ).strip().upper()
            if choice == "Q":
                persist_review(matrix, rows)
                print("REVIEW_SAVED_AND_EXIT")
                return 0
            if choice == "S":
                break
            if choice == "J":
                print("OPEN_STATIC_OK" if open_evidence(static_reference) else "OPEN_STATIC_UNAVAILABLE")
                continue
            if choice == "C":
                print("OPEN_CLIP_OK" if open_evidence(clip_reference) else "OPEN_CLIP_UNAVAILABLE")
                continue
            if choice in ALLOWED:
                static_sufficient = (
                    prompt_sufficiency("Evidencia estática")
                    if resolve_evidence(static_reference) else "NOT_AVAILABLE"
                )
                temporal_sufficient = (
                    prompt_sufficiency("Evidencia temporal")
                    if record.get("clip_available") and resolve_evidence(clip_reference)
                    else "NOT_AVAILABLE"
                )
                notes = input("Comparación JPEG vs clip (opcional, sin datos personales): ").strip()
                rows.append({
                    "review_id": record.get("review_id", ""),
                    "signal_id": record.get("signal_id", ""),
                    "camera_id": record.get("camera_id", ""),
                    "track_id": record.get("track_id", ""),
                    "classification": ALLOWED[choice],
                    "review_timestamp": datetime.now(timezone.utc).isoformat(),
                    "evidence_ref": static_reference,
                    "clip_evidence_ref": clip_reference,
                    "clip_sha256": record.get("clip_sha256", ""),
                    "static_evidence_sufficient": static_sufficient,
                    "temporal_evidence_sufficient": temporal_sufficient,
                    "comparison_notes": notes,
                })
                break
            print("Entrada inválida")
    persist_review(matrix, rows)
    print(f"REVIEW_COMPLETED {len(rows)}/{len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
