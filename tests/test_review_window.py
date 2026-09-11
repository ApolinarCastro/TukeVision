"""DEF-UI-REVIEW-01: human review is product UI inside TukeVision.

The review window adapts over the existing QW-00 JSONL dataset and the same
human_review_matrix.csv persistence (no second datastore, no CMD console).
"""

import csv
import json
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

from tests.conftest import shared_root

from src.ui.review_view import EMPTY_STATE_TEXT, TukeVisionReviewWindow
from src.ui.tk_view import TkApp

CAMERA_IDS = tuple(f"cam_{i:02d}" for i in range(1, 16))


def record(review_id, camera_id, classification="NOT_REVIEWED",
           clip_available=False, clip_ref="", evidence_ref=""):
    return {
        "review_id": review_id,
        "signal_id": f"SIG-{review_id}",
        "signal_type": "PERSON_RECOGNIZED",
        "camera_id": camera_id,
        "track_id": "TRK-7",
        "trajectory_id": "",
        "rule_id": "RULE_HIGH_VALUE",
        "timestamp_start": "2026-08-20T09:30:00+00:00",
        "timestamp_end": "2026-08-20T09:30:05+00:00",
        "rule_score": 0.94,
        "evidence_refs": [evidence_ref] if evidence_ref else [],
        "evidence_available": bool(evidence_ref),
        "clip_evidence_ref": clip_ref,
        "clip_available": clip_available,
        "clip_sha256": "",
        "human_classification": classification,
        "structured_explanation": {"rule_id": "RULE_HIGH_VALUE"},
    }


def write_matrix(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        "review_id", "signal_id", "camera_id", "track_id", "classification",
        "review_timestamp", "evidence_ref", "clip_evidence_ref", "clip_sha256",
        "static_evidence_sufficient", "temporal_evidence_sufficient",
        "comparison_notes",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


class ReviewWindowBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.dataset = self.base / "signal_review_records.jsonl"
        self.matrix = self.base / "human_review_matrix.csv"
        self.evidence = self.base / "evidence"
        self.evidence.mkdir(exist_ok=True)

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except Exception:
            pass
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass

    def _write_dataset(self, records):
        with self.dataset.open("w", encoding="utf-8") as stream:
            for record_ in records:
                stream.write(json.dumps(record_) + "\n")

    def _open(self, records, matrix_rows=None, **kwargs):
        if matrix_rows is not None:
            write_matrix(self.matrix, matrix_rows)
        return TukeVisionReviewWindow(
            self.root,
            records=records,
            matrix_path=self.matrix,
            evidence_root=self.evidence,
            opener=lambda path: True,
            **kwargs,
        )

    def _labels(self, window):
        out = []
        for widget in window.winfo_children():
            try:
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        out.append(child.cget("text"))
            except tk.TclError:
                pass
        return out


class TestReviewWindow(ReviewWindowBase):
    def test_window_opens_with_records(self):
        self._write_dataset([record("SRR-1", "cam_01")])
        window = self._open([record("SRR-1", "cam_01")])
        self.assertTrue(isinstance(window, tk.Toplevel))
        self.assertEqual(window.title(), "Revisión humana · QW-00")
        self.assertEqual(window._counter_var.get(), "Registro 1 / 1 · Pendientes: 1")
        self.assertEqual(window._info_vars["camera"].get(), "cam_01")

    def test_existing_review_record_loads(self):
        records = [
            record("SRR-1", "cam_01"),
            record("SRR-2", "cam_02"),
        ]
        reviewed = [{
            "review_id": "SRR-1", "signal_id": "SIG-SRR-1",
            "camera_id": "cam_01", "track_id": "TRK-7",
            "classification": "AMBIGUOUS", "review_timestamp": "2026-08-20T10:00:00",
            "evidence_ref": "", "clip_evidence_ref": "",
            "clip_sha256": "", "static_evidence_sufficient": "YES",
            "temporal_evidence_sufficient": "NOT_AVAILABLE", "comparison_notes": "",
        }]
        self._write_dataset(records)
        window = self._open(records, matrix_rows=reviewed)
        # Starts at the first PENDING record (SRR-2), then PREV loads SRR-1.
        self.assertEqual(window._info_vars["camera"].get(), "cam_02")
        window._on_prev()
        self.assertEqual(window._info_vars["camera"].get(), "cam_01")
        self.assertEqual(window._info_vars["classification"].get(), "AMBIGUOUS")
        self.assertEqual(window._info_vars["review_state"].get(), "REVIEWED")

    def test_next_and_previous_navigation(self):
        records = [record("SRR-1", "cam_01"), record("SRR-2", "cam_02")]
        window = self._open(records)
        self.assertEqual(window._index, 0)
        window._on_next()
        self.assertEqual(window._index, 1)
        self.assertEqual(window._info_vars["camera"].get(), "cam_02")
        window._on_prev()
        self.assertEqual(window._index, 0)
        self.assertEqual(window._info_vars["camera"].get(), "cam_01")

    def test_classification_persists_to_existing_matrix(self):
        records = [record("SRR-1", "cam_01"), record("SRR-2", "cam_02")]
        window = self._open(records)
        window._go_to(1)
        window._classify("USEFUL_SIGNAL")
        window._save()
        rows = []
        with self.matrix.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append(row)
        saved = {row["review_id"]: row for row in rows}
        self.assertEqual(saved["SRR-2"]["classification"], "USEFUL_SIGNAL")
        self.assertEqual(saved["SRR-2"]["camera_id"], "cam_02")
        self.assertTrue((self.matrix.parent / "operator_review_metrics.json").is_file())

    def test_classification_shows_after_classify(self):
        records = [record("SRR-1", "cam_01")]
        window = self._open(records)
        window._classify("SYSTEM_ERROR")
        self.assertEqual(window._info_vars["classification"].get(), "SYSTEM_ERROR")
        self.assertEqual(window._info_vars["review_state"].get(), "REVIEWED")

    def test_empty_review_shows_message_not_console(self):
        window = self._open([])
        self.assertEqual(window.title(), "Revisión humana · QW-00")
        texts = self._labels(window)
        self.assertTrue(
            any(EMPTY_STATE_TEXT in text for text in texts),
            f"expected '{EMPTY_STATE_TEXT}' in {texts}",
        )
        self.assertFalse(hasattr(window, "_save_btn"))

    def test_no_pending_records_shows_empty_message(self):
        records = [record("SRR-1", "cam_01")]
        reviewed = [{
            "review_id": "SRR-1", "signal_id": "SIG-SRR-1",
            "camera_id": "cam_01", "track_id": "",
            "classification": "BENIGN_ACTIVITY", "review_timestamp": "2026-08-20T10:00:00",
            "evidence_ref": "", "clip_evidence_ref": "",
            "clip_sha256": "", "static_evidence_sufficient": "YES",
            "temporal_evidence_sufficient": "NOT_AVAILABLE", "comparison_notes": "",
        }]
        self._write_dataset(records)
        window = self._open(records, matrix_rows=reviewed)
        texts = self._labels(window)
        self.assertTrue(any(EMPTY_STATE_TEXT in text for text in texts))

    def test_clip_status_shows_unavailable_without_technical_error(self):
        records = [record("SRR-1", "cam_01", clip_available=True,
                          clip_ref="clips/cam_01/missing.mp4")]
        window = self._open(records)
        self.assertEqual(window._info_vars["clip_status"].get(), "No disponible")
        window._on_open_clip()
        self.assertEqual(window._status_var.get(), "Clip no disponible")

    def test_jpeg_thumbnail_rendered_when_present(self):
        import numpy as np

        import cv2

        jpeg = self.evidence / "cam_01" / "frame_0001.jpg"
        jpeg.parent.mkdir(parents=True, exist_ok=True)
        frame = np.full((120, 160, 3), 90, dtype=np.uint8)
        ok, encoded = cv2.imencode(".jpg", frame)
        self.assertTrue(ok)
        jpeg.write_bytes(encoded.tobytes())
        records = [record("SRR-1", "cam_01", evidence_ref="cam_01/frame_0001.jpg")]
        window = self._open(records)
        self.assertIsNotNone(window._photo, "JPEG thumbnail should be rendered")

    def test_no_cmd_required_from_app(self):
        calls = []

        class ReviewController:
            is_multicamera = True
            store_id = "store_nicopoly_principal"

            @property
            def camera_ids(self):
                return CAMERA_IDS

            def stores(self):
                return ["store_nicopoly_principal"]

            def store_zones(self, store_id):
                return []

            def select_store(self, store_id, zone=""):
                pass

            def poll_state(self):
                return {
                    "status": "RUNNING", "store_id": self.store_id,
                    "system_health": None, "alert_log": [],
                    "evidence_paths": [], "clips_available": None, "fps": 0.0,
                }

            def poll_multicamera(self):
                return {}

            def ptz_status(self, camera_id):
                return {"supported": False, "certified": False}

            def ptz_command(self, camera_id, action):
                return False

            def mark_ui_rendered(self, camera_id, frame_index):
                pass

            def latest_evidence(self):
                return None

            def clip_target(self):
                return None

            def review_available(self):
                return True

            def review_records(self):
                return []

            def startfile_guard(self):
                calls.append("startfile")

        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except tk.TclError:
                pass
        app = TkApp(self.root, ReviewController())
        app._poll_once()
        app._on_open_clips()
        self.root.update_idletasks()
        self.root.update()
        windows = [
            w for w in self.root.winfo_children()
            if isinstance(w, TukeVisionReviewWindow)
        ]
        self.assertTrue(windows, "review GUI must open instead of a CMD console")
        self.assertEqual(calls, [], "os.startfile must not launch a console")


if __name__ == "__main__":
    unittest.main()