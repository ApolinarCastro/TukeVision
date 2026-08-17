"""LOOP-0018V operational pipeline and persistent evidence contracts."""

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

from src.app.advance_chain import AdvanceChain
from src.app.operational_pipeline import OperationalPipeline
from src.evidence.persistent import PersistentEvidenceStore


FRAME = np.zeros((80, 120, 3), dtype="uint8")
FRAME[10:60, 30:90] = 255


def config(root):
    return {
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
            "event_queue_maxlen": 4,
            "event_queue_overflow": "drop_oldest",
            "events": [{"type": "OBJECT_DETECTED", "min_confidence": 0.5}],
        },
        "temporal": {
            "association_window_ms": 2000,
            "track_timeout_ms": 5000,
            "iou_threshold": 0.05,
            "max_active_tracks": 8,
            "max_completed_history": 8,
            "max_event_refs": 4,
            "max_evidence_refs": 3,
        },
        "evidence": {
            "enabled": True,
            "root": root,
            "max_per_camera": 2,
            "jpeg_quality": 90,
        },
    }


class FakeManager:
    def __init__(self, cameras):
        self.cameras = list(cameras)
        self.snapshots = {}
        self.running = {camera: False for camera in cameras}
        self.closed = False

    def list_sources(self):
        return [{"camera_id": c, "running": self.running[c]} for c in self.cameras]

    def health(self, camera_id):
        return type("Health", (), {"fps": 15.0})()

    def start(self, camera_id):
        self.running[camera_id] = True

    def stop(self, camera_id):
        self.running[camera_id] = False

    def snapshot(self, camera_id):
        return self.snapshots.get(camera_id)

    def close_all(self):
        self.closed = True
        for camera in self.cameras:
            self.running[camera] = False


class TestPersistentEvidence(unittest.TestCase):
    def test_atomic_relative_sha_and_bounded_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "runtime"
            ids = iter(("EVD-001", "EVD-002", "EVD-003"))
            store = PersistentEvidenceStore(str(root), 2, id_factory=lambda: next(ids))
            refs = []
            for index in range(3):
                record = store.persist_selected(
                    FRAME, camera_id="CAM-01", timestamp=f"2026-08-17T00:00:0{index}Z",
                    producer="activity-policy", observation_ref=f"OBS-{index}",
                )
                refs.append(record["relative_path"])
            self.assertFalse(Path(refs[-1]).is_absolute())
            self.assertFalse(store.resolve(refs[0]).exists())
            self.assertTrue(store.verify(refs[-1]))
            metadata = json.loads(
                store.resolve(refs[-1]).with_name("metadata.json").read_text("utf-8")
            )
            self.assertEqual(
                metadata["sha256"], hashlib.sha256(store.resolve(refs[-1]).read_bytes()).hexdigest()
            )
            self.assertEqual(len(list((root / "CAM-01").iterdir())), 2)


class TestEndToEndOperationalContract(unittest.TestCase):
    def test_four_camera_trace_and_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "runtime")
            cameras = ["CAM-01", "CAM-02", "CAM-03", "CAM-04"]
            manager = FakeManager(cameras)
            cfg = config("data/runtime_evidence")
            store = PersistentEvidenceStore(root, 2)
            chain = AdvanceChain.build(cfg, manager, evidence_store=store)
            runtime = OperationalPipeline(cfg, manager, chain=chain)
            runtime.start()
            results = {}
            for camera in cameras:
                manager.snapshots[camera] = {
                    "camera_id": camera, "frame_index": 0, "frame": FRAME.copy(),
                    "state": "OPEN", "fps": 15.0, "resolution": "120x80",
                }
                results[camera] = runtime.process_available(camera)

            for camera, result in results.items():
                self.assertEqual(result["observation"].camera_id, camera)
                self.assertEqual(result["event"].camera_id, camera)
                self.assertEqual(result["track"].camera_id, camera)
                self.assertEqual(result["temporal_activity"].source_id, camera)
                self.assertEqual(result["temporal_activity"].track_id, result["track"].track_id)
                self.assertEqual(result["event"].observation_ref, result["observation"].observation_id)
                self.assertEqual(result["track"].event_refs[-1], result["event"].event_id)
                self.assertEqual(result["event"].evidence_ref, result["evidence"]["relative_path"])
                self.assertEqual(result["track"].evidence_refs["latest"], result["event"].evidence_ref)
                self.assertTrue(chain._evidence_store.verify(result["event"].evidence_ref))
                self.assertEqual(result["evidence"]["event_ref"], result["event"].event_id)
                self.assertEqual(result["evidence"]["track_ref"], result["track"].track_id)
                self.assertEqual(result["evidence"]["inference_ref"], result["event"].inference_ref)
                observation_ts = datetime.fromisoformat(result["observation"].timestamp.replace("Z", "+00:00"))
                event_ts = datetime.fromisoformat(result["event"].timestamp.replace("Z", "+00:00"))
                self.assertGreaterEqual(event_ts, observation_ts)
                self.assertEqual(result["track"].last_seen_at, result["event"].timestamp)

            manager.stop("CAM-03")
            manager.snapshots["CAM-01"]["frame_index"] = 8
            self.assertIsNotNone(runtime.process_available("CAM-01"))
            self.assertTrue(manager.running["CAM-01"])
            self.assertFalse(manager.running["CAM-03"])
            all_tracks = {result["track"].track_id for result in results.values()}
            self.assertEqual(len(all_tracks), 4)
            runtime.close()
            self.assertTrue(manager.closed)

    def test_policy_skip_does_not_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = FakeManager(["CAM-01"])
            cfg = config("data/runtime_evidence")
            chain = AdvanceChain.build(
                cfg, manager,
                evidence_store=PersistentEvidenceStore(str(Path(tmp) / "runtime"), 2),
            )
            chain.register_from_source_manager()
            result = chain.feed("CAM-01", 1, 15.0, FRAME)
            self.assertIsNone(result["observation"])
            self.assertIsNone(result["evidence"])
            self.assertFalse((Path(tmp) / "runtime").exists())
            chain.close()


if __name__ == "__main__":
    unittest.main()
