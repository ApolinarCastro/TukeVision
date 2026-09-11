import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from scripts.run_multicamera import MulticameraRuntime
from src.app.runtime_qw04 import RuntimeQw04Integration
from src.behavior.contracts import BehaviorFeature, BehaviorResult, BehaviorSignal
from src.evidence.clips import EvidenceClipAdapter, TemporalClipCoordinator


CAMERAS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")


def config(*, codec="mpeg4"):
    return {
        "video": {"max_width": 640},
        "rtsp": {"open_timeout_ms": 8000, "frame_stall_timeout_s": 10.0},
        "evidence": {"enabled": True, "root": "data/runtime_evidence"},
        "clips": {
            "enabled": True,
            "pre_roll_seconds": 1,
            "post_roll_seconds": 1,
            "max_clip_duration_seconds": 2,
            "buffer_fps": 2,
            "max_frames_per_camera": 16,
            "max_pending_per_camera": 2,
            "max_clips_per_camera": 8,
            "container": "mp4",
            "codec": codec,
        },
        "review_export": {
            "enabled": True,
            "max_records_total": 8,
            "max_records_per_camera": 2,
            "max_records_per_signal_type": 8,
            "max_records_per_rule": 8,
            "max_candidates": 16,
        },
    }


def frame(value):
    return np.full((32, 32, 3), value, dtype=np.uint8)


def result_with_signal(camera_id, number):
    static_ref = f"{camera_id}/EVD-{number}/frame.jpg"
    feature = BehaviorFeature(
        f"BF-{number}",
        "event_count",
        3,
        f"TRK-{camera_id}-{number}",
        (camera_id,),
        "2026-08-18T10:00:00Z",
        "2026-08-18T10:00:02Z",
        (f"EVT-{number}",),
        (static_ref,),
    )
    signal = BehaviorSignal(
        f"BS-{camera_id}-{number}",
        "REPEATED_ACTIVITY",
        "repeated_activity",
        20.0,
        feature.subject_ref,
        (feature.feature_id,),
        (camera_id,),
        feature.window_start,
        feature.window_end,
        feature.evidence_refs,
    )
    behavior = BehaviorResult(
        feature.subject_ref,
        (camera_id,),
        (feature,),
        (signal,),
        evidence_refs=feature.evidence_refs,
    )
    return {
        "behavior": behavior,
        "track": SimpleNamespace(track_id=feature.subject_ref),
        "correlation": None,
        "event": SimpleNamespace(timestamp=feature.window_end),
        "observation": None,
        "evidence": {"relative_path": static_ref},
    }


class TestRuntimeQw04Integration(unittest.TestCase):
    def test_four_camera_frames_generate_isolated_clips_and_qw00_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "signal_review_records.jsonl"
            integration = RuntimeQw04Integration.from_config(
                config(), evidence_root=root, review_target=dataset
            )

            for index, camera_id in enumerate(CAMERAS, 1):
                integration.ingest(camera_id, 0.0, frame(index), 0, {})
                integration.ingest(camera_id, 0.5, frame(index), 1, {})
                integration.ingest(
                    camera_id, 1.0, frame(index), 2,
                    result_with_signal(camera_id, index),
                )
            for index, camera_id in enumerate(CAMERAS, 1):
                integration.ingest(camera_id, 1.5, frame(index), 3, {})
                integration.ingest(camera_id, 2.0, frame(index), 4, {})

            rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual({row["camera_id"] for row in rows}, set(CAMERAS))
            self.assertEqual(len({row["signal_id"] for row in rows}), 4)
            for row in rows:
                self.assertTrue(row["clip_available"])
                self.assertTrue(row["clip_evidence_ref"].startswith(f"clips/{row['camera_id']}/"))
                self.assertLessEqual(row["clip_duration_seconds"], 2.0)
                clip = root / row["clip_evidence_ref"]
                sidecar = json.loads(clip.with_suffix(".json").read_text(encoding="utf-8"))
                self.assertTrue(clip.is_file())
                self.assertTrue(EvidenceClipAdapter.verify(sidecar, root))
                self.assertEqual(sidecar["camera_id"], row["camera_id"])
                self.assertEqual(sidecar["signal_id"], row["signal_id"])

    def test_backend_failure_exports_static_fallback_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "signal_review_records.jsonl"
            integration = RuntimeQw04Integration.from_config(
                config(codec="codec-does-not-exist"),
                evidence_root=root,
                review_target=dataset,
            )

            integration.ingest("CAM-001", 0.0, frame(1), 0, {})
            integration.ingest(
                "CAM-001", 1.0, frame(1), 1,
                result_with_signal("CAM-001", 1),
            )
            summary = integration.close()

            rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertFalse(rows[0]["clip_available"])
            self.assertIsNone(rows[0]["clip_evidence_ref"])
            self.assertTrue(rows[0]["evidence_available"])
            self.assertEqual(summary["clips_unavailable"], 1)
            self.assertEqual(integration.coordinator.pending_count(), 0)
            self.assertEqual(integration.coordinator.buffer.window("CAM-001", 0, 2), ())

    def test_repeated_pending_signal_does_not_duplicate_review_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = Path(temporary) / "signal_review_records.jsonl"
            integration = RuntimeQw04Integration.from_config(
                config(), evidence_root=Path(temporary) / "runtime", review_target=dataset
            )
            signal_result = result_with_signal("CAM-001", 1)
            integration.ingest("CAM-001", 0.0, frame(1), 0, {})
            integration.ingest("CAM-001", 1.0, frame(1), 1, signal_result)
            integration.ingest("CAM-001", 1.5, frame(1), 2, signal_result)
            integration.ingest("CAM-001", 2.0, frame(1), 3, signal_result)

            rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["signal_id"], "BS-CAM-001-1")

    def test_pending_bound_skips_extra_signal_without_crowding_qw00(self):
        with tempfile.TemporaryDirectory() as temporary:
            cfg = config()
            cfg["clips"]["max_pending_per_camera"] = 1
            dataset = Path(temporary) / "signal_review_records.jsonl"
            integration = RuntimeQw04Integration.from_config(
                cfg, evidence_root=Path(temporary) / "runtime", review_target=dataset
            )
            integration.ingest("CAM-001", 0.0, frame(1), 0, {})
            integration.ingest(
                "CAM-001", 1.0, frame(1), 1,
                result_with_signal("CAM-001", 1),
            )
            integration.ingest(
                "CAM-001", 1.1, frame(1), 2,
                result_with_signal("CAM-001", 2),
            )
            summary = integration.close()

            rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["signal_id"] for row in rows], ["BS-CAM-001-1"])
            self.assertTrue(rows[0]["clip_available"])
            self.assertEqual(summary["signals_seen"], 2)
            self.assertEqual(summary["clips_unavailable"], 0)

    def test_from_config_reuses_existing_coordinator_and_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            review_target = Path(temporary) / "records.jsonl"
            integration = RuntimeQw04Integration.from_config(
                config(),
                evidence_root=Path(temporary) / "runtime",
                review_target=review_target,
            )
            self.assertIsInstance(integration.coordinator, TemporalClipCoordinator)
            self.assertIsInstance(integration.coordinator.adapter, EvidenceClipAdapter)
            self.assertEqual(integration.coordinator.adapter.review_target, review_target)


class TestOperationalRuntimeWiring(unittest.TestCase):
    def test_runtime_instantiates_qw04_once_without_second_capture(self):
        manager = Mock()
        bridge = Mock()
        with (
            patch("scripts.run_multicamera.SourceManager", return_value=manager) as manager_type,
            patch("scripts.run_multicamera.OperationalPipeline") as pipeline_type,
            patch("scripts.run_multicamera.UiController"),
            patch(
                "scripts.run_multicamera.RuntimeQw04Integration.from_config",
                return_value=bridge,
            ) as bridge_factory,
        ):
            runtime = MulticameraRuntime(config(), "password", "user")

        self.assertIs(runtime._manager, manager)
        self.assertEqual(manager_type.call_count, 1)
        self.assertEqual(manager.register_source.call_count, 4)
        self.assertEqual(pipeline_type.call_count, 1)
        self.assertEqual(
            pipeline_type.call_args.kwargs["review_target"],
            runtime.review_target,
        )
        self.assertEqual(bridge_factory.call_count, 1)
        source = Path("scripts/run_multicamera.py").read_text(encoding="utf-8")
        self.assertNotIn("VideoCapture", source)
        self.assertEqual(source.count("SourceManager()"), 1)

    def test_runtime_passes_the_exact_existing_frame_and_timestamp_to_qw04(self):
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime._trace = Mock()
        runtime._controller = Mock()
        runtime._qw04 = Mock()
        existing_frame = frame(7)
        snapshot = {"frame_index": 9, "timestamp": 12.5, "frame": existing_frame}
        result = result_with_signal("CAM-001", 1)

        runtime._handle_pipeline_result("CAM-001", snapshot, result)

        call = runtime._qw04.ingest.call_args
        self.assertEqual(call.args[:2], ("CAM-001", 12.5))
        self.assertIs(call.args[2], existing_frame)
        self.assertEqual(call.args[3], 9)
        self.assertIs(call.args[4], result)

    def test_clean_close_joins_pipeline_then_flushes_qw04(self):
        order = []

        class Thread:
            def join(self, timeout):
                order.append(("join", timeout))

            def is_alive(self):
                return False

        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime._stop = threading.Event()
        runtime._thread = Thread()
        runtime._qw04 = Mock()
        runtime._qw04.close.side_effect = lambda: order.append(("qw04", None))
        runtime._trace = Mock()

        runtime.close()

        self.assertTrue(runtime._stop.is_set())
        self.assertEqual(order, [("join", 15), ("qw04", None)])
        runtime._trace.export.assert_called_once()


if __name__ == "__main__":
    unittest.main()
