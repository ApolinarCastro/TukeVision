"""Shutdown resilience tests (BLOCK B: review file PermissionError must not kill app)."""

import tempfile
import shutil
import json
import unittest
from pathlib import Path
import tkinter as tk
from unittest import mock

from tests.conftest import shared_root
from scripts.run_multicamera import MulticameraRuntime

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CONFIG = REPO_ROOT / "config" / "multistore.active.json"


class TestReviewRecordsResilience(unittest.TestCase):
    def test_review_records_returns_empty_on_permission_error(self):
        config = json.loads(ACTIVE_CONFIG.read_text(encoding="utf-8"))
        # Use a real runtime but patch Path.read_text to raise PermissionError
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime.review_target = Path("/fake/signal_review_records.jsonl")
        # Patch is_file to True, read_text to raise
        with mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(Path, "read_text", side_effect=PermissionError("locked")):
            result = runtime._review_records()
            self.assertEqual(result, ())

    def test_review_available_false_on_io_error(self):
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime.review_target = Path("/fake/signal_review_records.jsonl")
        with mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(Path, "read_text", side_effect=OSError("busy")):
            self.assertFalse(runtime.review_available())

    def test_clip_target_returns_none_on_io_error(self):
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime.review_target = Path("/fake/signal_review_records.jsonl")
        with mock.patch.object(Path, "is_file", return_value=True), \
             mock.patch.object(Path, "read_text", side_effect=PermissionError("locked")):
            self.assertIsNone(runtime.clip_target())


class TestTkPollResilience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = shared_root()

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="tuke_shutdown_"))
        self.config_path = self.tmp_dir / "multistore.active.json"
        shutil.copyfile(ACTIVE_CONFIG, self.config_path)
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        from src.ui.controller import UiController
        from src.ui.tk_view import TkApp
        from src.domain.catalog import StoreCatalog
        catalog = StoreCatalog.from_dict(config)
        entries = catalog.camera_descriptors(max_width=320, process_every_n_frames=1, credential_resolver=lambda ref: ("u", "p"))
        camera_ids = tuple(e.camera_id for e in entries)
        self.controller = UiController(config=config, camera_ids=camera_ids[:1])
        # Make review_available raise
        self.controller.review_available = mock.MagicMock(side_effect=PermissionError("locked"))
        self.controller.latest_evidence = mock.MagicMock(side_effect=OSError("e"))
        self.controller.clip_target = mock.MagicMock(side_effect=OSError("e"))
        self.app = TkApp(self.root, self.controller)

    def tearDown(self):
        try:
            self.app._root.after_cancel(self.app._poll_after_id)
        except Exception:
            pass
        for w in self.root.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_update_action_targets_survives_review_error(self):
        # Should not raise
        try:
            self.app._update_action_targets({"status": "RUNNING", "evidence_paths": []})
        except Exception as exc:
            self.fail(f"_update_action_targets raised {exc}")
        self.assertFalse(self.app._review_available)
        self.assertIsNone(self.app._clip_target)

    def test_poll_once_survives_review_error(self):
        # poll_once calls _update_action_targets which now swallows errors
        try:
            self.app._poll_once()
        except PermissionError:
            self.fail("poll_once propagated PermissionError")
        except OSError:
            self.fail("poll_once propagated OSError")

    def test_poll_schedules_next_even_after_error(self):
        # _poll should swallow exception and still schedule next after
        # Make poll_once raise something unexpected
        orig = self.app._poll_once
        self.app._poll_once = mock.MagicMock(side_effect=RuntimeError("boom"))
        self.app._poll_after_id = None
        try:
            self.app._poll()
        except RuntimeError:
            self.fail("_poll propagated error")
        # Should have scheduled next poll
        self.assertIsNotNone(self.app._poll_after_id)
        self.app._poll_once = orig
        try:
            self.root.after_cancel(self.app._poll_after_id)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
