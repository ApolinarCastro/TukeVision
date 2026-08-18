"""QW-04 validation adapter over the baseline four-camera behavior harness."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parents[2]
EVIDENCE = Path(os.environ.get(
    "TUKEVISION_EVIDENCE_ROOT",
    str(BASE / "evidence" / "loop_0019a_qw04_r2"),
))
MAX_CAPTURE_SECONDS = 300
sys.path.insert(0, str(BASE))

from scripts.run_multicamera import connection_host
from src.evidence.clips import (
    EvidenceClipAdapter,
    TemporalClipCoordinator,
    TemporalFrameBuffer,
)
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
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def bounded_parent_arguments() -> bool:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--stage-seconds", type=int)
    parser.add_argument("--main-seconds", type=int)
    known, _ = parser.parse_known_args()
    if known.stage_seconds is None:
        sys.argv.extend(("--stage-seconds", "10"))
    elif known.stage_seconds <= 0:
        return False
    if known.main_seconds is None:
        sys.argv.extend(("--main-seconds", str(MAX_CAPTURE_SECONDS)))
    elif known.main_seconds <= 0 or known.main_seconds > MAX_CAPTURE_SECONDS:
        return False
    return True


def install_fresh_credential_prompt(parent) -> None:
    """Patch only the old harness seam; never recover a historical username."""

    def fresh_connection_constants() -> tuple[str, str]:
        username = getpass.getpass(
            "Usuario RTSP autorizado (no se muestra ni persiste): "
        )
        return connection_host(), username

    parent.historical_connection_constants = fresh_connection_constants


def main() -> int:
    if not bounded_parent_arguments():
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        write_json("validation_status.json", {"status": "CAPTURE_BOUND_INVALID"})
        print("CAPTURE_BOUND_INVALID")
        return 2

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    config = json.loads((BASE / "config" / "default.json").read_text(encoding="utf-8"))
    frozen_keys = (
        "observation", "inference", "temporal", "correlation", "behavior",
        "evidence", "review_export", "clips",
    )
    frozen = {key: config[key] for key in frozen_keys}
    baseline_hash = canonical_hash(frozen)
    write_json("validation_baseline.json", {
        "execution_id": "LOOP-0019A-QW04-R2",
        "base_commit_expected": "04abddfc1b6c72a78a045e62049c0dbc936d88c8",
        "frozen_blocks": frozen,
        "fingerprint_sha256": baseline_hash,
        "threshold_changes_during_validation": 0,
        "max_capture_seconds": MAX_CAPTURE_SECONDS,
    })

    review_config = config["review_export"]
    clip_config = config["clips"]
    exporter = BoundedReviewExporter(
        max_records_total=review_config["max_records_total"],
        max_records_per_camera=review_config["max_records_per_camera"],
        max_records_per_signal_type=review_config["max_records_per_signal_type"],
        max_records_per_rule=review_config["max_records_per_rule"],
        max_candidates=review_config["max_candidates"],
    )
    live_dataset = EVIDENCE / "signal_review_records.jsonl"
    max_duration = float(clip_config["max_clip_duration_seconds"])
    clip_buffer = TemporalFrameBuffer(
        pre_roll_seconds=float(clip_config["pre_roll_seconds"]),
        retention_seconds=max_duration,
        max_frames_per_camera=int(clip_config["max_frames_per_camera"]),
        max_fps=float(clip_config["buffer_fps"]),
    )
    evidence_root = BASE / config["evidence"].get("root", "data/runtime_evidence")
    clip_adapter = EvidenceClipAdapter(
        evidence_root,
        max_clips_per_camera=int(clip_config["max_clips_per_camera"]),
        max_clip_duration_seconds=max_duration,
        frame_rate=float(clip_config["buffer_fps"]),
        container=clip_config["container"],
        codec=clip_config["codec"],
    )
    coordinator = TemporalClipCoordinator(
        clip_buffer,
        clip_adapter,
        pre_roll_seconds=float(clip_config["pre_roll_seconds"]),
        post_roll_seconds=float(clip_config["post_roll_seconds"]),
        max_pending_per_camera=int(clip_config["max_pending_per_camera"]),
    )
    state: dict[str, Any] = {
        "stage": "",
        "available_signals": 0,
        "clips_available": 0,
        "clips_unavailable": 0,
    }
    pending_records = {}
    parent = load_parent()
    install_fresh_credential_prompt(parent)
    original_run_stage = parent.run_stage
    original_feed = parent.AdvanceChain.feed

    def publish_clip(metadata: dict[str, Any]) -> None:
        record = pending_records.pop(metadata["signal_id"], None)
        if record is None:
            return
        available = metadata.get("availability") == "AVAILABLE"
        completed = replace(
            record,
            clip_evidence_ref=metadata.get("clip_evidence_ref"),
            clip_available=available,
            clip_sha256=metadata.get("sha256"),
            clip_duration_seconds=metadata.get("duration_seconds"),
        )
        exporter.offer(completed)
        exporter.export_jsonl(live_dataset)
        state["clips_available" if available else "clips_unavailable"] += 1

    def wrapped_run_stage(label, camera_count, duration, *args, **kwargs):
        state["stage"] = label
        if label == "MAIN":
            coordinator.clear()
            pending_records.clear()
        result = original_run_stage(label, camera_count, duration, *args, **kwargs)
        if label == "MAIN":
            for metadata in coordinator.flush():
                publish_clip(metadata)
            for signal_id, record in tuple(pending_records.items()):
                publish_clip(clip_adapter.unavailable(
                    camera_id=record.camera_id,
                    signal_id=signal_id,
                    start_timestamp=0,
                    end_timestamp=0,
                    reason="clip_finalize_incomplete",
                ))
            exporter.export_jsonl(live_dataset)
        return result

    def wrapped_feed(chain, camera_id, *args, **kwargs):
        frame_index = args[0] if args else kwargs.get("frame_index", -1)
        frame = args[2] if len(args) > 2 else kwargs.get("frame")
        now = time.monotonic()
        if state["stage"] == "MAIN":
            for metadata in coordinator.append(camera_id, now, frame, frame_index):
                publish_clip(metadata)
        result = original_feed(chain, camera_id, *args, **kwargs)
        behavior = result.get("behavior")
        if state["stage"] == "MAIN" and behavior is not None:
            state["available_signals"] += len(behavior.signals)
            track = result.get("track")
            correlation = result.get("correlation")
            trajectory = getattr(correlation, "trajectory", None)
            event = result.get("event")
            observation = result.get("observation")
            created_at = (
                getattr(event, "timestamp", None)
                or getattr(observation, "timestamp", None)
                or ""
            )
            for signal in behavior.signals:
                if signal.signal_id in pending_records:
                    continue
                record = record_from_signal(
                    signal,
                    behavior.features,
                    created_at=created_at,
                    track_id=getattr(track, "track_id", None),
                    trajectory_id=getattr(trajectory, "trajectory_id", None),
                )
                pending_records[signal.signal_id] = record
                if not clip_config.get("enabled", False):
                    publish_clip(clip_adapter.unavailable(
                        camera_id=camera_id,
                        signal_id=signal.signal_id,
                        start_timestamp=now,
                        end_timestamp=now,
                        reason="clip_disabled",
                    ))
                elif not coordinator.request(camera_id, signal.signal_id, now):
                    publish_clip(clip_adapter.unavailable(
                        camera_id=camera_id,
                        signal_id=signal.signal_id,
                        start_timestamp=now,
                        end_timestamp=now,
                        reason="pending_clip_bound_reached",
                    ))
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
    exporter.export_jsonl(live_dataset)
    evidence_store = PersistentEvidenceStore.from_config(config)
    assert evidence_store is not None
    broken_static = 0
    static_mismatches = 0
    broken_clips = 0
    clip_mismatches = 0
    evidence_index = []
    clip_index = []
    for record in records:
        for reference in record.evidence_refs:
            target = evidence_store.resolve(reference)
            if not target.is_file() or not target.with_name("metadata.json").is_file():
                broken_static += 1
                continue
            metadata = json.loads(
                target.with_name("metadata.json").read_text(encoding="utf-8")
            )
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            verified = actual == metadata.get("sha256")
            static_mismatches += int(not verified)
            evidence_index.append({
                "review_id": record.review_id,
                "evidence_ref": reference,
                "sha256": actual,
                "verified": verified,
            })
        if record.clip_available and record.clip_evidence_ref:
            clip_metadata = {
                "availability": "AVAILABLE",
                "clip_evidence_ref": record.clip_evidence_ref,
                "sha256": record.clip_sha256,
            }
            target = evidence_root / record.clip_evidence_ref
            sidecar = target.with_suffix(".json")
            verified = EvidenceClipAdapter.verify(clip_metadata, evidence_root)
            linkage = False
            if sidecar.is_file():
                stored = json.loads(sidecar.read_text(encoding="utf-8"))
                linkage = (
                    stored.get("signal_id") == record.signal_id
                    and stored.get("camera_id") == record.camera_id
                )
            broken_clips += int(not target.is_file() or not sidecar.is_file())
            clip_mismatches += int(not verified or not linkage)
            clip_index.append({
                "review_id": record.review_id,
                "signal_id": record.signal_id,
                "camera_id": record.camera_id,
                "clip_evidence_ref": record.clip_evidence_ref,
                "sha256": record.clip_sha256,
                "verified": verified,
                "signal_camera_linkage": linkage,
            })
    write_json("evidence_index.json", evidence_index)
    write_json("clip_index.json", clip_index)
    if broken_static or static_mismatches or broken_clips or clip_mismatches:
        write_json("validation_status.json", {
            "status": "EVIDENCE_TRACEABILITY_DIVERGENCE",
            "broken_evidence_refs": broken_static,
            "evidence_hash_mismatch": static_mismatches,
            "broken_clip_refs": broken_clips,
            "clip_hash_or_linkage_mismatch": clip_mismatches,
        })
        return 6

    stats = exporter.stats()
    stats.update({
        "available_signals": state["available_signals"],
        "review_records": len(records),
        "temporal_clips": len(clip_index),
        "clip_fallbacks": state["clips_unavailable"],
        "baseline_fingerprint": baseline_hash,
        "operator_verification": "PENDING",
    })
    write_json("review_metrics.json", stats)
    if state["available_signals"] and not clip_index:
        write_json("validation_status.json", {
            "status": "SIGNALS_WITHOUT_TEMPORAL_CLIPS",
            "available_signals": state["available_signals"],
        })
        print("SIGNALS_WITHOUT_TEMPORAL_CLIPS")
        return 7
    if not records:
        write_json("validation_status.json", {"status": "NO_REAL_BEHAVIOR_SIGNALS"})
        print("NO_REAL_BEHAVIOR_SIGNALS")
        return 8

    write_json("validation_status.json", {
        "status": "OPERATOR_VERIFICATION_PENDING",
        "real_signals_captured": len(records),
        "real_clips_created": len(clip_index),
        "signal_clip_linkage_verified": len(clip_index),
        "config_sha256": baseline_hash,
    })
    print("OPERATOR_VERIFICATION_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
