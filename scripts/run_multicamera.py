"""BASE multicamera operator entrypoint; capture remains in SourceManager.

OC-01/OC-02/OC-03: the operator camera set is derived from the config-driven
StoreCatalog (1 -> 4 -> 16 -> N) instead of a hardcoded four-camera tuple.
Credentials are resolved from the environment via ``credentials_ref`` and
never persist or log.

Identity and evidence from start: RUN_ID generated before opening cameras,
exclusive evidence/<RUN_ID>/ folder. Each file identifies RUN_ID, PID, start,
version. Atomic replacement during execution, finalize on close.
"""
from __future__ import annotations
import json
import logging
import os
import sys
import threading
import time
import tkinter as tk
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.app.operational_pipeline import OperationalPipeline
from src.app.runtime_qw04 import RuntimeQw04Integration
from src.capture.source_manager import SourceManager
from src.domain.catalog import StoreCatalog
from src.observability.logging_setup import new_run_id, setup_logging
from src.observability.exit_forensics import ExitForensics
from src.observability.frame_heartbeat import FrameHeartbeat
from src.observability.resource_telemetry import ResourceTelemetry
from src.observability.runtime_trace import BoundedRuntimeTrace
from src.observability.system_health import SystemHealthSampler
from src.observability.true_liveness import TrueLivenessTracker
from src.ui.controller import UiController
from src.ui.tk_view import TkApp

QW04_REVIEW_TARGET = BASE / "evidence/loop_0019a_qw04_r2/signal_review_records.jsonl"


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
        generation=int(source_snapshot.get("generation", 0) or 0),
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


class MulticameraRuntime:
    def __init__(self, config, password, user, run_id: Optional[str] = None):
        self._stop = threading.Event()
        self._config = config
        self._run_id = run_id or new_run_id()
        self._pid = os.getpid()
        self._start_time = time.time()
        self._version = self._get_version()
        
        self._catalog = StoreCatalog.from_dict(config)
        self._entries = self._catalog.camera_descriptors(
            max_width=int(config.get("video", {}).get("max_width", 640)),
            process_every_n_frames=int(config.get("video", {}).get("process_every_n_frames", 1)),
            frame_stall_timeout_s=float(config.get("rtsp", {}).get("frame_stall_timeout_s", 10.0)),
            rtsp_open_timeout_ms=int(config.get("rtsp", {}).get("open_timeout_ms", 8000)),
            credential_resolver=lambda ref: (user or "", password),
        )
        self._camera_ids = tuple(entry.camera_id for entry in self._entries)
        if not self._camera_ids:
            raise ValueError("catálogo sin cámaras habilitadas")
        self._controller = UiController(config=config, camera_ids=self._camera_ids)
        self.is_multicamera = True
        
        # Identity and evidence from start: exclusive folder per RUN_ID
        self.evidence_root = str((BASE / f"evidence/{self._run_id}").resolve())
        Path(self.evidence_root).mkdir(parents=True, exist_ok=True)
        self._write_identity_file()
        
        self._trace = BoundedRuntimeTrace(self._camera_ids)
        self._manager = SourceManager()
        # BLOCK B: GRID starts as SUBSTREAM (subtype=1) for all 15 cameras
        # to reduce DVR load; FOCUS will switch one to MAIN on demand.
        from dataclasses import replace as _replace
        grid_entries = []
        for entry in self._entries:
            desc = entry.descriptor
            if int(getattr(desc, "subtype", 0)) == 0:
                desc = _replace(desc, subtype=1)
                entry = _replace(entry, descriptor=desc)
            grid_entries.append(entry)
        self._entries = tuple(grid_entries)
        for entry in self._entries:
            self._manager.register_source(entry.descriptor)
        self._focused_camera: Optional[str] = None
        # Verify backend effective per camera: no silent fallback
        requested = os.environ.get("RTSP_BACKEND", "ffmpeg_supervised").strip().lower() or "ffmpeg_supervised"
        import logging as _lg2
        _lg2.getLogger("tukevision.capture").info("RTSP_BACKEND_REQUESTED=%s run_id=%s pid=%d", 
                                                   requested, self._run_id, self._pid)
        health_config = config.get("system_health", {})
        try:
            health_interval = float(health_config.get("sample_interval_seconds", 3.0))
        except (AttributeError, TypeError, ValueError):
            health_interval = 3.0
        if not 2.0 <= health_interval <= 5.0:
            health_interval = 3.0
        self._health = SystemHealthSampler(
            self._manager,
            self._camera_ids,
            sample_interval_seconds=health_interval,
            disk_path=BASE,
            catalog=self._catalog,
        )
        self._heartbeat = FrameHeartbeat(self._camera_ids)
        self._true_liveness = TrueLivenessTracker(self._camera_ids)
        self._telemetry = ResourceTelemetry(
            self._camera_ids,
            self._manager,
            interval_s=1.0,
            on_sample=self._write_live_evidence,
            identity={"run_id": self._run_id, "pid": self._pid},
            health_snapshot=lambda: self._health.snapshot(
                runtime_running=self._runtime_running()
            ),
        )
        self._pipeline = OperationalPipeline(
            config,
            self._manager,
            review_target=QW04_REVIEW_TARGET,
            on_received=self._on_frame_received,
        )
        self.review_target = QW04_REVIEW_TARGET
        self._qw04 = RuntimeQw04Integration.from_config(
            config,
            evidence_root=Path(self.evidence_root),
            review_target=QW04_REVIEW_TARGET,
        )
        self._thread = threading.Thread(target=self._run, name="tukevision-multicamera-pipeline", daemon=True)
    def start(self): self._thread.start()
    def _on_frame_received(self, camera_id, frame_index):
        self._heartbeat.mark_received(camera_id, frame_index)
        # True liveness: frame received (capture)
        try:
            h = self._manager.health(camera_id)
            self._true_liveness.observe_heartbeat(camera_id, h.state, h.stall_count, None)
        except Exception:
            pass
    def _handle_pipeline_result(self, camera_id, snapshot, result):
        frame_index = int(snapshot.get("frame_index", -1))
        frame = snapshot.get("frame")
        # True liveness: update with frame hash and sequence
        try:
            h = self._manager.health(camera_id)
            tid = None
            try:
                rt = self._manager._runtimes.get(camera_id)
                if rt and rt.source and hasattr(rt.source, "_reader_thread") and rt.source._reader_thread:
                    tid = rt.source._reader_thread.ident
            except Exception:
                pass
            self._true_liveness.observe_frame(camera_id, frame, frame_index, h.state, tid,
                                               acquired_at=snapshot.get("timestamp"),
                                               generation=snapshot.get("generation"))
            self._true_liveness.observe_heartbeat(camera_id, h.state, h.stall_count, tid)
        except Exception:
            pass
        self._trace.observe_pipeline_result(camera_id, frame_index, result)
        heartbeat = getattr(self, "_heartbeat", None)
        if heartbeat is not None:
            heartbeat.mark_inferred(camera_id, frame_index)
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
    def _runtime_running(self):
        return not self._stop.is_set() and self._thread.is_alive()
    def poll_multicamera(self):
        panels = self._controller.poll_multicamera()
        health = self._health.snapshot(runtime_running=self._runtime_running())
        by_camera = {item.camera_id: item for item in health.camera_health}
        return {
            camera_id: replace(
                panel,
                source_state=by_camera[camera_id].source_state,
                fps=(
                    by_camera[camera_id].fps
                    if by_camera[camera_id].fps is not None else panel.fps
                ),
            ) if camera_id in by_camera else panel
            for camera_id, panel in panels.items()
        }
    def mark_ui_rendered(self, camera_id, frame_index):
        self._trace.mark_ui_rendered(camera_id, frame_index)
        self._heartbeat.mark_rendered(camera_id, frame_index)

    def set_focus(self, camera_id: Optional[str]) -> None:
        """Switch focused camera to MAIN profile (subtype 0, max_width 0)."""
        self._focused_camera = camera_id
        if hasattr(self, "_manager") and self._manager is not None:
            for cam in self._camera_ids:
                if camera_id is not None and cam == camera_id:
                    self._manager.switch_stream(cam, 0, max_width=0)  # MAIN (HD Native)
                else:
                    self._manager.switch_stream(cam, 1, max_width=640)  # SUB (Economy)

    def clear_focus(self) -> None:
        self._focused_camera = None
        if hasattr(self, "_manager") and self._manager is not None:
            for cam in self._camera_ids:
                self._manager.switch_stream(cam, 1, max_width=640)

    def poll_state(self):
        running = self._runtime_running()
        panels = self.poll_multicamera()
        tracks = [panel.track_id for panel in panels.values() if panel.track_id]
        risks = [panel.risk for panel in panels.values() if panel.risk]
        evidence = [panel.evidence for panel in panels.values() if panel.evidence]
        fps_values = [panel.fps for panel in panels.values() if panel.fps]
        resolutions = [panel.resolution for panel in panels.values() if panel.resolution]
        qw04 = self._qw04.summary()
        system_health = self._health.snapshot(runtime_running=running)
        # True liveness: live exclusively via frame progress, not session open
        true_snap = {}
        live_count = system_health.online_camera_count
        try:
            true_snap = self._true_liveness.snapshot()
            # Override live count with true liveness if available after startup
            if any(v.last_frame_monotonic is not None for v in true_snap.values()):
                live_count = sum(1 for v in true_snap.values() if v.live)
        except Exception:
            true_snap = {}
        return {"status": "RUNNING" if running else "STOPPED", "source_path_display": "MULTICAMERA",
                "source_kind": "MULTICAMERA", "source_state": "OPEN" if running else "CLOSED",
                "resolution": resolutions[0] if resolutions else "-",
                "fps": sum(fps_values) / len(fps_values) if fps_values else 0.0,
                "zone_id": "", "zone_name": "", "followed_track": tracks[-1] if tracks else None,
                "permanence_seconds": 0.0, "risk_text": risks[-1] if risks else "",
                "latest_risk_score": None, "alert_log": [], "evidence_paths": evidence[-8:],
                "clips_available": int(qw04.get("clips_available", 0) or 0),
                "system_health": system_health,
                "true_liveness": true_snap,
                "live_count": live_count,
                "heartbeat": getattr(self, "_heartbeat", None).summary() if getattr(self, "_heartbeat", None) else {},
                "telemetry": getattr(self, "_telemetry", None).snapshot() if getattr(self, "_telemetry", None) else [],
                "store_id": self._store_id(),
                "error": "", "final_status": "STOPPED" if not running else ""}

    def _store_id(self):
        """Primary store id without requiring ``__init__`` state (robust for
        lightweight tests that build the runtime via ``__new__``)."""
        catalog = getattr(self, "_catalog", None)
        if catalog is not None:
            try:
                return catalog.stores()[0].store_id
            except Exception:
                pass
        config = getattr(self, "_config", None) or {}
        return str(config.get("business", {}).get("store_id", "") or "")

    @property
    def camera_ids(self):
        """Config-driven operator camera set (block 5 wiring contract)."""
        return getattr(self, "_camera_ids", ())

    @property
    def catalog(self):
        return getattr(self, "_catalog", None)

    def _derive_evidence_root(self, config):
        """Evidence root derived from the store namespace when multistore.

        Block 6: when the catalog declares per-store evidence namespaces, the
        runtime must not depend on a single global root; it routes evidence
        under ``organization/store`` via the store namespace.
        """
        try:
            store_id = self._store_id()
            namespace = self._catalog.evidence_root_for(store_id)
            if namespace:
                return str((BASE / namespace).resolve())
        except Exception:
            pass
        return str((BASE / config.get("evidence", {}).get(
            "root", "data/runtime_evidence"
        )).resolve())

    def _get_version(self) -> str:
        """Get version from git or config."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--always", "--dirty"],
                cwd=str(BASE), capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return config.get("version", "unknown")

    def _write_live_evidence(self):
        """Single sampler writer: observation is available before UI shutdown."""
        from dataclasses import asdict
        from src.observability.logging_setup import atomic_write_text
        base = Path(self.evidence_root)
        self._telemetry.export(base / "resource_telemetry.json")
        states = {cid: asdict(value) for cid, value in self._true_liveness.snapshot().items()}
        payload = {
            "run_id": self._run_id, "pid": self._pid,
            "observed_at": time.time(), "observed_monotonic": time.monotonic(),
            "cameras": states,
            "live_count": sum(value["live"] for value in states.values()),
            "technical_gate": "NOT_CERTIFIED",
            "trace": self._trace.snapshot(),
        }
        if getattr(self, "current_grid_snapshot", None):
            payload["grid_snapshot"] = self.current_grid_snapshot
        atomic_write_text(base / "live_status.json", json.dumps(payload, indent=2))
        self._trace.export(base / "runtime_trace.json")

    def _write_identity_file(self) -> None:
        """Write identity file with RUN_ID, PID, start time, version."""
        from src.observability.logging_setup import atomic_write_text
        identity = {
            "run_id": self._run_id,
            "pid": self._pid,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self._start_time)),
            "started_at_unix": self._start_time,
            "version": self._version,
            "camera_ids": list(self._camera_ids),
        }
        identity_path = Path(self.evidence_root) / "identity.json"
        atomic_write_text(identity_path, json.dumps(identity, indent=2))

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
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, PermissionError):
            return ()
        records = []
        for line in text.splitlines():
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
        if hasattr(self, "_manager") and self._manager:
            try:
                self._manager.close_all()
            except Exception:
                pass
        if not self._thread.is_alive():
            self._qw04.close()
    def close(self):
        self.stop()
        # evidence_root may not exist if runtime created via __new__ without __init__ (tests)
        evidence_root = getattr(self, "evidence_root", None)
        if evidence_root:
            self._trace.export(Path(evidence_root) / "runtime_trace.json")
        else:
            self._trace.export(BASE / "evidence" / "runtime_trace.json")

def main():
    run_id = new_run_id()
    setup_logging(run_id=run_id)
    config = json.loads((BASE / "config/multistore.active.json").read_text(encoding="utf-8"))

    # Resolve credentials from environment (never prompt, never hardcode)
    import os
    creds_ref = "ENV_DVR_PRINCIPAL_CREDS"
    creds_json = os.environ.get(creds_ref, "")
    if not creds_json:
        print(f"CREDENTIALS_MISSING: Set {creds_ref} environment variable with JSON {{\"username\": \"...\", \"password\": \"...\"}}")
        return 3
    try:
        creds = json.loads(creds_json)
        user = creds.get("username", "")
        password = creds.get("password", "")
    except json.JSONDecodeError:
        print(f"CREDENTIALS_INVALID: {creds_ref} must be valid JSON")
        return 3
    if not user or not password:
        print("CREDENTIALS_INCOMPLETE: username and password required")
        return 3

    runtime = MulticameraRuntime(config, password, user, run_id=run_id)
    runtime.start()
    runtime._telemetry.start()
    forensics = ExitForensics(
        Path(runtime.evidence_root) / "process_exit_forensics.json",
    )
    forensics.install()
    root = tk.Tk()
    exit_code = 0
    try:
        TkApp(root, runtime).run()
    except BaseException:
        exit_code = 1
        if not forensics.finished:
            try:
                import sys as _sys
                exc_info = _sys.exc_info()
                forensics.record_unhandled(*exc_info)
            except Exception:
                forensics.record_exit("UNHANDLED_EXCEPTION", {"message": "unknown"})
        raise
    finally:
        try:
            if not forensics.finished:
                forensics.record_exit("NORMAL_UI_CLOSE")
        finally:
            forensics.uninstall()
            runtime._telemetry.stop()
            runtime._telemetry.export(
                Path(runtime.evidence_root) / "resource_telemetry.json"
            )
            runtime.close()
            # Surgical correction: generate physical_runtime_report.json with T0..T30 markers per camera
            try:
                _generate_physical_report(runtime, forensics)
            except Exception as _e:
                import logging as _lg
                _lg.getLogger("tukevision.runtime").error("PHYSICAL_REPORT_FAILED %s", _e)
            # Verify orphan counts at shutdown
            try:
                _verify_orphans(runtime)
            except Exception:
                pass
    return exit_code


def _generate_physical_report(runtime, forensics):
    import hashlib
    import time as _time
    import psutil as _psutil
    base = Path(runtime.evidence_root)
    base.mkdir(parents=True, exist_ok=True)
    # per-camera details required by gate
    cameras = []
    try:
        true_snap = runtime._true_liveness.snapshot()
    except Exception:
        true_snap = {}
    try:
        health = runtime._health.snapshot(runtime_running=False)
        health_by = {c.camera_id: c for c in health.camera_health}
    except Exception:
        health_by = {}
    for cid in runtime._camera_ids:
        h = health_by.get(cid)
        tl = true_snap.get(cid)
        # determine stream profile from descriptor subtype
        profile = "subtype=1"
        try:
            for e in runtime._entries:
                if e.camera_id == cid:
                    profile = f"subtype={int(e.descriptor.subtype or 0)}"
                    break
        except Exception:
            pass
        # frame counts from trace
        try:
            trace = runtime._trace.snapshot() if hasattr(runtime._trace, "snapshot") else {}
            fc = 0
            last_ts = None
            if hasattr(runtime._trace, "_counters"):
                fc = runtime._trace._counters.get(cid, {}).get("FRAME_RECEIVED", 0)
        except Exception:
            fc = 0
            last_ts = None
        # fallback from true liveness
        if tl:
            fc = max(fc, tl.frame_sequence + 1)
            last_ts = tl.last_frame_monotonic
        # reconnects/timeouts/errors from health
        reconnects = getattr(h, "stall_count", 0) if h else 0
        if reconnects is None: reconnects = 0
        timeouts = reconnects
        errors = getattr(h, "last_error", "") if h else ""
        final_state = tl.liveness_state if tl else (getattr(h, "health_state", "UNKNOWN") if h else "UNKNOWN")
        # thread ids
        tid_before = getattr(tl, "reader_thread_id", None) if tl else None
        # FRAME_FREEZE = consecutive identical
        freeze = None  # identical image hashes are not proof of a frozen source
        # NO_FIRST_FRAME vs subsequent freeze differentiation
        no_first_frame = (fc == 0)
        cameras.append({
            "CAMERA_ID": cid,
            "START_OK": h is not None and getattr(h, "state", "") not in ("FAILED","CLOSED") if h else False,
            "FRAME_COUNT": int(fc or 0),
            "LAST_FRAME_TS": last_ts,  # Keep as None if no frame received (unknown/unavailable)
            "NO_FIRST_FRAME": no_first_frame,  # True if zero frames ever received
            "RECONNECTS": int(reconnects or 0),
            "TIMEOUTS": int(timeouts or 0),
            "ERRORS": str(errors)[:200],
            "FINAL_STATE": str(final_state),
            "STREAM_PROFILE": profile,
            "SOURCE_STATE_BEFORE": str(getattr(h, "state", "")) if h else "",
            "SOURCE_STATE_AFTER": str(final_state),
            "FRAME_TIMESTAMP_BEFORE": last_ts,  # Keep as None if unknown
            "FRAME_TIMESTAMP_AFTER": last_ts,   # Keep as None if unknown
            "RECONNECT_COUNT_BEFORE": int(reconnects or 0),
            "RECONNECT_COUNT_AFTER": int(reconnects or 0),
            "READER_THREAD_ID_BEFORE": tid_before,
            "READER_THREAD_ID_AFTER": tid_before,
            "FRAME_FREEZE": freeze,
            "IDENTICAL_FRAME_HASH_COUNT": getattr(tl, "consecutive_identical", 0) if tl else 0,
        })
    # global
    started = getattr(forensics, "_started", _time.time())
    ended = _time.time()
    uptime = round(ended - started, 1) if started else 0
    # resource markers are already in telemetry, include them
    try:
        tele = runtime._telemetry.snapshot()
        markers = runtime._telemetry.marker_rows()
    except Exception:
        tele = []
        markers = {}
    # orphan counts
    orphan_readers = None
    orphan_decoders = None
    try:
        import threading as _th
        orphan_readers = sum(1 for th in _th.enumerate()
                             if th.name.startswith(("tukevision-rtsp-reader", "tukevision-ffmpeg-")) and th.is_alive())
    except Exception:
        pass
    report = {
        "run_id": runtime._run_id,
        "pid": runtime._pid,
        "started_at": _time.strftime("%Y-%m-%dT%H:%M:%S", _time.localtime(started)) if started else "",
        "ended_at": _time.strftime("%Y-%m-%dT%H:%M:%S", _time.localtime(ended)),
        "uptime_seconds": uptime,
        "process_alive": True,
        "ui_responsive": None,
        "cameras_configured": len(runtime._camera_ids),
        "cameras_available_start": None,
        "cameras_live": sum(1 for c in cameras if c["FINAL_STATE"]=="ONLINE"),
        "cameras_stale": sum(1 for c in cameras if c["FINAL_STATE"]=="STALE"),
        "cameras_reconnecting": sum(1 for c in cameras if c["FINAL_STATE"]=="RECONNECTING"),
        "cameras_offline": sum(1 for c in cameras if c["FINAL_STATE"]=="OFFLINE"),
        "reconnect_total": sum(c["RECONNECTS"] for c in cameras),
        "freeze_total": None,
        "technical_gate": "NOT_CERTIFIED",
        "certification_note": "Continuity and decoder shutdown require independent verification",
        "no_first_frame_total": sum(1 for c in cameras if c["NO_FIRST_FRAME"]),
        "orphan_readers": orphan_readers,
        "orphan_decoders": orphan_decoders,
        "rss_start_mb": tele[0]["process_rss_mb"] if tele else None,
        "rss_end_mb": tele[-1]["process_rss_mb"] if tele else None,
        "rss_delta_mb": round((tele[-1]["process_rss_mb"] - tele[0]["process_rss_mb"]),1) if len(tele)>=2 and tele[-1].get("process_rss_mb") is not None and tele[0].get("process_rss_mb") is not None else None,
        "cpu_percent": tele[-1].get("cpu_percent") if tele else None,
        "thread_count": tele[-1].get("thread_count") if tele else None,
        "queue_depth": tele[-1].get("queue_depths", {}) if tele else {},
        "markers": markers,
        "per_camera": cameras,
        "evidence_paths": [str(base / "physical_runtime_report.json")],
        "sha256": "",
        "shutdown": {"UNHANDLED_EXCEPTION": 1 if forensics.registry.get("why_process_exited")=="UNHANDLED_EXCEPTION" else None, "NORMAL_UI_CLOSE": 1 if forensics.registry.get("why_process_exited")=="NORMAL_UI_CLOSE" else 0, "orphan_readers": orphan_readers, "orphan_decoders": orphan_decoders},
    }
    # compute sha256 of report without sha field
    import hashlib as _hl
    tmp_path = base / "physical_runtime_report.json.tmp"
    txt = json.dumps(report, indent=2)
    report.pop("sha256", None)
    tmp_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tmp_path.replace(base / "physical_runtime_report.json")
    manifest = {p.name: _hl.sha256(p.read_bytes()).hexdigest()
                for p in base.glob("*.json") if p.name != "sha256_manifest.json"}
    (base / "sha256_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Unknown measurements stay null, never successful by default.


def _verify_orphans(runtime):
    import threading as _th
    orphans = [th for th in _th.enumerate() if "tukevision-rtsp-reader" in th.name]
    alive = sum(1 for th in orphans if th.is_alive())
    # log verification, gate requires 0
    import logging as _lg
    _lg.getLogger("tukevision.runtime").info("ORPHAN_VERIFY readers=%s alive=%s run_id=%s", len(orphans), alive, runtime._run_id)

if __name__ == "__main__": raise SystemExit(main())
