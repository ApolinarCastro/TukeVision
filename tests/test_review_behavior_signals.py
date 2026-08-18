import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.review_behavior_signals import (
    FIELDS,
    dataset_path,
    load_existing,
    open_evidence,
    resolve_evidence,
    save,
    write_metrics,
)


class TestReviewBehaviorSignals(unittest.TestCase):
    def test_dataset_prefers_first_ready_qw00_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            (second / "signal_review_records.jsonl").write_text("{}\n", encoding="utf-8")
            self.assertEqual(dataset_path((first, second)), second / "signal_review_records.jsonl")

    def test_open_evidence_is_explicit_and_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            root.mkdir()
            clip = root / "clips" / "CAM-001" / "clip.mp4"
            clip.parent.mkdir(parents=True)
            clip.write_bytes(b"clip")
            opened = []
            self.assertTrue(open_evidence(
                "clips/CAM-001/clip.mp4", root=root, opener=opened.append
            ))
            self.assertEqual(opened, [str(clip.resolve())])
            self.assertIsNone(resolve_evidence("../outside.mp4", root))
            self.assertFalse(open_evidence("../outside.mp4", root=root, opener=opened.append))

    def test_legacy_review_csv_loads_with_new_fields_empty(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "human_review_matrix.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=("review_id", "classification"))
                writer.writeheader()
                writer.writerow({"review_id": "SRR-1", "classification": "AMBIGUOUS"})
            loaded = load_existing(path)["SRR-1"]
            self.assertEqual(loaded["classification"], "AMBIGUOUS")
            self.assertEqual(loaded["clip_evidence_ref"], "")
            self.assertEqual(set(loaded), set(FIELDS))

    def test_atomic_save_and_evidence_sufficiency_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "human_review_matrix.csv"
            rows = [{
                "review_id": "SRR-1",
                "classification": "INSUFFICIENT_EVIDENCE",
                "static_evidence_sufficient": "NO",
                "temporal_evidence_sufficient": "YES",
            }]
            save(path, rows)
            metrics = write_metrics(path, rows)
            self.assertEqual(load_existing(path)["SRR-1"]["temporal_evidence_sufficient"], "YES")
            self.assertEqual(metrics["static_evidence_sufficiency"]["NO"], 1)
            self.assertEqual(metrics["temporal_evidence_sufficiency"]["YES"], 1)
            persisted = json.loads(
                (path.parent / "operator_review_metrics.json").read_text(encoding="utf-8")
            )
            self.assertTrue(persisted["human_review_evidence_sufficiency_measured"])


if __name__ == "__main__":
    unittest.main()
