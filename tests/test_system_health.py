"""LOOP-0021: bounded host/camera health visible in the certified UI."""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.run_multicamera import MulticameraRuntime
from src.observability.system_health import SystemHealthSampler
from src.ui.tk_view import camera_health_text, health_header_text


CAMERAS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")


def host_values():
    return {
        "cpu_percent": 12.5,
        "ram_percent": 50.0,
        "ram_used_mb": 4096.0,
        "ram_total_mb": 8192.0,
        "disk_percent": 75.0,
        "disk_free_gb": 25.0,
    }


def camera(camera_id, state="OPEN", healthy=True):
    return SimpleNamespace(
        camera_id=camera_id,
        state=state,
        healthy=healthy,
        fps=15.0 if state == "OPEN" else 0.0,
        last_valid_frame_age_ms=500,
        stall_count=0,
        last_error="" if healthy else "STREAM_LOST",
    )


class FakeSourceManager:
    def __init__(self, states=None):
        self.states = states or {item: camera(item) for item in CAMERAS}
        self.health_calls = 0
        self.start_calls = 0
        self.snapshot_calls = 0

    def health(self, camera_id):
        self.health_calls += 1
        return self.states[camera_id]

    def start(self, camera_id):
        self.start_calls += 1
        raise AssertionError("health observer must not start a source")

    def snapshot(self, camera_id):
        self.snapshot_calls += 1
        raise AssertionError("health observer must not consume frames")


class MutableClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


def sampler(manager=None, reader=None, clock=None, interval=3.0):
    return SystemHealthSampler(
        manager or FakeSourceManager(),
        CAMERAS,
        sample_interval_seconds=interval,
        host_metrics_reader=reader or host_values,
        clock=clock or MutableClock(),
        timestamp_factory=lambda: "2026-08-18T22:00:00+00:00",
    )


class TestHostHealth(unittest.TestCase):
    def test_cpu_metric_is_visible(self):
        snapshot = sampler().snapshot(runtime_running=True)
        self.assertIn("CPU 12.5%", health_header_text(snapshot))

    def test_ram_percent_and_megabytes_are_visible(self):
        snapshot = sampler().snapshot(runtime_running=True)
        text = health_header_text(snapshot)
        self.assertIn("RAM 50.0%", text)
        self.assertIn("4096/8192 MB", text)

    def test_disk_percent_and_free_space_are_visible(self):
        snapshot = sampler().snapshot(runtime_running=True)
        text = health_header_text(snapshot)
        self.assertIn("DISK 75.0%", text)
        self.assertIn("25.0 GB free", text)

    def test_metric_failure_is_na_without_crashing(self):
        def unavailable():
            raise RuntimeError("host metrics unavailable")

        snapshot = sampler(reader=unavailable).snapshot(runtime_running=True)
        self.assertEqual(snapshot.global_health, "UNKNOWN")
        self.assertEqual(
            health_header_text(snapshot),
            "CPU N/A | RAM N/A | DISK N/A | HEALTH UNKNOWN",
        )

    def test_sampling_is_bounded_and_not_per_frame(self):
        clock = MutableClock()
        manager = FakeSourceManager()
        reader = Mock(side_effect=host_values)
        observer = sampler(manager, reader, clock, interval=3.0)

        first = observer.snapshot(runtime_running=True)
        for _ in range(100):
            self.assertIs(observer.snapshot(runtime_running=True), first)
        self.assertEqual(reader.call_count, 1)
        self.assertEqual(manager.health_calls, 4)

        clock.value = 3.1
        self.assertIsNot(observer.snapshot(runtime_running=True), first)
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(manager.health_calls, 8)


class TestCameraHealth(unittest.TestCase):
    def test_four_open_cameras_report_four_of_four(self):
        snapshot = sampler().snapshot(runtime_running=True)
        self.assertEqual(snapshot.online_camera_count, 4)
        self.assertEqual(snapshot.total_camera_count, 4)
        self.assertTrue(all(item.source_state == "OPEN" for item in snapshot.camera_health))

    def test_failed_camera_is_real_and_degraded(self):
        states = {item: camera(item) for item in CAMERAS}
        states["CAM-003"] = camera("CAM-003", "FAILED", False)
        snapshot = sampler(FakeSourceManager(states)).snapshot(runtime_running=True)
        failed = snapshot.camera("CAM-003")
        self.assertFalse(failed.online)
        self.assertEqual(snapshot.online_camera_count, 3)
        self.assertEqual(snapshot.global_health, "DEGRADED")
        self.assertIn("CAM-003 · RTSP FAILED", camera_health_text(failed))

    def test_stop_forces_zero_of_four_and_closed_without_historical_open(self):
        clock = MutableClock()
        manager = FakeSourceManager()
        reader = Mock(side_effect=host_values)
        observer = sampler(manager, reader, clock)
        observer.snapshot(runtime_running=True)
        stopped = observer.snapshot(runtime_running=False)

        self.assertEqual(stopped.online_camera_count, 0)
        self.assertTrue(all(item.source_state == "CLOSED" for item in stopped.camera_health))
        self.assertTrue(all("RTSP OPEN" not in camera_health_text(item) for item in stopped.camera_health))
        self.assertEqual(stopped.global_health, "OFFLINE")
        self.assertEqual(reader.call_count, 1)

    def test_observer_opens_no_connection_and_consumes_no_frame(self):
        manager = FakeSourceManager()
        sampler(manager).snapshot(runtime_running=True)
        self.assertEqual(manager.start_calls, 0)
        self.assertEqual(manager.snapshot_calls, 0)
        self.assertEqual(manager.health_calls, 4)


class TestGlobalAndUiHealth(unittest.TestCase):
    def test_global_health_ok_for_healthy_runtime(self):
        self.assertEqual(sampler().snapshot(runtime_running=True).global_health, "OK")

    def test_global_health_degraded_for_real_closed_source(self):
        states = {item: camera(item) for item in CAMERAS}
        states["CAM-002"] = camera("CAM-002", "CLOSED", False)
        snapshot = sampler(FakeSourceManager(states)).snapshot(runtime_running=True)
        self.assertEqual(snapshot.global_health, "DEGRADED")

    def test_global_health_unknown_when_required_host_metrics_are_unavailable(self):
        values = host_values()
        values["cpu_percent"] = None
        snapshot = sampler(reader=lambda: values).snapshot(runtime_running=True)
        self.assertEqual(snapshot.global_health, "UNKNOWN")

    def test_runtime_poll_exposes_cached_health_without_touching_pipeline(self):
        health = sampler().snapshot(runtime_running=True)
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime._stop = threading.Event()
        runtime._thread = SimpleNamespace(is_alive=lambda: True)
        runtime._controller = SimpleNamespace(poll_multicamera=lambda: {})
        runtime._qw04 = SimpleNamespace(summary=lambda: {})
        runtime._health = Mock()
        runtime._health.snapshot.return_value = health
        runtime._pipeline = Mock()

        state = runtime.poll_state()

        self.assertIs(state["system_health"], health)
        runtime._pipeline.assert_not_called()

    def test_certified_exact_frame_and_stop_helpers_remain_unchanged(self):
        from src.ui.tk_view import apply_stopped_state, select_panel_frame

        analytic = object()
        panel = SimpleNamespace(
            analytics_frame=analytic,
            analytics_frame_index=7,
            bboxes=((1, 2, 3, 4, 0.9),),
            track_bbox=None,
            frame=object(),
            frame_index=8,
            camera_id="CAM-001",
        )
        selected, frame_index, mode = select_panel_frame(panel)
        stopped = apply_stopped_state(panel)
        self.assertIs(selected, analytic)
        self.assertEqual((frame_index, mode), (7, "ANALITICA"))
        self.assertEqual((stopped["source_state"], stopped["online"]), ("CLOSED", False))


if __name__ == "__main__":
    unittest.main()
