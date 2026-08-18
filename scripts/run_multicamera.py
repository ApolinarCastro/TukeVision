"""BASE multicamera operator entrypoint; capture remains in SourceManager."""
from __future__ import annotations
import ast
import getpass
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.app.operational_pipeline import OperationalPipeline
from src.app.runtime_qw04 import RuntimeQw04Integration
from src.capture.source_manager import CameraDescriptor, SourceManager
from src.observability.logging_setup import new_run_id, setup_logging
from src.observability.runtime_trace import BoundedRuntimeTrace
from src.ui.controller import UiController
from src.ui.tk_view import TkApp

CHANNELS = (7, 1, 5, 3)
CAMERAS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")
QW04_REVIEW_TARGET = BASE / "evidence/loop_0019a_qw04_r2/signal_review_records.jsonl"


def camera_subtype(channel):
    """Use the same authorized main stream for a coherent four-camera view."""
    if channel not in CHANNELS:
        raise ValueError(f"unsupported authorized channel: {channel}")
    return 0


def build_panel_snapshot(source_snapshot, result):
    """Adapt one canonical AdvanceChain result without inventing values."""
    event = result.get("event")
    track = result.get("track")
    activity = result.get("temporal_activity")
    behavior_result = result.get("behavior")
    evidence = result.get("evidence")

    detections = None
    if event is not None:
        value = (getattr(event, "metadata", None) or {}).get("detections")
        detections = int(value) if value is not None else None
    metadata = (getattr(event, "metadata", None) or {}) if event else {}
    bboxes = tuple(
        tuple(item) for item in metadata.get("bboxes", ())
        if isinstance(item, (list, tuple)) and len(item) >= 5
    )

    temporal = None
    if activity is not None:
        temporal = "{} {} {:.1f}s".format(
            getattr(activity, "activity_type", "ACTIVITY"),
            getattr(activity, "status", ""),
            float(getattr(activity, "duration_ms", 0) or 0) / 1000.0,
        ).strip()

    behavior = None
    risk = None
    if behavior_result is not None:
        signals = tuple(getattr(behavior_result, "signals", ()) or ())
        if signals:
            behavior = ", ".join(str(item.signal_type) for item in signals)
        risk_event = getattr(behavior_result, "risk_event", None)
        if risk_event is not None:
            risk = "{} {:g}".format(
                getattr(risk_event, "risk_event_type", "RISK"),
                float(getattr(risk_event, "risk_score", 0) or 0),
            )

    return SimpleNamespace(
        frame_index=int(source_snapshot.get("frame_index", -1)),
        frame=source_snapshot.get("frame"),
        source_state=source_snapshot.get("state", "OPEN"),
        fps=float(source_snapshot.get("fps", 0.0) or 0.0),
        detections=detections,
        track_id=getattr(track, "track_id", None),
        track_status=getattr(track, "status", None),
        track_bbox=getattr(track, "last_bbox", None),
        bboxes=bboxes if event is not None else None,
        event_id=getattr(event, "event_id", None),
        event_type=getattr(event, "event_type", None),
        event_confidence=getattr(event, "confidence", None),
        inference_ref=getattr(event, "inference_ref", None),
        temporal=temporal,
        behavior=behavior,
        risk=risk,
        evidence=(evidence or {}).get("relative_path") if evidence else None,
        resolution=str(source_snapshot.get("resolution", "") or ""),
    )

def connection_host():
    """Load only authorized, non-secret endpoint metadata."""
    tree = ast.parse((BASE / "evidence/loop_0018o/validate_multicamera4.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "HOST" and isinstance(node.value, ast.Constant):
                return str(node.value.value)
    raise RuntimeError("Authorized non-secret endpoint metadata unavailable")


def prompt_connection_credentials():
    """Request fresh credentials locally without echoing or persistence."""
    username = getpass.getpass("Usuario RTSP autorizado (no se muestra ni persiste): ")
    password = getpass.getpass("Credencial RTSP autorizada (no se muestra ni persiste): ")
    return username, password

class MulticameraRuntime:
    def __init__(self, config, password, host, user):
        self._stop = threading.Event()
        self._controller = UiController(config=config)
        self.is_multicamera = True
        self.evidence_root = str((BASE / config.get("evidence", {}).get(
            "root", "data/runtime_evidence"
        )).resolve())
        self._trace = BoundedRuntimeTrace(CAMERAS)
        self._manager = SourceManager()
        for camera_id, channel in zip(CAMERAS, CHANNELS):
            self._manager.register_source(CameraDescriptor(
                camera_id=camera_id, host=host, channel=channel,
                subtype=camera_subtype(channel), username=user, password=password,
                max_width=int(config.get("video", {}).get("max_width", 640)),
                rtsp_open_timeout_ms=int(config.get("rtsp", {}).get("open_timeout_ms", 8000)),
                frame_stall_timeout_s=float(config.get("rtsp", {}).get("frame_stall_timeout_s", 10.0))))
        self._pipeline = OperationalPipeline(config, self._manager)
        self.review_target = QW04_REVIEW_TARGET
        self._qw04 = RuntimeQw04Integration.from_config(
            config,
            evidence_root=Path(self.evidence_root),
            review_target=QW04_REVIEW_TARGET,
        )
        self._thread = threading.Thread(target=self._run, name="tukevision-multicamera-pipeline", daemon=True)
    def start(self): self._thread.start()
    def _handle_pipeline_result(self, camera_id, snapshot, result):
        frame_index = int(snapshot.get("frame_index", -1))
        self._trace.observe_pipeline_result(camera_id, frame_index, result)
        timestamp = snapshot.get("timestamp")
        if timestamp is not None:
            self._qw04.ingest(
                camera_id,
                float(timestamp),
                snapshot.get("frame"),
                frame_index,
                result,
            )
        self._controller.ingest_camera_snapshot(
            camera_id, build_panel_snapshot(snapshot, result)
        )
        self._trace.mark_ui_model_received(camera_id, frame_index)
    def _run(self):
        def on_result(camera_id, snapshot, result):
            self._handle_pipeline_result(camera_id, snapshot, result)
        self._pipeline.run(self._stop.is_set, on_result)
    def poll_multicamera(self): return self._controller.poll_multicamera()
    def mark_ui_rendered(self, camera_id, frame_index):
        self._trace.mark_ui_rendered(camera_id, frame_index)
    def poll_state(self):
        running = not self._stop.is_set() and self._thread.is_alive()
        panels = self._controller.poll_multicamera()
        tracks = [panel.track_id for panel in panels.values() if panel.track_id]
        risks = [panel.risk for panel in panels.values() if panel.risk]
        evidence = [panel.evidence for panel in panels.values() if panel.evidence]
        fps_values = [panel.fps for panel in panels.values() if panel.fps]
        resolutions = [panel.resolution for panel in panels.values() if panel.resolution]
        qw04 = self._qw04.summary()
        return {"status": "RUNNING" if running else "STOPPED", "source_path_display": "MULTICAMERA",
                "source_kind": "MULTICAMERA", "source_state": "OPEN" if running else "CLOSED",
                "resolution": resolutions[0] if resolutions else "-",
                "fps": sum(fps_values) / len(fps_values) if fps_values else 0.0,
                "zone_id": "", "zone_name": "", "followed_track": tracks[-1] if tracks else None,
                "permanence_seconds": 0.0, "risk_text": risks[-1] if risks else "",
                "latest_risk_score": None, "alert_log": [], "evidence_paths": evidence[-8:],
                "clips_available": int(qw04.get("clips_available", 0) or 0),
                "error": "", "final_status": "STOPPED" if not running else ""}
    def _resolve_artifact(self, ref):
        """Absolute path of an evidence/clip artifact under evidence_root."""
        if not ref:
            return None
        root = Path(self.evidence_root).resolve()
        if Path(str(ref)).is_absolute():
            candidate = Path(str(ref)).resolve()
        else:
            candidate = (root / str(ref)).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                return None
        return str(candidate) if candidate.is_file() else None

    def _review_records(self):
        target = Path(self.review_target)
        if not target.is_file():
            return ()
        records = []
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
        return tuple(records)

    def latest_evidence(self):
        """Exact JPEG of the most recent evidence artifact, or None."""
        selected = None
        for panel in self._controller.poll_multicamera().values():
            ref = str(getattr(panel, "evidence", "") or "")
            if not ref:
                continue
            candidate = self._resolve_artifact(ref)
            if candidate is None:
                continue
            frame_index = int(getattr(panel, "frame_index", -1))
            if selected is None or frame_index >= selected[0]:
                selected = (frame_index, candidate)
        return selected[1] if selected else None

    def clip_target(self):
        """Exact MP4 of the selected review case, or None when unavailable."""
        records = self._review_records()
        if not records:
            return None
        record = records[-1]
        if not record.get("clip_available"):
            return None
        return self._resolve_artifact(record.get("clip_evidence_ref"))

    def review_available(self):
        """True when a QW-00 review case exists (with or without clip)."""
        return bool(self._review_records())

    def launch_review(self):
        """Open the human review console for the resolvable QW-00 case."""
        bat = BASE / "review_behavior_signals.bat"
        if bat.is_file():
            os.startfile(str(bat))

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=15)
        if not self._thread.is_alive():
            self._qw04.close()
    def close(self):
        self.stop()
        self._trace.export(BASE / "evidence/loop_0019a_r2/runtime_trace.json")

def main():
    setup_logging(run_id=new_run_id())
    config = json.loads((BASE / "config/default.json").read_text(encoding="utf-8"))
    host = connection_host()
    user, password = prompt_connection_credentials()
    if not user or not password:
        print("AUTHORIZED_SOURCE_UNAVAILABLE")
        return 3
    runtime = MulticameraRuntime(config, password, host, user)
    runtime.start()
    root = tk.Tk()
    try:
        TkApp(root, runtime).run()
    finally:
        runtime.close()
    return 0

if __name__ == "__main__": raise SystemExit(main())
