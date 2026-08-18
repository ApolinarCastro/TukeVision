"""Controlled, CCTV-free operator fixture for LOOP-0020 retention review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import numpy as np

from src.evidence.clips import BufferedFrame, EvidenceClipAdapter
from src.evidence.persistent import PersistentEvidenceStore
from src.review.exporter import load_review_retention_state


ROOT = BASE / "data" / "runtime_evidence"
FIXTURE = ROOT / "_loop_0020_operator_review"
DATASET = FIXTURE / "signal_review_records.jsonl"
STATE = FIXTURE / "fixture_state.json"
CAMERA = "LOOP-0020-CAM-001"
FRAME = np.full((96, 96, 3), 127, dtype=np.uint8)


def _clip_frames(value: int) -> tuple[BufferedFrame, ...]:
    frame = np.full((96, 96, 3), value, dtype=np.uint8)
    return tuple(BufferedFrame(index / 5, frame, index) for index in range(6))


def _fixture_paths() -> tuple[Path, Path, Path]:
    return FIXTURE, ROOT / CAMERA, ROOT / "clips" / CAMERA


def _reset_fixture() -> None:
    root = ROOT.resolve()
    for path in _fixture_paths():
        resolved = path.resolve()
        resolved.relative_to(root)
        if resolved.name not in {FIXTURE.name, CAMERA}:
            raise RuntimeError("unsafe fixture path")
        if resolved.is_dir():
            shutil.rmtree(resolved)


def _write_dataset(row: dict) -> None:
    FIXTURE.mkdir(parents=True, exist_ok=True)
    DATASET.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")


def prepare() -> int:
    _reset_fixture()
    ids = iter(("EVD-LOOP0020-A", "EVD-LOOP0020-B", "EVD-LOOP0020-C"))
    store = PersistentEvidenceStore(
        str(ROOT), 2, id_factory=lambda: next(ids), review_target=DATASET
    )
    clips = EvidenceClipAdapter(
        ROOT, max_clips_per_camera=2, frame_rate=5, review_target=DATASET
    )
    static_a = store.persist_selected(
        FRAME, camera_id=CAMERA, timestamp="1", producer="loop-0020-fixture"
    )
    clip_a = clips.create_clip(
        camera_id=CAMERA,
        signal_id="BS-LOOP0020-A",
        start_timestamp=0,
        end_timestamp=1,
        frames=_clip_frames(1),
    )
    if static_a is None or clip_a.get("availability") != "AVAILABLE":
        raise RuntimeError("fixture evidence creation failed")
    row = {
        "review_id": "SRR-LOOP0020-A",
        "signal_id": "BS-LOOP0020-A",
        "camera_id": CAMERA,
        "track_id": "TRK-LOOP0020-A",
        "signal_type": "CONTROLLED_RETENTION_FIXTURE",
        "rule_id": "LOOP-0020",
        "rule_score": 1.0,
        "human_classification": "NOT_REVIEWED",
        "review_state": "PENDING",
        "evidence_refs": [static_a["relative_path"]],
        "evidence_available": True,
        "clip_evidence_ref": clip_a["clip_evidence_ref"],
        "clip_available": True,
        "clip_sha256": clip_a["sha256"],
        "clip_duration_seconds": clip_a["duration_seconds"],
        "structured_explanation": "Caso sintético controlado; sin CCTV.",
    }
    _write_dataset(row)
    static_path = store.resolve(static_a["relative_path"])
    clip_path = ROOT / clip_a["clip_evidence_ref"]
    os.utime(static_path.parent, (1, 1))
    os.utime(clip_path, (1, 1))

    for suffix, value in (("B", 2), ("C", 3)):
        store.persist_selected(
            FRAME,
            camera_id=CAMERA,
            timestamp=str(value),
            producer="loop-0020-fixture",
        )
        clips.create_clip(
            camera_id=CAMERA,
            signal_id=f"BS-LOOP0020-{suffix}",
            start_timestamp=0,
            end_timestamp=1,
            frames=_clip_frames(value),
        )

    required = (
        static_path,
        static_path.with_name("metadata.json"),
        clip_path,
        clip_path.with_suffix(".json"),
    )
    if not all(path.is_file() for path in required):
        raise RuntimeError("pending evidence was evicted")
    STATE.write_text(
        json.dumps(
            {
                "static_ref": static_a["relative_path"],
                "clip_ref": clip_a["clip_evidence_ref"],
                "clip_sha256": hashlib.sha256(clip_path.read_bytes()).hexdigest(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print("PENDING_CASE_PREPARED=PASS")
    print("RETENTION_PRESSURE_BEFORE_REVIEW=PASS")
    print("JPEG_STILL_ACCESSIBLE=PASS")
    print("CLIP_STILL_ACCESSIBLE=PASS")
    print(f"REVIEW_DATASET={DATASET}")
    return 0


def verify_release() -> int:
    if not STATE.is_file():
        print("OPERATOR_FIXTURE_NOT_PREPARED")
        return 2
    state = json.loads(STATE.read_text(encoding="utf-8"))
    protection = load_review_retention_state(DATASET)
    if protection.protects_static(state["static_ref"]):
        print("OPERATOR_REVIEW=PENDING")
        print("PROTECTION_RELEASED=NO")
        return 3

    store = PersistentEvidenceStore(
        str(ROOT),
        2,
        id_factory=lambda: "EVD-LOOP0020-D",
        review_target=DATASET,
    )
    clips = EvidenceClipAdapter(
        ROOT, max_clips_per_camera=2, frame_rate=5, review_target=DATASET
    )
    store.persist_selected(
        FRAME, camera_id=CAMERA, timestamp="4", producer="loop-0020-fixture"
    )
    clips.create_clip(
        camera_id=CAMERA,
        signal_id="BS-LOOP0020-D",
        start_timestamp=0,
        end_timestamp=1,
        frames=_clip_frames(4),
    )
    static_path = ROOT / state["static_ref"]
    clip_path = ROOT / state["clip_ref"]
    if any(
        path.exists()
        for path in (
            static_path,
            static_path.with_name("metadata.json"),
            clip_path,
            clip_path.with_suffix(".json"),
        )
    ):
        raise RuntimeError("reviewed evidence did not return to normal retention")
    print("OPERATOR_REVIEW=COMPLETED")
    print("PROTECTION_RELEASED=PASS")
    print("NORMAL_RETENTION_RESTORED=PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "verify-release"))
    args = parser.parse_args()
    return prepare() if args.action == "prepare" else verify_release()


if __name__ == "__main__":
    raise SystemExit(main())
