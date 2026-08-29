"""MACRO-OC-02 stability instrumentation tests (BLOCKS C / D / E / L).

- BLOCK C: per-camera frame heartbeat distinguishes CAPTURE / INFERENCE /
  RENDER stalls from runtime timestamps (never per-frame logging).
- BLOCK D: resource telemetry samples UPTIME/CPU/RSS/RAM/threads/queues/
  online/reconnecting and exports atomically.
- BLOCK E: exit forensics records WHY_PROCESS_EXITED with sanitized
  tracebacks (no credentials/RTSP URL leaks).
- BLOCK L: a source recovering is RECONNECTING, never ONLINE.
"""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.app.operational_pipeline import OperationalPipeline
from src.observability.exit_forensics import ExitForensics
from src.observability.frame_heartbeat import (
    CAPTURE_STALL,
    HEALTHY,
    INFERENCE_STALL,
    NO_FRAME,
    RENDER_STALL,
    FrameHeartbeat,
)
from src.observability.resource_telemetry import MARKERS_SECONDS, ResourceTelemetry


def wall_now():
    """Deterministic wall-clock for heartbeat timestamps."""
    return 1000.0


class TestFrameHeartbeat(unittest.TestCase):
    def test_no_frame_until_received(self):
        hb = FrameHeartbeat(("cam_01",), now=wall_now)
        item = hb.per_camera("cam_01")
        self.assertEqual(item["state"], NO_FRAME)
        self.assertIsNone(item["last_received_frame_at"])

    def test_healthy_after_received_inferred_rendered(self):
        hb = FrameHeartbeat(("cam_01",), now=wall_now)
        hb.mark_received("cam_01", 1)
        hb.mark_inferred("cam_01", 1)
        hb.mark_rendered("cam_01", 1)
        self.assertEqual(hb.per_camera("cam_01")["state"], HEALTHY)

    def test_capture_stall_when_receive_old(self):
        clock = {"t": 1000.0}
        hb = FrameHeartbeat(("cam_01",), now=lambda: clock["t"])
        hb.mark_received("cam_01", 1)
        clock["t"] = 1010.0
        self.assertEqual(hb.per_camera("cam_01")["state"], CAPTURE_STALL)

    def test_inference_stall_when_received_but_not_processed(self):
        clock = {"t": 1000.0}
        hb = FrameHeartbeat(("cam_01",), now=lambda: clock["t"])
        hb.mark_received("cam_01", 1)
        hb.mark_inferred("cam_01", 1)
        hb.mark_rendered("cam_01", 1)
        clock["t"] = 1005.0
        hb.mark_received("cam_01", 2)  # new frame arrives, old inference
        clock["t"] = 1006.0
        self.assertEqual(hb.per_camera("cam_01")["state"], INFERENCE_STALL)

    def test_render_stall_when_processed_but_not_drawn(self):
        clock = {"t": 1000.0}
        hb = FrameHeartbeat(("cam_01",), now=lambda: clock["t"])
        hb.mark_received("cam_01", 1)
        hb.mark_inferred("cam_01", 1)
        hb.mark_rendered("cam_01", 1)
        clock["t"] = 1005.0
        hb.mark_received("cam_01", 2)
        hb.mark_inferred("cam_01", 2)
        clock["t"] = 1006.0
        self.assertEqual(hb.per_camera("cam_01")["state"], RENDER_STALL)

    def test_summary_counts(self):
        clock = {"t": 1000.0}
        hb = FrameHeartbeat(("cam_01", "cam_02"), now=lambda: clock["t"])
        hb.mark_received("cam_01", 1)
        hb.mark_inferred("cam_01", 1)
        hb.mark_rendered("cam_01", 1)
        hb.mark_received("cam_02", 1)
        clock["t"] = 1005.0
        hb.mark_received("cam_01", 2)
        hb.mark_inferred("cam_01", 2)
        hb.mark_rendered("cam_01", 2)
        clock["t"] = 1007.0
        summary = hb.summary()
        self.assertEqual(summary["counts"][HEALTHY], 1)
        self.assertEqual(summary["counts"][CAPTURE_STALL], 1)


class _HealthStub:
    def __init__(self, camera_id, state="OPEN"):
        self.camera_id = camera_id
        self.health_state = state


class _HealthSnapshotStub:
    def __init__(self, states):
        self.camera_health = tuple(
            _HealthStub(cid, state) for cid, state in states
        )


class _ManagerStub:
    def __init__(self, ids):
        self._ids = ids

    def list_sources(self):
        return [
            {"camera_id": cid, "running": cid == "cam_01"}
            for cid in self._ids
        ]

    def health(self, camera_id):
        return SimpleNamespace(
            state="OPEN", queue_depth=2 if camera_id == "cam_01" else 0
        )


class TestResourceTelemetry(unittest.TestCase):
    def _telemetry(self, health_states):
        return ResourceTelemetry(
            ("cam_01", "cam_02"),
            _ManagerStub(("cam_01", "cam_02")),
            health_snapshot=lambda: _HealthSnapshotStub(health_states),
            interval_s=1.0,
            markers_seconds=(0, 60),
            psutil_proc=SimpleNamespace(cpu_percent=lambda **kw: 0.0,
                                        memory_info=lambda: SimpleNamespace(rss=1024)),
        )

    def test_t0_baseline_sample(self):
        tele = self._telemetry([("cam_01", "ONLINE"), ("cam_02", "OFFLINE")])
        tele.start()
        self.assertTrue(tele.snapshot())
        self.assertIn("0", tele.marker_rows())
        tele.stop()

    def test_counts_and_metrics_fields(self):
        tele = self._telemetry([("cam_01", "ONLINE"), ("cam_02", "RECONNECTING")])
        tele.start()
        row = tele._sample()
        self.assertEqual(row["online"], 1)
        self.assertEqual(row["reconnecting"], 1)
        self.assertEqual(row["offline"], 0)
        self.assertEqual(row["active_sources"], 1)
        self.assertEqual(row["total_sources"], 2)
        self.assertEqual(row["queue_depths"], {"cam_01": 2, "cam_02": 0})
        self.assertIn("process_rss_mb", row)
        self.assertIn("thread_count", row)
        self.assertIn("uptime_s", row)
        tele.stop()

    def test_export_atomic_and_marker_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tele = self._telemetry([("cam_01", "ONLINE"), ("cam_02", "OFFLINE")])
            tele.start()
            target = tele.export(Path(tmp) / "telemetry.json")
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("samples", payload)
            self.assertIn("marker_rows", payload)
            self.assertIn("0", payload["marker_rows"])
            self.assertFalse(target.with_suffix(".json.tmp").exists())
            tele.stop()


class TestExitForensics(unittest.TestCase):
    def _forensics(self, tmp):
        return ExitForensics(Path(tmp) / "process_exit_forensics.json")

    def test_normal_close_writes_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            forensics = self._forensics(tmp)
            forensics.record_exit("NORMAL_UI_CLOSE")
            payload = json.loads(
                (Path(tmp) / "process_exit_forensics.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["why_process_exited"], "NORMAL_UI_CLOSE")
            self.assertGreaterEqual(payload["uptime_s"], 0)
            self.assertIn("pid", payload)
            self.assertFalse((Path(tmp) / "process_exit_forensics.json.tmp").exists())

    def test_unhandled_traceback_is_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            forensics = self._forensics(tmp)
            try:
                raise ValueError("rtsp://admin:supersecret@186.103.177.83/cam/realmonitor")
            except ValueError as exc:
                forensics.record_unhandled(type(exc), exc, exc.__traceback__)
            payload = json.loads(
                (Path(tmp) / "process_exit_forensics.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["why_process_exited"], "UNHANDLED_EXCEPTION")
            rendered = json.dumps(payload)
            self.assertNotIn("supersecret", rendered)
            self.assertEqual(payload["detail"]["exception_type"], "ValueError")

    def test_first_record_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            forensics = self._forensics(tmp)
            forensics.record_exit("NORMAL_UI_CLOSE")
            forensics.record_exit("UNHANDLED_EXCEPTION", {"message": "late"})
            payload = json.loads(
                (Path(tmp) / "process_exit_forensics.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["why_process_exited"], "NORMAL_UI_CLOSE")
            self.assertNotIn("detail", payload)


class _RecvManager:
    def __init__(self):
        self._snapshots = {"cam_01": {"frame_index": 0, "frame": None, "state": "OPEN"}}
        self._calls = []

    def start(self, camera_id):
        pass

    def list_sources(self):
        return [{"camera_id": "cam_01", "running": True}]

    def snapshot(self, camera_id):
        return dict(self._snapshots[camera_id])

    def close_all(self):
        pass


class _ChainStub:
    @staticmethod
    def build(config, manager, review_target=None):
        return _ChainStub()

    def feed(self, camera_id, frame_index, fps, frame, metadata):
        return {"event": None, "track": None, "temporal_activity": None,
                "behavior": None, "evidence": None}

    def register_from_source_manager(self):
        return []

    def summary(self):
        return {}

    def close(self):
        pass


class TestOperationalPipelineReceivedHook(unittest.TestCase):
    def test_on_received_fires_only_for_new_real_frames(self):
        manager = _RecvManager()
        received = []
        pipeline = OperationalPipeline(
            {"video": {"max_width": 320, "process_every_n_frames": 1}},
            manager,
            chain=_ChainStub(),
            on_received=lambda cid, idx: received.append((cid, idx)),
        )
        manager._snapshots["cam_01"] = {"frame_index": 1, "frame": object(), "state": "OPEN"}
        result = pipeline.process_available("cam_01")
        self.assertIsNotNone(result)
        self.assertEqual(received, [("cam_01", 1)])
        # Same frame again: no duplicate receive.
        pipeline.process_available("cam_01")
        self.assertEqual(received, [("cam_01", 1)])
        # No frame yet -> no receive.
        manager._snapshots["cam_01"] = {"frame_index": 2, "frame": None, "state": "OPEN"}
        pipeline.process_available("cam_01")
        self.assertEqual(received, [("cam_01", 1)])
        pipeline.close()


if __name__ == "__main__":
    unittest.main()
class TestLivenessRegressions(unittest.TestCase):
    def test_duplicate_frame_does_not_renew_age(self):
        from unittest.mock import patch
        import numpy as np
        from src.observability.true_liveness import TrueLivenessTracker
        tracker = TrueLivenessTracker(['cam'])
        with patch('src.observability.true_liveness.time.monotonic', return_value=10):
            tracker.observe_frame('cam', np.zeros((2,2,3), dtype=np.uint8), 0)
        with patch('src.observability.true_liveness.time.monotonic', return_value=14):
            tracker.observe_frame('cam', np.zeros((2,2,3), dtype=np.uint8), 0)
            self.assertFalse(tracker.snapshot()['cam'].live)
            self.assertEqual(tracker.snapshot()['cam'].last_frame_monotonic, 10)

    def test_static_scene_advancing_frames_remains_live(self):
        import numpy as np
        from src.observability.true_liveness import TrueLivenessTracker
        tracker = TrueLivenessTracker(['cam'])
        for idx in range(10):
            tracker.observe_frame('cam', np.zeros((2,2,3), dtype=np.uint8), idx)
        self.assertTrue(tracker.snapshot()['cam'].live)

    def test_new_generation_can_reset_sequence(self):
        import numpy as np
        from src.observability.true_liveness import TrueLivenessTracker
        tracker = TrueLivenessTracker(['cam'])
        frame = np.zeros((2,2,3), dtype=np.uint8)
        tracker.observe_frame('cam',frame,100,generation=1)
        tracker.observe_frame('cam',frame,0,generation=2)
        self.assertEqual(tracker.snapshot()['cam'].frame_sequence,0)
        self.assertTrue(tracker.snapshot()['cam'].live)

    def test_telemetry_persists_during_sampling_and_no_future_deltas(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'telemetry.json'
            tele = ResourceTelemetry(['cam_01'], _ManagerStub(['cam_01']), interval_s=1,
                                     identity={'run_id':'RUN-TEST','pid':123},
                                     psutil_proc=SimpleNamespace(cpu_percent=lambda **kw: 0.0,
                                                                 memory_info=lambda: SimpleNamespace(rss=1024)))
            tele._on_sample = lambda: tele.export(target)
            try:
                tele.start()
                first = json.loads(target.read_text())
                deadline = time.monotonic()+3
                while time.monotonic()<deadline:
                    current=json.loads(target.read_text())
                    if len(current['samples'])>=2:
                        break
                    time.sleep(.05)
                self.assertEqual(current['run_id'],'RUN-TEST')
                self.assertGreater(len(current['samples']),len(first['samples']))
                self.assertNotIn('rss_delta_30m_mb',current['rss_deltas_mb'])
                self.assertEqual(current['markers_minutes'],[0,5,10,15,20,25,30])
            finally:
                tele.stop()
