"""Validation-only LOOP-0018Y harness; product code/config remain immutable."""

from __future__ import annotations

import argparse
import ast
import csv
import getpass
import hashlib
import json
import os
import sys
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]
EVIDENCE = BASE / "evidence" / "loop_0018y"
sys.path.insert(0, str(BASE))

import psutil  # existing transitive runtime dependency; no installation

from src.app.advance_chain import AdvanceChain
from src.capture.source_manager import CameraDescriptor, SourceManager
from src.capture.live_sources import RTSPSource
from src.capture.rtsp_url import build_rtsp_url

CHANNELS = (7, 1, 5, 3)
CAMERA_IDS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")


def historical_connection_constants() -> tuple[str, str]:
    """Read non-secret host/user from the prior authorized harness without copying them."""
    path = BASE / "evidence" / "loop_0018o" / "validate_multicamera4.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {"HOST", "USER"} and isinstance(node.value, ast.Constant):
                values[node.targets[0].id] = str(node.value.value)
    if set(values) != {"HOST", "USER"}:
        raise RuntimeError("Historical non-secret connection metadata unavailable")
    return values["HOST"], values["USER"]


def write_json(name: str, value: Any) -> None:
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def probe(password: str, host: str, user: str) -> bool:
    source = RTSPSource(
        rtsp_url=build_rtsp_url(host, user, password, channel=CHANNELS[0], subtype=0),
        max_width=640, max_reconnect_attempts=0, rtsp_open_timeout_ms=8000,
        frame_stall_timeout_s=5.0,
    )
    try:
        source.open()
        for _ in source.frames():
            return True
        return False
    except Exception:
        return False
    finally:
        source.close()


def make_manager(count: int, password: str, host: str, user: str) -> SourceManager:
    manager = SourceManager()
    for index in range(count):
        channel = CHANNELS[index]
        manager.register_source(CameraDescriptor(
            camera_id=CAMERA_IDS[index], host=host, channel=channel,
            subtype=0 if channel == 7 else 1, username=user, password=password,
            max_width=640, rtsp_open_timeout_ms=8000, frame_stall_timeout_s=10.0,
        ))
    return manager


def safe_result(result: dict[str, Any]) -> dict[str, Any]:
    behavior = result.get("behavior")
    correlation = result.get("correlation")
    track = result.get("track")
    activity = result.get("temporal_activity")
    event = result.get("event")
    observation = result.get("observation")
    risk = getattr(behavior, "risk_event", None)
    return {
        "timestamp": getattr(event, "timestamp", None) or getattr(observation, "timestamp", None),
        "camera_id": result.get("camera_id"),
        "observation_id": getattr(observation, "observation_id", None),
        "event_id": getattr(event, "event_id", None),
        "track_id": getattr(track, "track_id", None),
        "activity_id": getattr(activity, "activity_id", None),
        "trajectory_id": getattr(getattr(correlation, "trajectory", None), "trajectory_id", None),
        "behavior": behavior.to_dict() if behavior is not None else None,
        "risk_event_id": getattr(risk, "risk_event_id", None),
    }


def run_stage(label: str, camera_count: int, duration: int, password: str,
              host: str, user: str, config: dict[str, Any], metrics_writer,
              events_handle) -> dict[str, Any]:
    manager = make_manager(camera_count, password, host, user)
    chain = AdvanceChain.build(deepcopy(config), manager)
    camera_ids = CAMERA_IDS[:camera_count]
    chain.register_from_source_manager()
    for camera_id in camera_ids:
        manager.start(camera_id)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if all(manager.health(cid).healthy and manager.health(cid).readable_frames > 0 for cid in camera_ids):
            break
        time.sleep(1)
    if not all(manager.health(cid).healthy for cid in camera_ids):
        manager.close_all()
        chain.close()
        return {"label": label, "camera_count": camera_count, "status": "SOURCE_UNAVAILABLE"}

    process = psutil.Process(os.getpid())
    process.cpu_percent(None)
    started = time.monotonic()
    last_sample = 0.0
    last_frames: dict[str, int] = {}
    counts = Counter()
    tracks: set[str] = set()
    activities: set[str] = set()
    trajectories: set[str] = set()
    risks: set[str] = set()
    camera_risks = Counter()
    errors: list[dict[str, str]] = []
    resource_rows = []
    try:
        while time.monotonic() - started < duration:
            active = False
            for camera_id in camera_ids:
                try:
                    snapshot = manager.snapshot(camera_id)
                    if not snapshot:
                        continue
                    index = int(snapshot["frame_index"])
                    if index <= last_frames.get(camera_id, -1):
                        continue
                    last_frames[camera_id] = index
                    active = True
                    result = chain.feed(camera_id, index, float(snapshot.get("fps", 0.0) or 0.0),
                                        snapshot["frame"], metadata={"source_state": snapshot.get("state", "OPEN"),
                                                                    "resolution": snapshot.get("resolution", "")})
                    counts["processed_results"] += 1
                    for key in ("observation", "event", "track", "temporal_activity"):
                        if result.get(key) is not None:
                            counts[key] += 1
                    if result.get("track") is not None:
                        tracks.add(result["track"].track_id)
                    if result.get("temporal_activity") is not None:
                        activities.add(result["temporal_activity"].activity_id)
                    correlation = result.get("correlation")
                    trajectory = getattr(correlation, "trajectory", None)
                    if trajectory is not None:
                        trajectories.add(trajectory.trajectory_id)
                    behavior = result.get("behavior")
                    if behavior is not None:
                        counts["behavior_features"] += len(behavior.features)
                        counts["behavior_signals"] += len(behavior.signals)
                        if behavior.risk_event is not None:
                            risk_id = behavior.risk_event.risk_event_id
                            if risk_id not in risks:
                                risks.add(risk_id)
                                camera_risks[camera_id] += 1
                                events_handle.write(json.dumps(safe_result(result), ensure_ascii=False, sort_keys=True) + "\n")
                                events_handle.flush()
                except Exception as exc:
                    counts["errors"] += 1
                    errors.append({"camera_id": camera_id, "error_type": type(exc).__name__})
            elapsed = time.monotonic() - started
            if elapsed - last_sample >= 5.0:
                last_sample = elapsed
                summary = chain.summary()
                health = {cid: manager.health(cid) for cid in camera_ids}
                row = {
                    "stage": label, "elapsed_seconds": round(elapsed, 3), "camera_id": "ALL",
                    "frames_received": sum(item.readable_frames for item in health.values()),
                    "frames_selected": counts["observation"],
                    "inferences": summary["inference"]["totals"]["processed"],
                    "detections": counts["event"], "events": counts["event"],
                    "active_tracks": max(0, summary["temporal"]["tracks_started"] - summary["temporal"]["tracks_ended"]),
                    "completed_tracks": summary["temporal"]["tracks_ended"],
                    "temporal_activities": len(activities),
                    "trajectory_candidates": summary["correlation"]["candidate_count"],
                    "trajectories": len(trajectories),
                    "behavior_features": counts["behavior_features"],
                    "behavior_signals": counts["behavior_signals"], "risk_events": len(risks),
                    "evidence_written": counts["observation"],
                    "queue_depths": sum(item.queue_depth for item in health.values()),
                    "cpu_percent": process.cpu_percent(None),
                    "ram_mb": round(process.memory_info().rss / 1048576, 3),
                    "threads": process.num_threads(), "errors": counts["errors"],
                    "stalls": sum(item.stall_count for item in health.values()),
                    "healthy_cameras": sum(1 for item in health.values() if item.healthy),
                }
                resource_rows.append(row)
                metrics_writer.writerow(row)
            if not active:
                time.sleep(0.01)
    finally:
        summary = chain.summary()
        final_health = {cid: {"healthy": manager.health(cid).healthy,
                              "readable_frames": manager.health(cid).readable_frames,
                              "stall_count": manager.health(cid).stall_count,
                              "last_error": bool(manager.health(cid).last_error)} for cid in camera_ids}
        chain.close()
        manager.close_all()

    return {
        "label": label, "camera_count": camera_count, "duration_seconds": duration,
        "status": "COMPLETED", "counts": dict(counts), "unique_tracks": len(tracks),
        "unique_activities": len(activities), "unique_trajectories": len(trajectories),
        "unique_risk_events": len(risks), "events_per_camera": dict(camera_risks),
        "errors": errors, "final_health": final_health, "chain_summary": summary,
        "resource_samples": resource_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-seconds", type=int, default=30)
    parser.add_argument("--main-seconds", type=int, default=1800)
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    config = json.loads((BASE / "config" / "default.json").read_text(encoding="utf-8"))
    host, user = historical_connection_constants()
    password = getpass.getpass("Credencial RTSP autorizada (no se muestra ni persiste): ")
    if not password or not probe(password, host, user):
        write_json("validation_status.json", {"status": "AUTHORIZED_SOURCE_UNAVAILABLE"})
        print("AUTHORIZED_SOURCE_UNAVAILABLE")
        return 3

    fields = ["stage", "elapsed_seconds", "camera_id", "frames_received", "frames_selected",
              "inferences", "detections", "events", "active_tracks", "completed_tracks",
              "temporal_activities", "trajectory_candidates", "trajectories", "behavior_features",
              "behavior_signals", "risk_events", "evidence_written", "queue_depths", "cpu_percent",
              "ram_mb", "threads", "errors", "stalls", "healthy_cameras"]
    stages = []
    with (EVIDENCE / "runtime_metrics.csv").open("w", newline="", encoding="utf-8") as metrics_handle, \
         (EVIDENCE / "behavior_events.jsonl").open("w", encoding="utf-8") as events_handle:
        writer = csv.DictWriter(metrics_handle, fieldnames=fields)
        writer.writeheader()
        for label, count, seconds in (("STAGE_A", 1, args.stage_seconds),
                                      ("STAGE_B", 2, args.stage_seconds),
                                      ("STAGE_C", 4, args.stage_seconds),
                                      ("MAIN", 4, args.main_seconds)):
            print(f"{label}: {count} camera(s), {seconds}s")
            result = run_stage(label, count, seconds, password, host, user, config, writer, events_handle)
            stages.append(result)
            write_json("stage_results.json", stages)
            if result["status"] != "COMPLETED":
                write_json("validation_status.json", {"status": "AUTHORIZED_SOURCE_UNAVAILABLE", "stage": label})
                print("AUTHORIZED_SOURCE_UNAVAILABLE")
                return 4
    write_json("validation_status.json", {"status": "VALIDATION_WINDOW_COMPLETED",
                                           "config_sha256": hashlib.sha256((BASE / "config" / "default.json").read_bytes()).hexdigest().upper()})
    print("VALIDATION_WINDOW_COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
