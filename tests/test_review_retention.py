"""LOOP-0020: pending human-review evidence survives bounded retention."""

import json
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.review_behavior_signals import save
from src.evidence.clips import BufferedFrame, EvidenceClipAdapter
from src.evidence.persistent import PersistentEvidenceStore


FRAME = np.full((24, 24, 3), 127, dtype=np.uint8)
CAMERAS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")
BLOCKED = "RETENTION_CAPACITY_BLOCKED_BY_PROTECTED_REVIEWS"


def clip_frames(value: int = 1) -> tuple[BufferedFrame, ...]:
    frame = np.full((24, 24, 3), value, dtype=np.uint8)
    return tuple(BufferedFrame(index / 5, frame, index) for index in range(6))


def write_dataset(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def review_case(
    *,
    suffix: str,
    camera_id: str,
    static_ref: str,
    clip_ref: str,
    state: str | None = None,
) -> dict:
    row = {
        "review_id": f"SRR-{suffix}",
        "signal_id": f"BS-{suffix}",
        "camera_id": camera_id,
        "track_id": f"TRK-{camera_id}-{suffix}",
        "human_classification": "NOT_REVIEWED",
        "evidence_refs": [static_ref],
        "clip_available": True,
        "clip_evidence_ref": clip_ref,
    }
    if state is not None:
        row["review_state"] = state
    return row


def mark_reviewed(dataset: Path, row: dict) -> None:
    save(
        dataset.parent / "human_review_matrix.csv",
        [{
            "review_id": row["review_id"],
            "signal_id": row["signal_id"],
            "camera_id": row["camera_id"],
            "track_id": row["track_id"],
            "classification": "USEFUL_SIGNAL",
            "review_timestamp": "2026-08-18T22:00:00+00:00",
            "evidence_ref": row["evidence_refs"][-1],
            "clip_evidence_ref": row["clip_evidence_ref"],
            "static_evidence_sufficient": "YES",
            "temporal_evidence_sufficient": "YES",
            "comparison_notes": "CONTROLLED_RETENTION_FIXTURE",
        }],
    )


class TestReviewRetentionLifecycle(unittest.TestCase):
    def test_selected_case_protects_jpeg_clip_and_sidecar_then_review_releases(self):
        """T1-T7/T9: protect the case jointly, then release it after review."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "review" / "signal_review_records.jsonl"
            ids = iter(("EVD-A", "EVD-B", "EVD-C", "EVD-D"))
            store = PersistentEvidenceStore(
                str(root), 2, id_factory=lambda: next(ids), review_target=dataset
            )
            clips = EvidenceClipAdapter(
                root, max_clips_per_camera=2, frame_rate=5, review_target=dataset
            )

            static_a = store.persist_selected(
                FRAME, camera_id="CAM-001", timestamp="1", producer="fixture"
            )
            clip_a = clips.create_clip(
                camera_id="CAM-001", signal_id="BS-A",
                start_timestamp=0, end_timestamp=1, frames=clip_frames(1),
            )
            case_a = review_case(
                suffix="A", camera_id="CAM-001",
                static_ref=static_a["relative_path"],
                clip_ref=clip_a["clip_evidence_ref"],
                state="SELECTED_FOR_REVIEW",
            )
            write_dataset(dataset, [case_a])
            static_a_path = store.resolve(static_a["relative_path"])
            clip_a_path = root / clip_a["clip_evidence_ref"]
            os.utime(static_a_path.parent, (1, 1))
            os.utime(clip_a_path, (1, 1))

            unprotected_static = []
            unprotected_clips = []
            for suffix, value in (("B", 2), ("C", 3)):
                record = store.persist_selected(
                    FRAME, camera_id="CAM-001", timestamp=value, producer="fixture"
                )
                unprotected_static.append(store.resolve(record["relative_path"]))
                metadata = clips.create_clip(
                    camera_id="CAM-001", signal_id=f"BS-{suffix}",
                    start_timestamp=0, end_timestamp=1, frames=clip_frames(value),
                )
                unprotected_clips.append(root / metadata["clip_evidence_ref"])

            self.assertTrue(static_a_path.is_file())
            self.assertTrue(static_a_path.with_name("metadata.json").is_file())
            self.assertTrue(clip_a_path.is_file())
            self.assertTrue(clip_a_path.with_suffix(".json").is_file())
            self.assertEqual(sum(path.is_file() for path in unprotected_static), 1)
            self.assertEqual(sum(path.is_file() for path in unprotected_clips), 1)

            mark_reviewed(dataset, case_a)
            store.persist_selected(
                FRAME, camera_id="CAM-001", timestamp="4", producer="fixture"
            )
            clips.create_clip(
                camera_id="CAM-001", signal_id="BS-D",
                start_timestamp=0, end_timestamp=1, frames=clip_frames(4),
            )

            self.assertFalse(static_a_path.exists())
            self.assertFalse(static_a_path.with_name("metadata.json").exists())
            self.assertFalse(clip_a_path.exists())
            self.assertFalse(clip_a_path.with_suffix(".json").exists())

    def test_restart_reconstructs_pending_protection_from_review_files(self):
        """T10: no in-memory lock is required after process restart."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "review" / "signal_review_records.jsonl"
            first_store = PersistentEvidenceStore(
                str(root), 2, id_factory=lambda: "EVD-A", review_target=dataset
            )
            first_clips = EvidenceClipAdapter(
                root, max_clips_per_camera=2, frame_rate=5, review_target=dataset
            )
            static_a = first_store.persist_selected(
                FRAME, camera_id="CAM-001", timestamp="1", producer="fixture"
            )
            clip_a = first_clips.create_clip(
                camera_id="CAM-001", signal_id="BS-A",
                start_timestamp=0, end_timestamp=1, frames=clip_frames(),
            )
            case_a = review_case(
                suffix="A", camera_id="CAM-001",
                static_ref=static_a["relative_path"],
                clip_ref=clip_a["clip_evidence_ref"], state="PENDING",
            )
            write_dataset(dataset, [case_a])

            restarted_store = PersistentEvidenceStore(
                str(root), 1, id_factory=lambda: "EVD-B", review_target=dataset
            )
            restarted_clips = EvidenceClipAdapter(
                root, max_clips_per_camera=1, frame_rate=5, review_target=dataset
            )

            self.assertIsNone(restarted_store.persist_selected(
                FRAME, camera_id="CAM-001", timestamp="2", producer="fixture"
            ))
            rejected_clip = restarted_clips.create_clip(
                camera_id="CAM-001", signal_id="BS-B",
                start_timestamp=0, end_timestamp=1, frames=clip_frames(2),
            )
            self.assertEqual(rejected_clip["availability"], "UNAVAILABLE")
            self.assertEqual(rejected_clip["error"], BLOCKED)
            self.assertTrue(first_store.resolve(static_a["relative_path"]).is_file())
            self.assertTrue((root / clip_a["clip_evidence_ref"]).is_file())

    def test_all_protected_capacity_is_explicit_and_deletes_nothing(self):
        """T11: over-capacity protected evidence blocks instead of disappearing."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "review" / "signal_review_records.jsonl"
            ids = iter(("EVD-A", "EVD-B"))
            setup_store = PersistentEvidenceStore(
                str(root), 2, id_factory=lambda: next(ids), review_target=dataset
            )
            setup_clips = EvidenceClipAdapter(
                root, max_clips_per_camera=2, frame_rate=5, review_target=dataset
            )
            cases = []
            static_paths = []
            clip_paths = []
            for suffix, value in (("A", 1), ("B", 2)):
                static = setup_store.persist_selected(
                    FRAME, camera_id="CAM-001", timestamp=value, producer="fixture"
                )
                clip = setup_clips.create_clip(
                    camera_id="CAM-001", signal_id=f"BS-{suffix}",
                    start_timestamp=0, end_timestamp=1, frames=clip_frames(value),
                )
                cases.append(review_case(
                    suffix=suffix, camera_id="CAM-001",
                    static_ref=static["relative_path"],
                    clip_ref=clip["clip_evidence_ref"],
                ))
                static_paths.append(setup_store.resolve(static["relative_path"]))
                clip_paths.append(root / clip["clip_evidence_ref"])
            write_dataset(dataset, cases)

            store = PersistentEvidenceStore(str(root), 1, review_target=dataset)
            clips = EvidenceClipAdapter(root, max_clips_per_camera=1, review_target=dataset)
            self.assertEqual(store.enforce_retention("CAM-001"), BLOCKED)
            self.assertEqual(clips.enforce_retention("CAM-001"), BLOCKED)
            self.assertEqual(store.retention_status("CAM-001"), BLOCKED)
            self.assertEqual(clips.retention_status("CAM-001"), BLOCKED)
            self.assertTrue(all(path.is_file() for path in static_paths))
            self.assertTrue(all(path.is_file() for path in clip_paths))
            self.assertTrue(all(path.with_suffix(".json").is_file() for path in clip_paths))

    def test_four_camera_retention_is_isolated(self):
        """T8: pressure in one camera cannot evict protected cases in another."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "review" / "signal_review_records.jsonl"
            ids = iter(tuple(f"EVD-{camera}" for camera in CAMERAS) + ("EVD-NEW",))
            store = PersistentEvidenceStore(
                str(root), 1, id_factory=lambda: next(ids), review_target=dataset
            )
            cases = []
            paths = {}
            for camera in CAMERAS:
                record = store.persist_selected(
                    FRAME, camera_id=camera, timestamp="1", producer="fixture"
                )
                paths[camera] = store.resolve(record["relative_path"])
                if camera != "CAM-004":
                    cases.append(review_case(
                        suffix=camera, camera_id=camera,
                        static_ref=record["relative_path"], clip_ref="",
                    ))
            write_dataset(dataset, cases)
            replacement = store.persist_selected(
                FRAME, camera_id="CAM-004", timestamp="2", producer="fixture"
            )

            self.assertTrue(all(paths[camera].is_file() for camera in CAMERAS[:3]))
            self.assertFalse(paths["CAM-004"].exists())
            self.assertTrue(store.resolve(replacement["relative_path"]).is_file())

    def test_historical_missing_reference_does_not_break_retention(self):
        """T12: a previously evicted reference is tolerated without fabrication."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            dataset = Path(temporary) / "review" / "signal_review_records.jsonl"
            write_dataset(dataset, [review_case(
                suffix="MISSING", camera_id="CAM-001",
                static_ref="CAM-001/EVD-MISSING/frame.jpg",
                clip_ref="clips/CAM-001/CLP-MISSING.mp4",
                state="PENDING",
            )])
            store = PersistentEvidenceStore(str(root), 1, review_target=dataset)
            clips = EvidenceClipAdapter(root, max_clips_per_camera=1, review_target=dataset)

            self.assertEqual(store.enforce_retention("CAM-001"), "RETENTION_OK")
            self.assertEqual(clips.enforce_retention("CAM-001"), "RETENTION_OK")
            self.assertFalse(store.resolve("CAM-001/EVD-MISSING/frame.jpg").exists())


if __name__ == "__main__":
    unittest.main()
