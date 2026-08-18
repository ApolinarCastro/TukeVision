import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.evidence.clips import (
    BufferedFrame,
    EvidenceClipAdapter,
    TemporalClipCoordinator,
    TemporalFrameBuffer,
)


def frame(value: int = 0) -> np.ndarray:
    return np.full((32, 32, 3), value, dtype=np.uint8)


class TestTemporalFrameBuffer(unittest.TestCase):
    def test_buffer_order_isolated_and_bounded(self):
        buffer = TemporalFrameBuffer(pre_roll_seconds=2, max_frames_per_camera=3)
        for index in range(6):
            buffer.append("CAM-001", index, frame(index), index)
        buffer.append("CAM-002", 1, frame(9), 1)
        self.assertEqual(
            [item.frame_index for item in buffer.window("CAM-001", 3, 5)],
            [3, 4, 5],
        )
        self.assertEqual(len(buffer.window("CAM-002", 0, 2)), 1)

    def test_sampling_and_frame_copy_keep_memory_bounded_and_stable(self):
        buffer = TemporalFrameBuffer(
            pre_roll_seconds=1,
            retention_seconds=2,
            max_frames_per_camera=4,
            max_fps=2,
        )
        original = frame(3)
        self.assertTrue(buffer.append("CAM-001", 0.0, original, 0))
        self.assertFalse(buffer.append("CAM-001", 0.1, frame(4), 1))
        original[:] = 99
        self.assertEqual(int(buffer.window("CAM-001", 0, 1)[0].frame[0, 0, 0]), 3)

    def test_four_camera_state_is_isolated(self):
        buffer = TemporalFrameBuffer(pre_roll_seconds=2, max_frames_per_camera=8)
        for camera in ("CAM-001", "CAM-002", "CAM-003", "CAM-004"):
            buffer.append(camera, 1.0, frame(int(camera[-1])), 1)
        for camera in ("CAM-001", "CAM-002", "CAM-003", "CAM-004"):
            selected = buffer.window(camera, 0, 2)
            self.assertEqual(len(selected), 1)
            self.assertEqual(int(selected[0].frame[0, 0, 0]), int(camera[-1]))


class TestEvidenceClipAdapter(unittest.TestCase):
    def _frames(self, count: int = 6):
        return tuple(BufferedFrame(index / 5, frame(index), index) for index in range(count))

    def test_synthetic_clip_has_contract_sha_and_atomic_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            adapter = EvidenceClipAdapter(temporary, max_clips_per_camera=1, frame_rate=5)
            metadata = adapter.create_clip(
                camera_id="CAM-001",
                signal_id="BS-1",
                start_timestamp=0,
                end_timestamp=1,
                frames=self._frames(),
            )
            self.assertEqual(metadata["availability"], "AVAILABLE")
            self.assertEqual(metadata["camera_id"], "CAM-001")
            self.assertEqual(metadata["signal_id"], "BS-1")
            self.assertTrue(metadata["clip_evidence_ref"].endswith(".mp4"))
            self.assertTrue(EvidenceClipAdapter.verify(metadata, temporary))
            media = Path(temporary) / metadata["clip_evidence_ref"]
            sidecar = json.loads(media.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["sha256"], metadata["sha256"])
            self.assertEqual(list(media.parent.glob("*.tmp")), [])

    def test_empty_buffer_falls_back_without_false_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            metadata = EvidenceClipAdapter(temporary).create_clip(
                camera_id="CAM-001",
                signal_id="BS-1",
                start_timestamp=0,
                end_timestamp=1,
                frames=(),
            )
            self.assertEqual(metadata["availability"], "UNAVAILABLE")
            self.assertIsNone(metadata["clip_evidence_ref"])
            self.assertTrue(metadata["static_evidence_fallback"])
            self.assertFalse(EvidenceClipAdapter.verify(metadata, temporary))

    def test_duration_is_hard_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            adapter = EvidenceClipAdapter(
                temporary, max_clip_duration_seconds=2, frame_rate=5
            )
            frames = tuple(
                BufferedFrame(index / 5, frame(index), index) for index in range(21)
            )
            metadata = adapter.create_clip(
                camera_id="CAM-001", signal_id="BS-1",
                start_timestamp=0, end_timestamp=4, frames=frames,
            )
            self.assertEqual(metadata["availability"], "AVAILABLE")
            self.assertLessEqual(metadata["duration_seconds"], 2)
            self.assertLessEqual(metadata["frame_count"], 11)

    def test_retention_is_enforced_across_adapter_restarts(self):
        with tempfile.TemporaryDirectory() as temporary:
            for index in range(3):
                adapter = EvidenceClipAdapter(
                    temporary, max_clips_per_camera=2, frame_rate=5
                )
                metadata = adapter.create_clip(
                    camera_id="CAM-001", signal_id=f"BS-{index}",
                    start_timestamp=0, end_timestamp=1, frames=self._frames(),
                )
                self.assertEqual(metadata["availability"], "AVAILABLE")
            directory = Path(temporary) / "clips" / "CAM-001"
            self.assertEqual(len(list(directory.glob("*.mp4"))), 2)
            self.assertEqual(len(list(directory.glob("*.json"))), 2)

    def test_path_components_cannot_escape_evidence_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            metadata = EvidenceClipAdapter(temporary).create_clip(
                camera_id="../outside", signal_id="BS-1",
                start_timestamp=0, end_timestamp=1, frames=self._frames(),
            )
            self.assertEqual(metadata["availability"], "UNAVAILABLE")
            self.assertEqual(metadata["error"], "invalid_clip_contract")


class TestTemporalClipCoordinator(unittest.TestCase):
    def test_waits_for_post_roll_and_links_signal(self):
        with tempfile.TemporaryDirectory() as temporary:
            buffer = TemporalFrameBuffer(
                pre_roll_seconds=1, retention_seconds=2,
                max_frames_per_camera=16,
            )
            adapter = EvidenceClipAdapter(
                temporary, max_clip_duration_seconds=2, frame_rate=2
            )
            coordinator = TemporalClipCoordinator(
                buffer, adapter, pre_roll_seconds=1, post_roll_seconds=1
            )
            coordinator.append("CAM-001", 0.0, frame(0), 0)
            coordinator.append("CAM-001", 0.5, frame(1), 1)
            coordinator.append("CAM-001", 1.0, frame(2), 2)
            self.assertTrue(coordinator.request("CAM-001", "BS-1", 1.0))
            self.assertEqual(coordinator.append("CAM-001", 1.5, frame(3), 3), ())
            completed = coordinator.append("CAM-001", 2.0, frame(4), 4)
            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]["signal_id"], "BS-1")
            self.assertEqual(completed[0]["duration_seconds"], 2)
            self.assertEqual(completed[0]["availability"], "AVAILABLE")

    def test_pending_requests_and_flush_are_bounded_per_camera(self):
        with tempfile.TemporaryDirectory() as temporary:
            buffer = TemporalFrameBuffer(
                pre_roll_seconds=1, retention_seconds=2,
                max_frames_per_camera=16,
            )
            adapter = EvidenceClipAdapter(
                temporary, max_clip_duration_seconds=2, frame_rate=2
            )
            coordinator = TemporalClipCoordinator(
                buffer, adapter, pre_roll_seconds=1, post_roll_seconds=1,
                max_pending_per_camera=1,
            )
            coordinator.append("CAM-001", 1.0, frame(1), 1)
            self.assertTrue(coordinator.request("CAM-001", "BS-1", 1.0))
            self.assertFalse(coordinator.request("CAM-001", "BS-2", 1.1))
            completed = coordinator.flush()
            self.assertEqual(len(completed), 1)
            self.assertEqual(coordinator.pending_count(), 0)


if __name__ == "__main__":
    unittest.main()
