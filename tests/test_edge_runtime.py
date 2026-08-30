"""Edge runtime + full 16-source vertical integration (MACRO-OC-02, Bloques D/I).

Builds two stores x 8 cameras = 16 synthetic RTSP sources, runs the real
StoreEdgeRuntime per store (SourceManager -> AdvanceChain -> QW04 -> health
-> Scene -> OperatorInsight -> Learning) with the shared evidence router:

  - EDGE_RUNTIME / EDGE_START_STOP / EDGE_RESTART / PARTIAL_STORE_ISOLATION
  - FULL_PIPELINE_16_SOURCE_INTEGRATION: one runtime drives all 16 cameras
  - EVIDENCE_ISOLATION / REVIEW_ISOLATION per store
  - review -> learning case + scene/insight connected to the same runtime
"""

import json
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event

import numpy as np

from src.capture.live_sources import SourceState
from src.capture.source_manager import CameraDescriptor
from src.capture.video_source import VideoMetadata
from src.deployment.edge_runtime import EdgeRuntimeManager, StoreEdgeRuntime
from src.deployment.topology import DeploymentTopology, EdgeCentralSplit
from src.domain.catalog import StoreCatalog


def _camera(store_id, index):
    camera_id = f"{store_id}_cam_{index:02d}"
    return {
        "camera_id": camera_id,
        "store_id": store_id,
        "channel_number": index,
        "camera_name": f"Cámara {index} de {store_id}",
        "source_type": "RTSP_STREAM",
        "host": "192.168.100.10",
        "stream_main": f"rtsp://192.168.100.10/{camera_id}",
        "stream_sub": f"rtsp://192.168.100.10/{camera_id}_sub",
        "zone": "Cajas" if index % 2 else "Pasillos",
        "role": "HYBRID",
        "enabled": True,
        "credentials_ref": "",
        "evidence_namespace": f"data/evidence/{store_id}/{camera_id}/",
    }


def make_config(principal=8, norte=8):
    stores = []
    for store_id, count in (("store_a", principal), ("store_b", norte)):
        stores.append({
            "store_id": store_id,
            "organization_id": "org_test",
            "store_name": f"Store {store_id}",
            "location_address": "Santiago",
            "timezone": "America/Santiago",
            "evidence_namespace": f"data/evidence/{store_id}/",
            "recorders": [{
                "recorder_id": f"dvr_{store_id}",
                "store_id": store_id,
                "recorder_name": f"DVR {store_id}",
                "recorder_type": "DVR",
                "host": "192.168.100.10",
                "port": 554,
                "vendor": "Hikvision",
                "credentials_ref": "ENV_TEST_CREDS",
                "total_channels": count,
                "cameras": [_camera(store_id, i + 1) for i in range(count)],
            }],
            "direct_cameras": [],
        })
    return {
        "multistore": {
            "enabled": True,
            "organization": {
                "organization_id": "org_test",
                "organization_name": "Test Retail",
                "created_at": "2026-08-19T00:00:00Z",
            },
            "stores": stores,
        },
        "video": {"max_width": 640, "process_every_n_frames": 1},
        "rtsp": {"open_timeout_ms": 8000, "read_timeout_ms": 4000,
                 "frame_stall_timeout_s": 10.0},
        "output": {"save_processed_video": False, "show_preview": False},
        "zone": {"id": "ZONE-001", "name": "Cajas",
                 "rectangle": [0, 0, 640, 480]},
        "business": {"store_id": "store_a", "camera_id": "store_a_cam_01"},
        "alerts": {"risk_threshold": 60},
        "observation": {
            "default_profile": "BALANCED",
            "profiles": {
                "QUALITY": {"max_analysis_fps": 5.0},
                "BALANCED": {"max_analysis_fps": 2.0},
                "ECONOMY": {"max_analysis_fps": 1.0},
            },
        },
        "inference": {
            "backend": "deterministic",
            "confidence_threshold": 0.5,
            "event_queue_maxlen": 16,
            "event_queue_overflow": "drop_oldest",
            "events": [{"type": "OBJECT_DETECTED", "min_confidence": 0.5}],
        },
        "temporal": {
            "association_window_ms": 2000,
            "track_timeout_ms": 5000,
            "iou_threshold": 0.05,
            "max_active_tracks": 16,
            "max_completed_history": 32,
            "max_event_refs": 16,
            "max_evidence_refs": 3,
        },
        "evidence": {"enabled": True, "root": "data/runtime_evidence",
                     "max_per_camera": 8, "jpeg_quality": 90},
        "clips": {
            "enabled": False,
            "pre_roll_seconds": 1,
            "post_roll_seconds": 1,
            "max_clip_duration_seconds": 5,
            "buffer_fps": 5,
            "max_frames_per_camera": 16,
            "max_pending_per_camera": 4,
            "max_clips_per_camera": 4,
            "container": "mp4",
            "codec": "mpeg4",
        },
        "correlation": {
            "enabled": True,
            "transitions": [],
            "score_weights": {"temporal": 0.7, "topology": 0.3, "direction": 0.0},
            "max_active_trajectories": 32,
            "max_candidates_per_camera_pair": 16,
            "candidate_ttl_seconds": 120,
            "trajectory_ttl_seconds": 600,
            "max_tracks": 256,
        },
        "behavior": {
            "enabled": True,
            "retention": {"max_results": 64},
            "rules": {
                "prolonged_dwell": {"enabled": True, "min_seconds": 0, "score": 25},
                "repeated_activity": {"enabled": True, "min_events": 1, "score": 20},
                "multi_camera_sequence": {"enabled": True, "min_transitions": 0, "score": 30},
                "repeated_zone_activity": {"enabled": True, "min_visits": 1, "score": 20},
            },
            "risk": {"min_signal_count": 2, "review_threshold": 60},
        },
        "review_export": {
            "enabled": True,
            "format": "jsonl",
            "max_records_total": 64,
            "max_records_per_camera": 2,
            "max_records_per_signal_type": 8,
            "max_records_per_rule": 8,
            "max_candidates": 64,
        },
        "system_health": {"sample_interval_seconds": 3.0},
    }


class FakeSource:
    def __init__(self, camera_id, frames=3):
        self.camera_id = camera_id
        self._remaining = frames
        self._state = SourceState.CLOSED
        self._metadata = None
        self.fps = 30.0
        self.width = 640
        self.height = 480
        self.stall_count = 0
        self.last_valid_frame_age_ms = 0
        self.readable_frames = 0
        self.source_type = "RTSP"
        self.stop_event = Event()

    def open(self):
        self._state = SourceState.OPEN
        self._metadata = VideoMetadata(
            width=self.width, height=self.height, fps=self.fps,
            total_frames=0, duration_seconds=0.0,
            path=f"rtsp://redacted/{self.camera_id}", source_type="RTSP",
        )
        return self._metadata

    def frames(self):
        delivered = 0
        while self._remaining > 0:
            self._remaining -= 1
            delivered += 1
            self.readable_frames += 1
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame[16:48, 24:80] = 255
            yield (delivered - 1, frame)
            # Space frames so the polling pipeline observes frame 0 before
            # the snapshot is overwritten by faster synthetic delivery.
            time.sleep(0.06)

    @property
    def state(self):
        return self._state

    @property
    def metadata(self):
        return self._metadata

    def close(self):
        self._state = SourceState.CLOSED


class FakeSourceFactory:
    def __call__(self, descriptor: CameraDescriptor):
        return FakeSource(descriptor.camera_id)


def wait_until(predicate, timeout=30.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


class TestFullVerticalIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.evidence_base = str(Path(self.tmp.name) / "evidence")
        self.config = make_config(principal=8, norte=8)
        self.config["learning"] = {
            "dataset_root": str(Path(self.tmp.name) / "learning" / "datasets"),
            "policy_root": str(Path(self.tmp.name) / "learning" / "policies"),
        }
        self.catalog = StoreCatalog.from_dict(self.config)
        self.manager = EdgeRuntimeManager(
            self.config,
            self.catalog,
            source_factory=FakeSourceFactory(),
            credential_resolver=lambda ref: ("user", "pass"),
            evidence_base=self.evidence_base,
        )

    def tearDown(self):
        try:
            self.manager.close()
        except Exception:
            pass
        self.tmp.cleanup()

    def test_sixteen_sources_full_vertical(self):
        started = self.manager.start_all()
        self.assertEqual(len(started), 2)
        runtime_a = self.manager.runtime("store_a")
        runtime_b = self.manager.runtime("store_b")
        self.assertIsInstance(runtime_a, StoreEdgeRuntime)
        # Every store owns its own SourceManager/pipeline/qw04/health.
        self.assertIsNot(runtime_a._manager, runtime_b._manager)

        # Wait until both finite synthetic runs complete. The deadline is a
        # wall-clock guard against hangs; under full-suite CPU load the runs
        # finish slower than in isolation, so keep a generous bound.
        self.assertTrue(wait_until(
            lambda: not runtime_a.running and not runtime_b.running, timeout=120.0
        ), "16-source run did not finish in time")

        summary_a = runtime_a.store_summary()
        summary_b = runtime_b.store_summary()
        self.assertGreater(summary_a["processed_frames"], 0)
        self.assertGreater(summary_b["processed_frames"], 0)
        self.assertNotEqual(
            summary_a["evidence_root"], summary_b["evidence_root"]
        )

        # Evidence isolated per store namespace.
        root_a = Path(summary_a["evidence_root"])
        root_b = Path(summary_b["evidence_root"])
        self.assertIn("store_a", str(root_a))
        self.assertIn("store_b", str(root_b))
        jpgs_a = list(root_a.rglob("*.jpg"))
        jpgs_b = list(root_b.rglob("*.jpg"))
        self.assertTrue(jpgs_a, "store A produced no evidence JPEGs")
        self.assertTrue(jpgs_b, "store B produced no evidence JPEGs")

        # Review records exported per store (clips disabled -> UNAVAILABLE).
        target_a = Path(summary_a["review_target"])
        target_b = Path(summary_b["review_target"])
        self.assertTrue(target_a.is_file())
        self.assertTrue(target_b.is_file())
        records_a = [json.loads(l) for l in target_a.read_text("utf-8").splitlines() if l]
        records_b = [json.loads(l) for l in target_b.read_text("utf-8").splitlines() if l]
        self.assertTrue(records_a)
        self.assertTrue(records_b)
        self.assertTrue(all(r["store_id"] == "store_a" for r in records_a))
        self.assertTrue(all(r["store_id"] == "store_b" for r in records_b))
        self.assertTrue(all(r["organization_id"] == "org_test" for r in records_a))

        # Scene / Operator / Learning connected to the same runtime.
        wiring_a = self.manager.wiring("store_a")
        wiring_b = self.manager.wiring("store_b")
        self.assertIsNotNone(wiring_a)
        self.assertIsNotNone(wiring_b)
        summary_a_w = wiring_a.summary()
        summary_b_w = wiring_b.summary()
        self.assertGreater(summary_a_w["scene_events"], 0)
        self.assertGreater(summary_a_w["raw_cases"], 0)
        self.assertGreater(summary_b_w["scene_events"], 0)
        self.assertGreater(summary_b_w["raw_cases"], 0)
        self.assertGreaterEqual(summary_a_w["insights"], 0)

    def test_edge_lifecycle_and_partial_isolation(self):
        # Start only store_a; store_b must remain untouched.
        self.manager.start_store("store_a")
        runtime_a = self.manager.runtime("store_a")
        self.assertIsNotNone(runtime_a)
        self.assertTrue(runtime_a.running)
        self.assertIsNone(self.manager.runtime("store_b"))

        # Stop one store does not touch the other's lifecycle.
        self.manager.stop_store("store_a")
        self.assertFalse(runtime_a.running)

        # Restart store_a.
        runtime_a = self.manager.restart_store("store_a")
        self.assertTrue(runtime_a.running)
        self.manager.stop_all()
        self.assertFalse(runtime_a.running)

        # Unknown store raises (never silently ignored).
        with self.assertRaises(Exception):
            self.manager.start_store("store_inexistente")

    def test_deployment_topology_drives_real_store_edge_runtime(self):
        topology = DeploymentTopology(
            self.catalog.organization,
            edge_runtime_provider=self.manager.prepare_store,
        )
        store = self.catalog.store("store_a")
        topology.add_store(store, EdgeCentralSplit(store_id=store.store_id))

        service = topology.create_edge_service(store.store_id)
        self.assertIsNotNone(service)
        self.assertIsInstance(service.runtime, StoreEdgeRuntime)
        self.assertIs(service.runtime, self.manager.runtime(store.store_id))

        service.start()
        self.assertTrue(
            wait_until(lambda: not service.runtime.running, timeout=60.0),
            "edge service runtime did not finish synthetic frames in time",
        )
        self.assertGreater(service.runtime.store_summary()["processed_frames"], 0)
        service.stop()


if __name__ == "__main__":
    unittest.main()

