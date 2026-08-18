"""LOOP-0019B-R1: evidencia/clip exactos y estado UI coherente tras STOP.

Cubre los fallos V8 (evidencia/clip), V9 (coherencia post-STOP) y V10
(estado UI de STOP) sin abrir ventanas Tk: verifica funciones puras de la
vista y los ayudantes de resolución del runtime multicámara.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.run_multicamera import MulticameraRuntime
from src.ui.tk_view import (
    action_button_states,
    frozen_overlay_text,
    online_camera_count,
    resolve_evidence_path,
    stopped_camera_line,
)


def _panel(evidence="", frame_index=-1, source_state="OFFLINE"):
    return SimpleNamespace(
        evidence=evidence, frame_index=frame_index, source_state=source_state
    )


class TestEvidenceExactTarget(unittest.TestCase):
    def test_evidence_target_resolves_exact_jpeg_not_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "CAM-001" / "EVD-1" / "frame.jpg"
            evidence.parent.mkdir(parents=True)
            evidence.write_bytes(b"jpeg")
            self.assertEqual(
                Path(resolve_evidence_path("CAM-001/EVD-1/frame.jpg", root)).resolve(),
                evidence.resolve(),
            )

    def test_evidence_target_none_when_file_missing_or_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertIsNone(resolve_evidence_path("CAM-001/EVD-1/frame.jpg", root))
            self.assertIsNone(resolve_evidence_path("", root))
            self.assertIsNone(resolve_evidence_path("..\\..\\secret", root))


class TestLatestEvidence(unittest.TestCase):
    def test_latest_evidence_returns_exact_recent_jpeg(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "CAM-001" / "EVD-1" / "frame.jpg"
            second = root / "CAM-001" / "EVD-2" / "frame.jpg"
            first.parent.mkdir(parents=True)
            first.write_bytes(b"a")
            second.parent.mkdir(parents=True)
            second.write_bytes(b"b")
            runtime = MulticameraRuntime.__new__(MulticameraRuntime)
            runtime.evidence_root = str(root)
            runtime._controller = SimpleNamespace(poll_multicamera=lambda: {
                "CAM-001": _panel("CAM-001/EVD-1/frame.jpg", 5),
                "CAM-002": _panel("CAM-001/EVD-2/frame.jpg", 9),
                "CAM-003": _panel("", -1),
            })
            self.assertEqual(
                Path(runtime.latest_evidence()).resolve(), second.resolve()
            )

    def test_latest_evidence_none_when_only_missing_refs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = MulticameraRuntime.__new__(MulticameraRuntime)
            runtime.evidence_root = str(root)
            runtime._controller = SimpleNamespace(poll_multicamera=lambda: {
                "CAM-001": _panel("CAM-001/EVD-1/frame.jpg", 5),
            })
            self.assertIsNone(runtime.latest_evidence())


class TestClipExactTarget(unittest.TestCase):
    def _runtime(self, root, records):
        runtime = MulticameraRuntime.__new__(MulticameraRuntime)
        runtime.evidence_root = str(root)
        runtime.review_target = str(root / "records.jsonl")
        if records:
            (root / "records.jsonl").write_text(
                "\n".join(json.dumps(record) for record in records) + "\n",
                encoding="utf-8",
            )
        runtime._controller = SimpleNamespace(poll_multicamera=lambda: {})
        return runtime

    def test_clip_target_resolves_exact_mp4_from_latest_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clip = root / "clips" / "CAM-001" / "CLP-1.mp4"
            clip.parent.mkdir(parents=True)
            clip.write_bytes(b"mp4")
            runtime = self._runtime(root, [
                {"clip_available": False, "clip_evidence_ref": None},
                {"clip_available": True, "clip_evidence_ref": "clips/CAM-001/CLP-1.mp4"},
            ])
            self.assertEqual(
                Path(runtime.clip_target()).resolve(), clip.resolve()
            )
            self.assertTrue(runtime.review_available())

    def test_no_clip_but_review_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = self._runtime(
                root, [{"clip_available": False, "clip_evidence_ref": None}]
            )
            self.assertIsNone(runtime.clip_target())
            self.assertTrue(runtime.review_available())

    def test_no_review_means_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = self._runtime(root, [])
            self.assertIsNone(runtime.clip_target())
            self.assertFalse(runtime.review_available())


class TestStopUiState(unittest.TestCase):
    def test_stopped_header_reports_zero_online(self):
        panels = {
            camera_id: _panel("", 1, "OPEN")
            for camera_id in ("CAM-001", "CAM-002", "CAM-003", "CAM-004")
        }
        self.assertEqual(online_camera_count(panels, running=False), 0)
        self.assertEqual(online_camera_count(panels, running=True), 4)

    def test_stopped_side_panel_shows_closed_system_idle(self):
        line = stopped_camera_line("CAM-001")
        self.assertIn("CAM-001", line)
        self.assertIn("CLOSED", line)
        self.assertIn("SYSTEM IDLE", line)

    def test_frozen_frame_marked_offline(self):
        text = frozen_overlay_text()
        self.assertIn("CLOSED", text)
        self.assertIn("LAST FRAME", text)
        self.assertIn("OFFLINE", text)


class TestActionButtons(unittest.TestCase):
    def test_evidence_button_enabled_only_with_valid_target(self):
        self.assertFalse(action_button_states(None, None, False)["evidence_enabled"])
        self.assertTrue(action_button_states("/tmp/x.jpg", None, False)["evidence_enabled"])

    def test_clip_button_enabled_with_clip_or_review(self):
        self.assertTrue(action_button_states(None, "/tmp/x.mp4", False)["clip_enabled"])
        self.assertTrue(action_button_states(None, None, True)["clip_enabled"])
        self.assertFalse(action_button_states(None, None, False)["clip_enabled"])


class TestGenericFolderOpeningRemoved(unittest.TestCase):
    def test_evidence_clip_actions_open_exact_files_never_folders(self):
        source = Path("src/ui/tk_view.py").read_text(encoding="utf-8")
        self.assertIn("EVIDENCE_UNAVAILABLE", source)
        self.assertIn("CLIP_REVIEW_UNAVAILABLE", source)
        self.assertIn("os.path.isfile(target)", source)
        self.assertIn("LAST FRAME / OFFLINE", source)
        self.assertIn("SYSTEM IDLE", source)
        self.assertNotIn("startfile(base)", source)

    def test_review_tool_finds_runtime_qw04_dataset(self):
        source = Path("scripts/review_behavior_signals.py").read_text(encoding="utf-8")
        self.assertIn("loop_0019a_qw04_r2", source)


if __name__ == "__main__":
    unittest.main()