import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.run_multicamera import build_panel_snapshot
from src.observability.runtime_trace import BoundedRuntimeTrace
from src.ui.tk_view import fit_frame_to_panel, multicamera_control_state

import numpy as np


class TestMulticameraEntrypoint(unittest.TestCase):
    def test_launcher_selects_mode_without_secrets(self):
        launcher = Path("start_tukevision.ps1").read_text(encoding="utf-8")
        entrypoint = Path("scripts/run_multicamera.py").read_text(encoding="utf-8")
        self.assertIn('Mode -ieq "Multicamera"', launcher)
        self.assertIn("run_multicamera.py", launcher)
        self.assertIn("SourceManager", entrypoint)
        self.assertIn("OperationalPipeline", entrypoint)
        self.assertIn("getpass.getpass", entrypoint)
        self.assertNotIn("rtsp://", launcher.lower())
        self.assertNotIn("password=", launcher.lower())
        self.assertNotIn("VideoCapture", entrypoint)

    def test_canonical_result_is_adapted_without_fabricating_values(self):
        event = SimpleNamespace(metadata={"detections": 2}, event_type="PERSON_DETECTED")
        track = SimpleNamespace(track_id="TRK-7")
        activity = SimpleNamespace(activity_type="PERSON_PRESENCE", status="ACTIVE", duration_ms=2300)
        signal = SimpleNamespace(signal_type="PROLONGED_DWELL")
        risk = SimpleNamespace(risk_event_type="REVIEW", risk_score=65)
        behavior = SimpleNamespace(signals=(signal,), risk_event=risk)
        source = {"frame_index": 9, "frame": object(), "state": "OPEN", "fps": 4.0}
        result = {"event": event, "track": track, "temporal_activity": activity,
                  "behavior": behavior, "evidence": {"relative_path": "CAM-001/EVD/frame.jpg"}}
        panel = build_panel_snapshot(source, result)
        self.assertEqual(panel.detections, 2)
        self.assertEqual(panel.track_id, "TRK-7")
        self.assertEqual(panel.temporal, "PERSON_PRESENCE ACTIVE 2.3s")
        self.assertEqual(panel.behavior, "PROLONGED_DWELL")
        self.assertEqual(panel.risk, "REVIEW 65")
        self.assertEqual(panel.evidence, "CAM-001/EVD/frame.jpg")

    def test_runtime_trace_is_bounded_and_records_ui_boundary(self):
        trace = BoundedRuntimeTrace(("CAM-001",))
        result = {
            "observation": object(),
            "event": SimpleNamespace(metadata={"detections": 2}),
            "track": object(), "temporal_activity": object(),
            "behavior": SimpleNamespace(signals=(object(),)),
            "evidence": {"relative_path": "CAM-001/EVD/frame.jpg"},
        }
        trace.observe_pipeline_result("CAM-001", 10, result)
        trace.mark_ui_model_received("CAM-001", 10)
        trace.mark_ui_rendered("CAM-001", 10)
        snapshot = trace.snapshot()["CAM-001"]
        self.assertEqual(snapshot["FRAME_RECEIVED"], 1)
        self.assertEqual(snapshot["DETECTIONS_RETURNED"], 2)
        self.assertEqual(snapshot["UI_MODEL_RECEIVED"], 1)
        self.assertEqual(snapshot["UI_RENDERED"], 1)
        self.assertNotIn("frame", snapshot)

    def test_multicamera_controls_follow_runtime_and_hide_legacy(self):
        running = multicamera_control_state("RUNNING")
        stopped = multicamera_control_state("STOPPED")
        self.assertFalse(running["show_legacy"])
        self.assertTrue(running["stop_enabled"])
        self.assertFalse(stopped["stop_enabled"])

    def test_panel_fit_is_consistent_without_upscaling_source(self):
        frame = np.full((100, 200, 3), 255, dtype=np.uint8)
        fitted = fit_frame_to_panel(frame, width=400, height=240)
        self.assertEqual(fitted.shape, (240, 400, 3))
        self.assertEqual(int(np.count_nonzero(fitted == 255)), frame.size)


if __name__ == "__main__":
    unittest.main()
