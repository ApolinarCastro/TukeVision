import json
import tempfile
import unittest
from pathlib import Path

from src.behavior.contracts import BehaviorFeature, BehaviorSignal
from src.review import (ALLOWED_CLASSIFICATIONS, BoundedReviewExporter,
                        SignalReviewRecord, record_from_signal)


def signal(n=1, camera="CAM-001", kind="REPEATED_ACTIVITY", rule="repeated_activity"):
    feature = BehaviorFeature(f"BF-{n}", "event_count", n + 2, f"T-{n}",
                              (camera,), "2026-08-17T10:00:00Z", "2026-08-17T10:00:10Z",
                              (f"EVT-{n}", f"T-{n}"), (f"{camera}/E-{n}/frame.jpg",))
    sig = BehaviorSignal(f"BS-{n}", kind, rule, 20.0, f"T-{n}", (feature.feature_id,),
                         (camera,), feature.window_start, feature.window_end,
                         feature.evidence_refs)
    return sig, (feature,)


class TestSignalReviewRecord(unittest.TestCase):
    def test_serializes_complete_non_accusatory_record(self):
        sig, features = signal()
        record = record_from_signal(sig, features, created_at="2026-08-17T12:00:00Z")
        data = record.to_dict()
        self.assertEqual(data["signal_id"], "BS-1")
        self.assertEqual(data["human_classification"], "NOT_REVIEWED")
        self.assertTrue(data["evidence_available"])
        self.assertEqual(data["source_refs"], ["EVT-1", "T-1"])
        self.assertIn("threshold", data["structured_explanation"])
        self.assertNotIn("suspicious", json.dumps(data).lower())

    def test_only_controlled_classifications_are_allowed(self):
        sig, features = signal()
        record = record_from_signal(sig, features, created_at="x")
        for value in ALLOWED_CLASSIFICATIONS:
            self.assertEqual(record.with_review(value, "note").human_classification, value)
        with self.assertRaises(ValueError):
            record.with_review("GUILTY", "")

    def test_missing_evidence_is_not_fabricated(self):
        sig, features = signal()
        sig = BehaviorSignal(sig.signal_id, sig.signal_type, sig.rule_id, sig.rule_score,
                             sig.subject_ref, sig.feature_refs, sig.camera_ids,
                             sig.window_start, sig.window_end, ())
        record = record_from_signal(sig, features, created_at="x")
        self.assertEqual(record.evidence_refs, ())

    def test_evidence_refs_are_preserved_and_secrets_redacted(self):
        sig, features = signal()
        sig = BehaviorSignal(sig.signal_id, sig.signal_type, sig.rule_id, sig.rule_score,
                             sig.subject_ref, sig.feature_refs, sig.camera_ids,
                             sig.window_start, sig.window_end,
                             ("rtsp://admin:secret@camera.local/live", "frame.jpg"))
        record = record_from_signal(sig, features, created_at="x")
        self.assertEqual(record.evidence_refs, sig.evidence_refs)
        serialized = json.dumps(record.to_dict())
        self.assertNotIn("secret", serialized)
        self.assertIn("frame.jpg", serialized)


class TestBoundedReviewExporter(unittest.TestCase):
    def test_deduplicates_and_enforces_all_bounds(self):
        exporter = BoundedReviewExporter(max_records_total=4, max_records_per_camera=2,
                                         max_records_per_signal_type=3,
                                         max_records_per_rule=3, max_candidates=12)
        for i in range(10):
            sig, features = signal(i, f"CAM-00{i % 3 + 1}",
                                   "REPEATED_ACTIVITY" if i % 2 else "MULTI_CAMERA_SEQUENCE",
                                   "repeat" if i % 2 else "multi")
            exporter.offer(record_from_signal(sig, features, created_at="x"))
            exporter.offer(record_from_signal(sig, features, created_at="x"))
        selected = exporter.select()
        self.assertLessEqual(len(selected), 4)
        self.assertEqual(len({r.review_id for r in selected}), len(selected))
        for camera in {r.camera_id for r in selected}:
            self.assertLessEqual(sum(r.camera_id == camera for r in selected), 2)

    def test_sampling_is_deterministic_and_balanced(self):
        records = []
        for i in range(12):
            sig, features = signal(i, f"CAM-00{i % 3 + 1}",
                                   "TYPE-A" if i < 9 else "TYPE-B",
                                   "rule-a" if i < 9 else "rule-b")
            records.append(record_from_signal(sig, features, created_at="x"))
        a = BoundedReviewExporter(max_records_total=6, max_records_per_camera=3,
                                  max_records_per_signal_type=4, max_records_per_rule=4)
        b = BoundedReviewExporter(max_records_total=6, max_records_per_camera=3,
                                  max_records_per_signal_type=4, max_records_per_rule=4)
        for record in records:
            a.offer(record)
        for record in reversed(records):
            b.offer(record)
        self.assertEqual([r.review_id for r in a.select()], [r.review_id for r in b.select()])
        self.assertEqual({r.signal_type for r in a.select()}, {"TYPE-A", "TYPE-B"})
        self.assertEqual({r.camera_id for r in a.select()}, {"CAM-001", "CAM-002", "CAM-003"})

    def test_atomic_jsonl_export_and_stats(self):
        exporter = BoundedReviewExporter(max_records_total=2)
        for i in range(3):
            sig, features = signal(i)
            exporter.offer(record_from_signal(sig, features, created_at="x"))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "review.jsonl"
            stats = exporter.export_jsonl(target)
            rows = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(stats["selected"], 2)
        self.assertEqual(stats["duplicates"], 0)

    def test_candidate_memory_is_bounded_and_camera_state_isolated(self):
        exporter = BoundedReviewExporter(max_records_total=3, max_candidates=5)
        for i in range(30):
            sig, features = signal(i, f"CAM-00{i % 4 + 1}")
            exporter.offer(record_from_signal(sig, features, created_at="x"))
        self.assertLessEqual(exporter.stats()["retained_candidates"], 5)
        self.assertGreaterEqual(len({r.camera_id for r in exporter.select()}), 2)


if __name__ == "__main__":
    unittest.main()
