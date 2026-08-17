import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.run_multicamera import build_panel_snapshot


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


if __name__ == "__main__":
    unittest.main()
