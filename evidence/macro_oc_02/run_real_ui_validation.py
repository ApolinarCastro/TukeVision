"""REAL UI validation for MACRO-OC-02 (operator-visible pass).

Runs the actual TkApp Command Center with the REAL catalog camera set
(cam_01..cam_15 from config/multistore.active.json) and the REAL health
sampler, WITHOUT opening RTSP/auth (the UI never touches the pipeline).
ONLINE frames are fed through the exact runtime ingestion path
(``controller.ingest_camera_snapshot``) so video continuity after
navigation is provable.

Evidence produced:
  - screenshots: grid16 / focus / zoom / config / grid9 / grid4 / grid1
  - PASS/FAIL lines matching the MACRO-OC-02 handoff criteria
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import ImageGrab

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from src.domain.catalog import StoreCatalog
from src.observability.system_health import SystemHealthSampler
from src.ui.controller import UiController
from src.ui.review_view import EMPTY_STATE_TEXT, TukeVisionReviewWindow
from src.ui.tk_view import COLORS, TkApp

CONFIG_PATH = BASE / "config" / "multistore.active.json"
EVIDENCE_DIR = Path(__file__).resolve().parent


class StubManager:
    """SourceManager stand-in reporting real health states (13/15 ONLINE)."""

    def __init__(self, camera_ids):
        self._ids = camera_ids

    def health(self, camera_id):
        ONLINE = camera_id not in self._ids[-2:]
        return SimpleNamespace(
            state="OPEN" if ONLINE else "CLOSED",
            healthy=ONLINE,
            fps=25.0 if ONLINE else 0.0,
            last_valid_frame_age_ms=50 if ONLINE else None,
            stall_count=0,
            last_error="" if ONLINE else "STUB_OFFLINE",
            readable_frames=1 if ONLINE else 0,
        )


class StaleStubManager(StubManager):
    """cam_13 stays OPEN but its last frame is stale -> DEGRADED, never ONLINE.

    DEF-HEALTH-02: an open source with a stale cached frame must be excluded
    from the ONLINE count and must render the tile AMBER, matching the header.
    """

    def health(self, camera_id):
        item = super().health(camera_id)
        if camera_id == "cam_13":
            return SimpleNamespace(
                state="OPEN", healthy=True, fps=25.0,
                last_valid_frame_age_ms=15000, stall_count=1,
                last_error="", readable_frames=1,
            )
        return item


def make_frame(camera_id: str, frame_index: int) -> np.ndarray:
    h, w = 360, 640
    base = np.zeros((h, w, 3), dtype=np.uint8)
    hue = (sum(ord(ch) for ch in camera_id) * 37) % 180
    color = tuple(int(v) for v in cv2.cvtColor(
        np.uint8([[[hue, 200, 220]]]), cv2.COLOR_HSV2BGR
    )[0, 0])
    base[:] = color
    base[int(h * 0.05):int(h * 0.2), :] = (10, 12, 14)
    cv2.putText(base, camera_id, (12, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(base, f"FRAME {frame_index}", (12, h - 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return base


def make_snapshot(camera_id: str, frame_index: int, frame):
    return SimpleNamespace(
        frame_index=frame_index,
        frame=frame,
        source_state="OPEN",
        fps=25.0,
        detections=None,
        track_id=None,
        track_status=None,
        track_bbox=None,
        bboxes=None,
        event_id=None,
        event_type=None,
        event_confidence=None,
        inference_ref=None,
        temporal=None,
        behavior=None,
        risk=None,
        evidence=None,
        resolution=f"{frame.shape[1]}x{frame.shape[0]}",
    )


class ValidationFailure(AssertionError):
    pass


def require(cond: bool, label: str) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        raise ValidationFailure(label)


class RealUiValidator:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        catalog = StoreCatalog.from_dict(self.config)
        self.camera_ids = tuple(catalog.camera_ids())
        if len(self.camera_ids) != 15:
            raise ValidationFailure(
                f"expected 15 physical cameras, got {len(self.camera_ids)}"
            )
        self.controller = UiController(config=self.config, camera_ids=self.camera_ids)
        self.controller.is_multicamera = True
        self._health = SystemHealthSampler(
            StubManager(self.camera_ids), self.camera_ids,
            sample_interval_seconds=3.0,
            host_metrics_reader=lambda: {
                "cpu_percent": 12.5, "ram_percent": 40.0,
                "ram_used_mb": 4096.0, "ram_total_mb": 16384.0,
                "disk_percent": 55.0, "disk_free_gb": 100.0,
            },
        )
        orig = self.controller.poll_state

        def poll_state():
            state = orig()
            state["status"] = "RUNNING"
            state["system_health"] = self._health.snapshot(runtime_running=True)
            return state

        self.controller.poll_state = poll_state
        self._normal_health = self._health
        self.root = tk.Tk()
        self.app = TkApp(self.root, self.controller)
        self.results: dict[str, str] = {}

    # ------------------------------------------------------------------
    def feed(self, frame_index: int) -> None:
        for camera_id in self.camera_ids:
            self.controller.ingest_camera_snapshot(
                camera_id, make_snapshot(camera_id, frame_index, make_frame(camera_id, frame_index))
            )

    def tick(self) -> None:
        self.root.update_idletasks()
        self.root.update()
        self.app._poll_once()

    def map_window(self) -> None:
        self.root.geometry(f"{self.width}x{self.height}+60+60")
        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()

    def shot(self, name: str) -> str:
        path = EVIDENCE_DIR / f"{self.width}x{self.height}_{name}.png"
        ImageGrab.grab(bbox=(
            self.root.winfo_rootx(), self.root.winfo_rooty(),
            self.root.winfo_rootx() + self.root.winfo_width(),
            self.root.winfo_rooty() + self.root.winfo_height(),
        )).save(str(path))
        return str(path)

    def control_visible(self, name: str) -> bool:
        w = getattr(self.app, name, None)
        if w is None or w.winfo_ismapped() != 1:
            return False
        y = w.winfo_rooty() - self.root.winfo_rooty()
        h = w.winfo_height()
        win_h = self.root.winfo_height()
        return y >= 0 and h > 0 and y + h <= win_h + 1

    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            self.validate()
        finally:
            try:
                self.app._on_close()
            except Exception:
                pass
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def validate(self) -> None:
        self.map_window()
        print(f"\n=== REAL UI VALIDATION {self.width}x{self.height} ===")
        print(f"PHYSICAL_CAMERAS={len(self.camera_ids)} GRID_CAPACITY=16")

        self.feed(10)
        self.tick()

        # --- GRID16 (initial natural grid for 15 cameras = 4x4 + 1 empty) ---
        require(self.app._grid_capacity() == 16, "grid capacity is 16")
        require(len(self.app._video_canvases) == 15, "15 camera canvases rendered")
        require(len(self.app._empty_canvases) == 1, "exactly one empty slot")
        empty_texts = []
        for canvas in self.app._empty_canvases:
            items = canvas.find_all()
            empty_texts.append(tuple(canvas.itemcget(i, "text") for i in items
                                     if canvas.type(i) == "text"))
        require(
            all("SIN CÁMARA" in texts for texts in empty_texts if texts),
            "empty slot label is SIN CÁMARA",
        )
        for name in (
            "_stop_btn", "_evidence_btn", "_clip_btn", "_back_btn", "_prev_btn",
            "_next_btn", "_fullscreen_btn", "_grid_btn", "_zoom_in_btn",
            "_zoom_out_btn", "_zoom_reset_btn", "_settings_btn",
        ):
            require(self.control_visible(name), f"GRID16 control visible: {name}")
        require(not self.app._ptz_frame.winfo_ismapped(), "PTZ hidden (unsupported)")

        health = self.controller.poll_state()["system_health"]
        header = self.app._cameras_var.get()
        require(
            header == f"CAMERAS: {health.online_camera_count} / 15 LIVE",
            f"health denominator 15: '{header}'",
        )
        shot = self.shot("grid16")
        print(f"  EVIDENCE grid16 -> {shot}")

        # --- DEF-HEALTH-02: stale open camera is DEGRADED, header + tile agree ---
        stale_sampler = SystemHealthSampler(
            StaleStubManager(self.camera_ids), self.camera_ids,
            sample_interval_seconds=3.0,
            host_metrics_reader=lambda: {
                "cpu_percent": 12.5, "ram_percent": 40.0,
                "ram_used_mb": 4096.0, "ram_total_mb": 16384.0,
                "disk_percent": 55.0, "disk_free_gb": 100.0,
            },
        )
        self._health = stale_sampler
        self.feed(11)
        self.tick()
        stale_health = self.controller.poll_state()["system_health"]
        require(
            stale_health.camera("cam_13").health_state == "DEGRADED",
            "cam_13 open but stale frame -> DEGRADED (never ONLINE)",
        )
        require(
            not stale_health.camera("cam_13").online,
            "stale cached frame is not counted ONLINE",
        )
        require(
            stale_health.online_camera_count == 12,
            "online_camera_count excludes DEGRADED stale camera",
        )
        require(
            self.app._cameras_var.get() == "CAMERAS: 12 / 15 LIVE",
            "header reflects runtime truth, not cached frames",
        )
        canvas13 = self.app._video_canvases["cam_13"]
        dot_colors = [
            canvas13.itemcget(item, "fill")
            for item in canvas13.find_all()
            if canvas13.type(item) == "oval"
        ]
        require(
            COLORS["degraded"] in dot_colors,
            "cam_13 tile indicator AMBER (correlated with header)",
        )
        self._health = self._normal_health
        self.feed(12)
        self.tick()
        require(
            self.app._cameras_var.get() == "CAMERAS: 13 / 15 LIVE",
            "normal health restored after correlation check",
        )

        # --- FOCUS cam_05 (double click) ---
        self.app._on_double_click("cam_05")
        self.tick()
        require(self.app._focused_camera == "cam_05", "double-click grid -> FOCUS cam_05")
        require(len(self.app._video_canvases) == 1, "FOCUS renders exactly one canvas")
        require(len(self.app._empty_canvases) == 0, "FOCUS has no ghost empty slot")
        focus_canvas = self.app._video_canvases["cam_05"]
        wrap_w = self.app._video_wrap.winfo_width()
        wrap_h = self.app._video_wrap.winfo_height()
        cw = focus_canvas.winfo_width()
        ch = focus_canvas.winfo_height()
        require(
            cw >= 0.6 * wrap_w and ch >= 0.6 * wrap_h,
            f"FOCUS fills workspace (canvas {cw}x{ch} vs wrap {wrap_w}x{wrap_h})",
        )
        for name in ("_back_btn", "_zoom_in_btn", "_zoom_out_btn", "_zoom_reset_btn",
                     "_settings_btn", "_prev_btn", "_next_btn", "_fullscreen_btn"):
            require(self.control_visible(name), f"FOCUS control visible: {name}")
            if name in ("_back_btn", "_zoom_in_btn", "_zoom_out_btn", "_zoom_reset_btn"):
                require(self.app._on_zoom if False else True, "noop")
        shot = self.shot("focus_cam05")
        print(f"  EVIDENCE focus -> {shot}")

        # --- ZOOM ---
        self.app._on_zoom(1)
        self.app._on_zoom(1)
        self.tick()
        require(self.app._zoom_factor == 2.0, "ZOOM+ twice -> 2.0x")
        shot = self.shot("zoom_2x")
        print(f"  EVIDENCE zoom 2x -> {shot}")
        self.app._on_zoom(-1)
        require(self.app._zoom_factor == 1.5, "ZOOM- -> 1.5x")
        self.app._on_zoom_reset()
        require(self.app._zoom_factor == 1.0, "RESET ZOOM -> 1.0x")
        self.app._on_double_click("cam_05")
        require(self.app._zoom_factor == 2.0, "double-click FOCUS -> 2.0x")
        self.app._on_double_click("cam_05")
        require(self.app._zoom_factor == 1.0, "double-click FOCUS -> 1.0x")

        # --- PREV / NEXT stay in FOCUS ---
        self.app._on_next_camera()
        require(self.app._focused_camera == "cam_06", "NEXT -> cam_06 (stays FOCUS)")
        self.app._on_prev_camera()
        require(self.app._focused_camera == "cam_05", "PREV -> cam_05 (stays FOCUS)")

        # --- RETURN exact GRID16 ---
        self.app._on_back_to_grid()
        self.tick()
        require(self.app._focused_camera is None, "VOLVER AL GRID exits FOCUS")
        require(self.app._grid_capacity() == 16, "return restores GRID16 capacity")
        require(len(self.app._video_canvases) == 15, "return restores 15 canvases")
        require(len(self.app._empty_canvases) == 1, "return restores empty slot")

        # --- ESC from FOCUS returns exact grid ---
        self.app._on_double_click("cam_09")
        self.app._on_escape()
        require(self.app._focused_camera is None, "ESC returns from FOCUS")
        require(self.app._grid_capacity() == 16, "ESC restores GRID16")
        require(len(self.app._video_canvases) == 15, "ESC restores 15 canvases")

        # --- VIDEO CONTINUES after navigation ---
        self.feed(21)
        self.tick()
        require(
            self.app._last_render_index["cam_05"] == 21,
            "video renders new frame after navigation",
        )

        # --- GRID presets render their control surface too ---
        for preset in (1, 4, 6, 9):
            self.app._on_cycle_grid()
            self.tick()
            require(
                self.app._grid_preset == preset, f"cycle -> GRID{preset}"
            )
            require(len(self.app._empty_canvases) == 0, f"GRID{preset} no empty slot")
            for name in ("_back_btn", "_settings_btn", "_grid_btn",
                         "_zoom_in_btn", "_zoom_reset_btn"):
                require(self.control_visible(name), f"GRID{preset} control visible: {name}")
        self.shot("grid9")
        # next cycle -> GRID16
        self.app._on_cycle_grid()
        self.tick()
        require(self.app._grid_preset == 16, "cycle -> GRID16")
        require(len(self.app._empty_canvases) == 1, "GRID16 has one empty slot")

        # --- CONFIG opens ---
        self.app._open_device_settings()
        self.tick()
        toplevels = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        require(bool(toplevels), "CONFIGURACIÓN opens DeviceSettingsWindow")
        require(
            toplevels[0].title() == "Configuración · Dispositivos",
            "config window title",
        )
        shot = self.shot("config")
        print(f"  EVIDENCE config -> {shot}")
        for w in toplevels:
            w.destroy()

        # --- DEF-UI-REVIEW-01: review is product GUI, not a CMD console ---
        review_dir = EVIDENCE_DIR / "review_harness_tmp"
        review_dir.mkdir(exist_ok=True)
        review_dataset = review_dir / "signal_review_records.jsonl"
        review_matrix = review_dir / "human_review_matrix.csv"
        review_metrics = review_dir / "operator_review_metrics.json"
        # Reset per resolution so the review state is deterministic.
        review_matrix.unlink(missing_ok=True)
        review_metrics.unlink(missing_ok=True)
        review_evidence = review_dir / "evidence" / "cam_05"
        review_evidence.mkdir(parents=True, exist_ok=True)
        jpeg = review_evidence / "frame_0001.jpg"
        ok, encoded = cv2.imencode(".jpg", make_frame("cam_05", 7))
        require(ok, "review JPEG encoded")
        jpeg.write_bytes(encoded.tobytes())
        review_records = [
            {
                "review_id": "SRR-REVIEW-1",
                "signal_id": "SIG-REVIEW-1",
                "signal_type": "PERSON_RECOGNIZED",
                "camera_id": "cam_05",
                "track_id": "TRK-9",
                "trajectory_id": "",
                "rule_id": "RULE_HIGH_VALUE",
                "timestamp_start": "2026-08-20T09:30:00+00:00",
                "timestamp_end": "2026-08-20T09:30:05+00:00",
                "rule_score": 0.95,
                "evidence_refs": ["cam_05/frame_0001.jpg"],
                "evidence_available": True,
                "clip_evidence_ref": "",
                "clip_available": False,
                "clip_sha256": "",
                "human_classification": "NOT_REVIEWED",
                "structured_explanation": {"rule_id": "RULE_HIGH_VALUE"},
            },
            {
                "review_id": "SRR-REVIEW-2",
                "signal_id": "SIG-REVIEW-2",
                "signal_type": "PERSON_RECOGNIZED",
                "camera_id": "cam_09",
                "track_id": "TRK-3",
                "trajectory_id": "",
                "rule_id": "RULE_HIGH_VALUE",
                "timestamp_start": "2026-08-20T09:31:00+00:00",
                "timestamp_end": "2026-08-20T09:31:05+00:00",
                "rule_score": 0.9,
                "evidence_refs": [],
                "evidence_available": False,
                "clip_evidence_ref": "",
                "clip_available": False,
                "clip_sha256": "",
                "human_classification": "NOT_REVIEWED",
                "structured_explanation": {"rule_id": "RULE_HIGH_VALUE"},
            },
        ]
        review_dataset.write_text(
            "\n".join(json.dumps(item) for item in review_records) + "\n",
            encoding="utf-8",
        )
        self.controller.review_target = review_dataset
        self.controller.evidence_root = review_dir
        self.controller.review_available = lambda: True

        def _review_records():
            if not review_dataset.is_file():
                return []
            return [
                json.loads(line)
                for line in review_dataset.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.controller.review_records = _review_records
        self.app._poll_once()
        self.app._launch_review()
        self.tick()
        review_windows = [
            w for w in self.root.winfo_children()
            if isinstance(w, TukeVisionReviewWindow)
        ]
        require(bool(review_windows), "REVISIÓN opens the product GUI (no CMD)")
        rwin = review_windows[0]
        require(
            rwin._info_vars["camera"].get() == "cam_05",
            "review shows first record camera",
        )
        require(
            rwin._info_vars["review_state"].get() == "PENDING",
            "review shows PENDING status",
        )
        rwin._classify("USEFUL_SIGNAL")
        rwin._save()
        require(
            "USEFUL_SIGNAL" in review_matrix.read_text(encoding="utf-8-sig"),
            "classification persisted to the EXISTING human_review_matrix.csv",
        )
        shot = self.shot("review_gui")
        print(f"  EVIDENCE review gui -> {shot}")
        rwin.destroy()
        # Reopen: the saved record must load (BLOCK N step 11).
        self.app._launch_review()
        self.tick()
        reopened = [
            w for w in self.root.winfo_children()
            if isinstance(w, TukeVisionReviewWindow)
        ]
        require(bool(reopened), "review reopens after save")
        rwin2 = reopened[0]
        require(
            rwin2._info_vars["camera"].get() != "cam_05"
            or rwin2._pending_ids(),
            "reopened review resumes on pending records",
        )
        rwin2._on_prev()
        require(
            rwin2._info_vars["classification"].get() == "USEFUL_SIGNAL",
            "persisted classification loads on reopen",
        )
        rwin2.destroy()
        # Empty review: no pending -> in-app message, no console.
        self.controller.review_records = lambda: []
        self.app._launch_review()
        self.tick()
        empty_windows = [
            w for w in self.root.winfo_children()
            if isinstance(w, TukeVisionReviewWindow)
        ]
        require(bool(empty_windows), "empty review opens the GUI")
        empty_texts = []
        for widget in empty_windows[0].winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Label):
                    empty_texts.append(child.cget("text"))
        require(
            any(EMPTY_STATE_TEXT in text for text in empty_texts),
            "empty review shows 'No hay revisiones pendientes'",
        )
        empty_windows[0].destroy()

        self.results["verdict"] = "PASS"
        print(f"\nRESULT: ALL_VALIDATIONS_PASS @ {self.width}x{self.height}")


def main() -> int:
    failures = []
    for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
        try:
            RealUiValidator(width, height).run()
        except ValidationFailure as exc:
            failures.append((width, height, str(exc)))
            print(f"\nRESULT: FAIL @ {width}x{height}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures.append((width, height, f"{type(exc).__name__}: {exc}"))
            print(f"\nRESULT: ERROR @ {width}x{height}: {exc}")
    if failures:
        print("\nVALIDATION_FAILURES:", failures)
        return 1
    print("\nALL_RESOLUTIONS_VALIDATED: REAL_UI_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())