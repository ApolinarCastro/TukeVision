"""LOOP-0019B smoke: instantiate TkApp (multicamera) and render 4 panels."""
import sys
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

import numpy as np
import tkinter as tk

from src.ui.tk_view import TkApp, camera_summary_line
from src.ui.multicamera import CAMERA_IDS


def make_frame(index):
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = (30, 40, 50)
    x = 200 + index * 60
    frame[200:600, x:x + 160] = (90, 140, 220)
    return frame


def make_panel(camera_id, index):
    return SimpleNamespace(
        camera_id=camera_id,
        source_state="OPEN",
        frame=make_frame(index),
        frame_index=index,
        fps=15.0,
        detections=2,
        track_id=f"TRK-{index}",
        track_status="ACTIVE",
        track_bbox=(200, 200, 360, 600),
        bboxes=((200, 200, 360, 600, 0.91, "person"),),
        event_type="PERSON_DETECTED",
        event_confidence=0.91,
        analytics_frame=make_frame(index),
        analytics_frame_index=index,
        temporal="PERSON_PRESENCE ACTIVE 2.3s",
        behavior="PROLONGED_DWELL",
        risk="REVIEW 65",
        evidence="CAM-001/EVD/frame.jpg",
        resolution="1280x720",
    )


class FakeRuntime:
    is_multicamera = True
    evidence_root = str(BASE / "data/runtime_evidence")

    def __init__(self):
        self._index = 1
        self.panels = {cid: make_panel(cid, i) for i, cid in enumerate(CAMERA_IDS)}

    def poll_multicamera(self):
        return self.panels

    def poll_state(self):
        return {
            "status": "RUNNING", "source_path_display": "MULTICAMERA",
            "source_kind": "MULTICAMERA", "source_state": "OPEN",
            "resolution": "1280x720", "fps": 15.0, "zone_id": "",
            "zone_name": "", "followed_track": "TRK-1",
            "permanence_seconds": 2.3, "risk_text": "REVIEW 65",
            "latest_risk_score": None, "alert_log": [],
            "evidence_paths": ["CAM-001/EVD/frame.jpg"],
            "clips_available": 2, "error": "", "final_status": "",
        }

    def mark_ui_rendered(self, camera_id, frame_index):
        pass

    def stop(self):
        pass

    def close(self):
        pass


def main():
    root = tk.Tk()
    root.withdraw()
    app = TkApp(root, FakeRuntime())
    root.update_idletasks()
    root.deiconify()
    for _ in range(3):
        root.update()
        app._poll_once()
        root.update()
    panels = app._controller.poll_multicamera()
    for cid in CAMERA_IDS:
        assert app._photos[cid] is not None, f"{cid} not rendered"
        line = camera_summary_line(panels[cid])
        print(f"{cid}: photo ok, summary='{line[:90]}...'")
    assert app._clip_var.get() == "Clip disponible: 2"
    assert app._cameras_var.get().endswith("ONLINE")
    print("SIDE_PANEL clip=", app._clip_var.get())
    print("HEADER=", app._cameras_var.get(), "|", app._res_var.get(), "|", app._fps_var.get())
    root.destroy()
    print("SMOKE_OK")


if __name__ == "__main__":
    main()