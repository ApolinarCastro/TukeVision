"""DEF-HEALTH-02: per-camera health derived from RUNTIME truth, not cached frames.

ONLINE   = source open + readable frames + last frame age <= threshold
DEGRADED = open/reconnecting but no frame yet, stale frame, or recoverable
           reconnect (a cached LAST FRAME is NEVER counted as ONLINE)
OFFLINE  = closed / failed / not healthy / no recent frame

Also proves the header denominator stays 15 (never 16) and that the tile
indicator colors follow the SAME health_state the header uses (BLOCK G).
"""

import unittest
from types import SimpleNamespace

from src.observability.system_health import (
    FRESH_FRAME_AGE_SECONDS,
    CameraOperationalHealth,
    SystemHealthSampler,
    health_state_for,
)
from src.ui.tk_view import COLORS, health_state_color


def host_values():
    return {
        "cpu_percent": 10.0,
        "ram_percent": 50.0,
        "ram_used_mb": 4096.0,
        "ram_total_mb": 8192.0,
        "disk_percent": 60.0,
        "disk_free_gb": 50.0,
    }


def camera(state="OPEN", healthy=True, fps=15.0, age_ms=50, readable=1,
           stall=0, last_error=""):
    return SimpleNamespace(
        state=state, healthy=healthy, fps=fps,
        last_valid_frame_age_ms=age_ms, stall_count=stall,
        readable_frames=readable, last_error=last_error,
    )


class Manager:
    def __init__(self, states):
        self._states = states

    def health(self, camera_id):
        return self._states[camera_id]


def sampler(states, threshold=FRESH_FRAME_AGE_SECONDS):
    ids = tuple(states)
    return SystemHealthSampler(
        Manager(states), ids,
        sample_interval_seconds=3.0,
        host_metrics_reader=host_values,
        fresh_frame_age_seconds=threshold,
        timestamp_factory=lambda: "2026-08-20T10:00:00+00:00",
    )


class TestHealthStateDerivation(unittest.TestCase):
    def test_open_fresh_frame_is_online(self):
        snap = sampler({"cam_01": camera()}).snapshot(runtime_running=True)
        item = snap.camera("cam_01")
        self.assertEqual(item.health_state, "ONLINE")
        self.assertTrue(item.online)

    def test_open_but_no_frames_ever_is_degraded_not_online(self):
        # last_valid_frame_age_ms == 0 means "no frame yet"; readable_frames 0
        # must NOT be counted ONLINE (DEF-HEALTH-02 / BLOCK E).
        snap = sampler({
            "cam_01": camera(state="OPEN", age_ms=0, readable=0),
        }).snapshot(runtime_running=True)
        item = snap.camera("cam_01")
        self.assertEqual(item.health_state, "DEGRADED")
        self.assertFalse(item.online)

    def test_open_stale_frame_is_degraded_not_online(self):
        snap = sampler({
            "cam_01": camera(age_ms=int((FRESH_FRAME_AGE_SECONDS + 1.0) * 1000)),
        }).snapshot(runtime_running=True)
        item = snap.camera("cam_01")
        self.assertEqual(item.health_state, "DEGRADED")
        self.assertFalse(item.online)

    def test_cached_last_frame_never_online_when_source_closed(self):
        # A frozen LAST FRAME must never paint ONLINE when the source is
        # closed/failed: it is evidence of history, not of liveness.
        snap = sampler({
            "cam_01": camera(state="CLOSED", healthy=False, age_ms=500, readable=5),
        }).snapshot(runtime_running=True)
        item = snap.camera("cam_01")
        self.assertEqual(item.health_state, "OFFLINE")
        self.assertFalse(item.online)

    def test_reconnecting_is_never_online(self):
        snap = sampler({
            "cam_01": camera(state="RECONNECTING", age_ms=500, readable=1),
        }).snapshot(runtime_running=True)
        self.assertEqual(snap.camera("cam_01").health_state, "RECONNECTING")
        self.assertFalse(snap.camera("cam_01").online)

    def test_failed_is_offline(self):
        snap = sampler({
            "cam_01": camera(state="FAILED", healthy=False, age_ms=500, readable=1),
        }).snapshot(runtime_running=True)
        self.assertEqual(snap.camera("cam_01").health_state, "OFFLINE")
        self.assertFalse(snap.camera("cam_01").online)

    def test_online_count_excludes_degraded_and_offline(self):
        states = {
            "cam_01": camera(),                                    # ONLINE
            "cam_02": camera(age_ms=15000),                        # DEGRADED stale
            "cam_03": camera(state="CLOSED", healthy=False),       # OFFLINE
            "cam_04": camera(readable=0, age_ms=0),                # DEGRADED no frames
        }
        snap = sampler(states).snapshot(runtime_running=True)
        self.assertEqual(snap.online_camera_count, 1)
        self.assertEqual(snap.total_camera_count, 4)

    def test_stopped_runtime_marks_everything_offline(self):
        snap = sampler({"cam_01": camera()}).snapshot(runtime_running=False)
        item = snap.camera("cam_01")
        self.assertEqual(item.health_state, "OFFLINE")
        self.assertFalse(item.online)
        self.assertEqual(snap.online_camera_count, 0)

    def test_threshold_is_configurable(self):
        # With a very small threshold even a 50ms-old frame is DEGRADED.
        snap = sampler(
            {"cam_01": camera(age_ms=50)}, threshold=0.02
        ).snapshot(runtime_running=True)
        self.assertEqual(snap.camera("cam_01").health_state, "DEGRADED")
        self.assertFalse(snap.camera("cam_01").online)

    def test_denominator_is_15_never_16(self):
        ids = {f"cam_{i:02d}": camera() for i in range(1, 16)}
        snap = sampler(ids).snapshot(runtime_running=True)
        self.assertEqual(snap.total_camera_count, 15)
        self.assertEqual(len(snap.camera_health), 15)


class TestHealthStatePureFunction(unittest.TestCase):
    def test_health_state_for_corner_cases(self):
        self.assertEqual(
            health_state_for("OPEN", healthy=True, age_seconds=0.05), "ONLINE"
        )
        self.assertEqual(
            health_state_for("OPEN", healthy=True, age_seconds=9.0), "DEGRADED"
        )
        self.assertEqual(
            health_state_for("OPEN", healthy=True, age_seconds=0.05,
                             readable_frames=0), "DEGRADED"
        )
        self.assertEqual(
            health_state_for("RECONNECTING", healthy=True, age_seconds=0.05),
            "RECONNECTING",
        )
        self.assertEqual(
            health_state_for("CLOSED", healthy=False, age_seconds=0.05), "OFFLINE"
        )


class TestTileHeaderCorrelation(unittest.TestCase):
    def test_indicator_colors_follow_health_state(self):
        # BLOCK G: GREEN=ONLINE, AMBER=DEGRADED, GRAY=OFFLINE using the SAME
        # health_state that composes the header online count.
        self.assertEqual(health_state_color("ONLINE"), COLORS["online"])
        self.assertEqual(health_state_color("DEGRADED"), COLORS["degraded"])
        self.assertEqual(health_state_color("RECONNECTING"), COLORS["degraded"])
        self.assertEqual(health_state_color("OFFLINE"), COLORS["offline"])
        self.assertEqual(health_state_color("UNKNOWN"), COLORS["offline"])

    def test_online_flag_matches_health_state(self):
        for state in ("ONLINE", "DEGRADED", "OFFLINE", "UNKNOWN"):
            item = CameraOperationalHealth(
                "cam_01", "OPEN", state == "ONLINE", 15.0, 0.05, 0,
                "", state,
            )
            self.assertEqual(item.online, item.health_state == "ONLINE")


if __name__ == "__main__":
    unittest.main()