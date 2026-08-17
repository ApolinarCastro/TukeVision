"""BASE multicamera operator entrypoint; capture remains in SourceManager."""
from __future__ import annotations
import ast, getpass, json, sys, threading
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from src.app.operational_pipeline import OperationalPipeline
from src.capture.source_manager import CameraDescriptor, SourceManager
from src.observability.logging_setup import new_run_id, setup_logging
from src.ui.controller import UiController
from src.ui.tk_view import TkApp

CHANNELS = (7, 1, 5, 3)
CAMERAS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")

def connection_constants():
    tree = ast.parse((BASE / "evidence/loop_0018o/validate_multicamera4.py").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in {"HOST", "USER"} and isinstance(node.value, ast.Constant):
                values[node.targets[0].id] = str(node.value.value)
    if set(values) != {"HOST", "USER"}:
        raise RuntimeError("Historical non-secret connection metadata unavailable")
    return values["HOST"], values["USER"]

class MulticameraRuntime:
    def __init__(self, config, password, host, user):
        self._stop = threading.Event()
        self._controller = UiController(config=config)
        self._manager = SourceManager()
        for camera_id, channel in zip(CAMERAS, CHANNELS):
            self._manager.register_source(CameraDescriptor(
                camera_id=camera_id, host=host, channel=channel,
                subtype=0 if channel == 7 else 1, username=user, password=password,
                max_width=int(config.get("video", {}).get("max_width", 640)),
                rtsp_open_timeout_ms=int(config.get("rtsp", {}).get("open_timeout_ms", 8000)),
                frame_stall_timeout_s=float(config.get("rtsp", {}).get("frame_stall_timeout_s", 10.0))))
        self._pipeline = OperationalPipeline(config, self._manager)
        self._thread = threading.Thread(target=self._run, name="tukevision-multicamera-pipeline", daemon=True)
    def start(self): self._thread.start()
    def _run(self):
        def on_result(camera_id, snapshot, result):
            self._controller.ingest_camera_snapshot(camera_id, SimpleNamespace(
                frame_index=int(snapshot.get("frame_index", -1)), frame=snapshot.get("frame"),
                source_state=snapshot.get("state", "OPEN"), fps=float(snapshot.get("fps", 0.0) or 0.0)))
        self._pipeline.run(self._stop.is_set, on_result)
    def poll_multicamera(self): return self._controller.poll_multicamera()
    def poll_state(self):
        running = not self._stop.is_set() and self._thread.is_alive()
        return {"status": "RUNNING" if running else "STOPPED", "source_path_display": "MULTICAMERA",
                "source_state": "OPEN", "resolution": "", "fps": 0.0, "zone_id": "", "zone_name": "",
                "followed_track": None, "permanence_seconds": 0.0, "risk_text": "", "latest_risk_score": None,
                "alert_log": [], "evidence_paths": [], "error": "", "final_status": "STOPPED"}
    def stop(self): self._stop.set()
    def close(self): self._stop.set(); self._thread.join(timeout=15)

def main():
    setup_logging(run_id=new_run_id())
    config = json.loads((BASE / "config/default.json").read_text(encoding="utf-8"))
    host, user = connection_constants()
    password = getpass.getpass("Credencial RTSP autorizada (no se muestra ni persiste): ")
    if not password:
        print("AUTHORIZED_SOURCE_UNAVAILABLE")
        return 3
    runtime = MulticameraRuntime(config, password, host, user)
    runtime.start()
    import tkinter as tk
    root = tk.Tk()
    try:
        TkApp(root, runtime).run()
    finally:
        runtime.close()
    return 0

if __name__ == "__main__": raise SystemExit(main())
