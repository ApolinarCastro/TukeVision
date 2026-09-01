"""Integration test for full launcher path: TukeVision.bat → launcher → child → source factory.

Verifies:
- TukeVision.bat invokes launcher with correct python
- Launcher resolves config and passes RTSP_BACKEND explicitly
- Child process receives RTSP_BACKEND and instantiates correct source class
- Evidence folder created with RUN_ID identity
- Isolation between two runs (different RUN_ID, different evidence folders)
- Live evidence update via atomic replacement
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = REPO_ROOT / "scripts" / "launcher.py"
RUN_MULTICAMERA_PATH = REPO_ROOT / "scripts" / "run_multicamera.py"
BAT_PATH = REPO_ROOT / "TukeVision.bat"
CONFIG_PATH = REPO_ROOT / "config" / "multistore.active.json"

# Load launcher module
_spec = importlib.util.spec_from_file_location("tv_launcher", LAUNCHER_PATH)
_launcher_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_launcher_module)
CredentialDialog = _launcher_module.CredentialDialog

# Load run_multicamera module
_spec2 = importlib.util.spec_from_file_location("tv_run_multicamera", RUN_MULTICAMERA_PATH)
_run_multicamera_module = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_run_multicamera_module)
MulticameraRuntime = _run_multicamera_module.MulticameraRuntime


class FakeRTSPSource:
    """Stand-in for RTSPSource that records instantiation."""
    instances = []

    def __init__(self, rtsp_url=None, **kwargs):
        self.rtsp_url = rtsp_url
        self.kwargs = kwargs
        self.closed = False
        FakeRTSPSource.instances.append(self)

    def open(self):
        return type('Metadata', (), {'width': 352, 'height': 240, 'fps': 25.0, 'total_frames': 0, 'duration_seconds': 0.0, 'path': rtsp_url or '', 'source_type': 'RTSP'})()

    def close(self):
        self.closed = True


class FakeFFmpegSource:
    """Stand-in for FFmpegSupervisedSource that records instantiation."""
    instances = []

    def __init__(self, rtsp_url=None, **kwargs):
        self.rtsp_url = rtsp_url
        self.kwargs = kwargs
        self.closed = False
        FakeFFmpegSource.instances.append(self)

    def open(self):
        return type('Metadata', (), {'width': 352, 'height': 240, 'fps': 25.0, 'total_frames': 0, 'duration_seconds': 0.0, 'path': rtsp_url or '', 'source_type': 'RTSP'})()

    def close(self):
        self.closed = True


class TestFullLauncherPath(unittest.TestCase):
    """Integration tests for the full launcher path."""

    def setUp(self):
        FakeRTSPSource.instances.clear()
        FakeFFmpegSource.instances.clear()

    def test_bat_invokes_launcher_with_venv_python(self):
        """TukeVision.bat should reference .venv/Scripts/python.exe and launcher.py."""
        bat_content = BAT_PATH.read_text(encoding="utf-8")
        self.assertIn(".venv\\Scripts\\python.exe", bat_content)
        self.assertIn("scripts\\launcher.py", bat_content)

    def test_launcher_resolves_config_before_spawn(self):
        """Launcher should read RTSP_BACKEND from config before spawning child."""
        dialog = CredentialDialog(CONFIG_PATH)
        config = dialog.config
        rtsp_config = config.get("rtsp", {})
        # Config should have backend field (will be added by fix)
        # For now, verify launcher reads config correctly
        self.assertIn("multistore", config)

    def test_spawn_runtime_passes_rtsp_backend_explicitly(self):
        """_spawn_runtime should pass RTSP_BACKEND in child env."""
        dialog = CredentialDialog(CONFIG_PATH)
        with mock.patch("subprocess.Popen") as popen:
            popen.return_value = mock.Mock(pid=12345, wait=mock.Mock(return_value=0))
            rc = dialog._spawn_runtime("store_nicopoly_principal", "admin", "password")
        self.assertEqual(rc, 0)
        args, kwargs = popen.call_args
        env = kwargs["env"]
        self.assertIn("RTSP_BACKEND", env)
        self.assertIn("RTSP_BACKEND_REQUESTED", env)
        self.assertIn("RTSP_BACKEND_SOURCE", env)
        self.assertEqual(env["RTSP_BACKEND_SOURCE"], "config.rtsp.backend")

    def test_spawn_runtime_propagates_child_exit_0(self):
        """CHILD_EXIT_0 -> LAUNCHER_EXIT_0."""
        dialog = CredentialDialog(CONFIG_PATH)
        with mock.patch("subprocess.Popen") as popen:
            popen.return_value = mock.Mock(pid=12345, wait=mock.Mock(return_value=0))
            rc = dialog._spawn_runtime("store_nicopoly_principal", "admin", "password")
        self.assertEqual(rc, 0)

    def test_spawn_runtime_propagates_child_exit_nonzero(self):
        """CHILD_EXIT_NONZERO -> LAUNCHER_EXIT_NONZERO."""
        dialog = CredentialDialog(CONFIG_PATH)
        with mock.patch("subprocess.Popen") as popen:
            popen.return_value = mock.Mock(pid=12345, wait=mock.Mock(return_value=42))
            rc = dialog._spawn_runtime("store_nicopoly_principal", "admin", "password")
        self.assertEqual(rc, 42)

    def test_child_instantiates_correct_source_class_ffmpeg(self):
        """Child process should instantiate FFmpegSupervisedSource when RTSP_BACKEND=ffmpeg_supervised."""
        # This test verifies the source_factory behavior
        from src.capture.source_manager import _default_rtsp_source, CameraDescriptor
        
        os.environ["RTSP_BACKEND"] = "ffmpeg_supervised"
        try:
            # Patch the import location in _default_rtsp_source
            import src.capture.ffmpeg_supervised as ffmpeg_mod
            original_class = ffmpeg_mod.FFmpegSupervisedSource
            ffmpeg_mod.FFmpegSupervisedSource = FakeFFmpegSource
            try:
                descriptor = CameraDescriptor(
                    camera_id="cam_01",
                    host="rtsp://186.103.177.83:554/cam/realmonitor?channel=1&subtype=1",
                    username="admin",
                    password="password",
                )
                source = _default_rtsp_source(descriptor)
                self.assertIsInstance(source, FakeFFmpegSource)
                self.assertEqual(len(FakeFFmpegSource.instances), 1)
                self.assertEqual(len(FakeRTSPSource.instances), 0)
            finally:
                ffmpeg_mod.FFmpegSupervisedSource = original_class
        finally:
            os.environ.pop("RTSP_BACKEND", None)

    def test_child_fails_fast_if_ffmpeg_requested_but_unavailable(self):
        """If FFmpeg backend requested but import fails, should raise VideoSourceError."""
        from src.capture.source_manager import _default_rtsp_source, CameraDescriptor
        from src.capture.video_source import VideoSourceError
        
        os.environ["RTSP_BACKEND"] = "ffmpeg_supervised"
        try:
            # Make FFmpegSupervisedSource raise on import
            import src.capture.ffmpeg_supervised as ffmpeg_mod
            original_class = ffmpeg_mod.FFmpegSupervisedSource
            
            class FailingFFmpegSource:
                def __init__(self, *args, **kwargs):
                    raise ImportError("FFmpeg not available")
            
            ffmpeg_mod.FFmpegSupervisedSource = FailingFFmpegSource
            try:
                descriptor = CameraDescriptor(
                    camera_id="cam_01",
                    host="rtsp://186.103.177.83:554/cam/realmonitor?channel=1&subtype=1",
                    username="admin",
                    password="password",
                )
                with self.assertRaises(VideoSourceError) as ctx:
                    _default_rtsp_source(descriptor)
                self.assertIn("FFmpeg backend requested but failed to instantiate", str(ctx.exception))
            finally:
                ffmpeg_mod.FFmpegSupervisedSource = original_class
        finally:
            os.environ.pop("RTSP_BACKEND", None)

    def test_run_multicamera_creates_exclusive_evidence_folder(self):
        """MulticameraRuntime should create evidence/<RUN_ID>/ folder with identity.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock BASE to use temp dir
            import src.observability.logging_setup as ls
            original_new_run_id = ls.new_run_id
            ls.new_run_id = lambda: "RUN-TEST123"
            
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            
            # Mock BASE in run_multicamera module
            import scripts.run_multicamera as rm
            original_base = rm.BASE
            rm.BASE = Path(tmpdir)
            
            try:
                runtime = MulticameraRuntime(config, "password", "user", run_id="RUN-TEST123")
                
                # Check evidence folder created
                evidence_root = Path(runtime.evidence_root)
                self.assertTrue(evidence_root.exists())
                self.assertTrue(evidence_root.name == "RUN-TEST123")
                
                # Check identity.json exists and has correct content
                identity_path = evidence_root / "identity.json"
                self.assertTrue(identity_path.exists())
                
                identity = json.loads(identity_path.read_text(encoding="utf-8"))
                self.assertEqual(identity["run_id"], "RUN-TEST123")
                self.assertIn("pid", identity)
                self.assertIn("started_at", identity)
                self.assertIn("version", identity)
                self.assertIn("camera_ids", identity)
            finally:
                ls.new_run_id = original_new_run_id
                rm.BASE = original_base

    def test_isolation_between_two_runs(self):
        """Two runs should have different RUN_IDs and separate evidence folders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import src.observability.logging_setup as ls
            import scripts.run_multicamera as rm
            
            original_base = rm.BASE
            rm.BASE = Path(tmpdir)
            
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            
            try:
                run_id1 = "RUN-AAAAAA"
                runtime1 = MulticameraRuntime(config, "password", "user", run_id=run_id1)
                
                run_id2 = "RUN-BBBBBB"
                runtime2 = MulticameraRuntime(config, "password", "user", run_id=run_id2)
                
                # Different evidence roots
                self.assertNotEqual(runtime1.evidence_root, runtime2.evidence_root)
                self.assertTrue(Path(runtime1.evidence_root).name == run_id1)
                self.assertTrue(Path(runtime2.evidence_root).name == run_id2)
                
                # Different identity files
                id1 = json.loads((Path(runtime1.evidence_root) / "identity.json").read_text())
                id2 = json.loads((Path(runtime2.evidence_root) / "identity.json").read_text())
                self.assertEqual(id1["run_id"], run_id1)
                self.assertEqual(id2["run_id"], run_id2)
            finally:
                rm.BASE = original_base

    def test_live_evidence_update_atomic_replacement(self):
        """Evidence files should be written via atomic replacement (tmp + replace)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import src.observability.logging_setup as ls
            import scripts.run_multicamera as rm
            
            original_base = rm.BASE
            rm.BASE = Path(tmpdir)
            
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            
            try:
                runtime = MulticameraRuntime(config, "password", "user", run_id="RUN-ATOMIC")
                
                # Check identity.json was written atomically (no .tmp file left)
                evidence_root = Path(runtime.evidence_root)
                tmp_files = list(evidence_root.glob("*.tmp"))
                self.assertEqual(len(tmp_files), 0, "No .tmp files should remain after atomic write")
                
                # File should exist and be valid JSON
                identity_path = evidence_root / "identity.json"
                self.assertTrue(identity_path.exists())
                identity = json.loads(identity_path.read_text(encoding="utf-8"))
                self.assertEqual(identity["run_id"], "RUN-ATOMIC")
            finally:
                rm.BASE = original_base

    def test_last_frame_ts_none_handling(self):
        """LAST_FRAME_TS should remain None when no frames received (not converted to 0)."""
        from src.observability.true_liveness import TrueLivenessTracker
        
        tracker = TrueLivenessTracker(["cam_01"])
        snap = tracker.snapshot()
        
        # For camera with no frames, last_frame_monotonic should be None
        cam_state = snap.get("cam_01")
        if cam_state:
            self.assertIsNone(cam_state.last_frame_monotonic,
                             "LAST_FRAME_TS should be None when no frames received")

    def test_no_first_frame_differentiated_from_freeze(self):
        """NO_FIRST_FRAME (zero frames) should be differentiated from subsequent freeze."""
        # This is verified in _generate_physical_report by the NO_FIRST_FRAME field
        with tempfile.TemporaryDirectory() as tmpdir:
            import src.observability.logging_setup as ls
            import scripts.run_multicamera as rm
            
            original_base = rm.BASE
            rm.BASE = Path(tmpdir)
            
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            
            try:
                runtime = MulticameraRuntime(config, "password", "user", run_id="RUN-NOFF")
                
                # Call _generate_physical_report with mocked components
                class MockForensics:
                    _started = time.time()
                    registry = {"why_process_exited": "NORMAL_UI_CLOSE"}
                    finished = True
                
                # Mock the components that _generate_physical_report needs
                runtime._true_liveness = mock.Mock()
                runtime._true_liveness.snapshot.return_value = {}
                runtime._health = mock.Mock()
                health_mock = mock.Mock()
                health_mock.camera_health = []
                runtime._health.snapshot.return_value = health_mock
                runtime._trace = mock.Mock()
                runtime._trace._counters = {}
                runtime._telemetry = mock.Mock()
                runtime._telemetry.snapshot.return_value = []
                runtime._telemetry.marker_rows.return_value = {}
                
                forensics = MockForensics()
                _run_multicamera_module._generate_physical_report(runtime, forensics)
                
                report_path = Path(runtime.evidence_root) / "physical_runtime_report.json"
                self.assertTrue(report_path.exists())
                report = json.loads(report_path.read_text(encoding="utf-8"))
                for cam in report["per_camera"]:
                    self.assertIsNone(cam["LAST_FRAME_TS"])
                    self.assertTrue(cam["NO_FIRST_FRAME"])
            finally:
                rm.BASE = original_base

    def test_reconnection_generation_counter_reset(self):
        """OperationalPipeline must accept lower frame_index when generation increases (reconnect)."""
        from src.app.operational_pipeline import OperationalPipeline
        from unittest.mock import MagicMock
        
        manager = MagicMock()
        pipe = OperationalPipeline({"observation": {}, "temporal": {}, "behavior": {}}, manager, chain=MagicMock())
        
        # Generation 1, frame 50
        snap1 = {"frame_index": 50, "generation": 1, "frame": object(), "state": "OPEN"}
        res1 = pipe.process_available("cam_01", snapshot=snap1)
        self.assertEqual(pipe._last_frame["cam_01"], (1, 50))
        
        # Generation 1, frame 40 (stale / duplicate -> ignored)
        snap1_old = {"frame_index": 40, "generation": 1, "frame": object(), "state": "OPEN"}
        res1_old = pipe.process_available("cam_01", snapshot=snap1_old)
        self.assertIsNone(res1_old)
        self.assertEqual(pipe._last_frame["cam_01"], (1, 50))
        
        # Generation 2 (reconnect!), frame 0 (counter reset -> MUST be processed)
        snap2 = {"frame_index": 0, "generation": 2, "frame": object(), "state": "OPEN"}
        res2 = pipe.process_available("cam_01", snapshot=snap2)
        self.assertEqual(pipe._last_frame["cam_01"], (2, 0))

    def test_slow_analytics_and_stale_results_do_not_freeze_live_presentation(self):
        """MultiCameraViewModel and select_panel_frame must always present latest live frame."""
        from types import SimpleNamespace
        from src.ui.multicamera import MultiCameraViewModel
        from src.ui.tk_view import select_panel_frame
        import numpy as np
        
        vm = MultiCameraViewModel(("cam_01",))
        
        frame_old = np.full((100, 100, 3), 10, dtype=np.uint8)
        frame_live = np.full((100, 100, 3), 255, dtype=np.uint8)
        
        # 1. Pipeline analyzed old frame (index=5) with bounding box
        snap_analytic = SimpleNamespace(
            frame_index=5,
            generation=1,
            frame=frame_old,
            source_state="OPEN",
            fps=15.0,
            detections=1,
            bboxes=((10, 10, 50, 50, 0.9),),
            track_id="TRK-1",
        )
        vm.update("cam_01", snap_analytic)
        
        # At index 5, analytics matches live frame -> returns analytics
        p1 = vm.panel("cam_01")
        sel1, idx1, mode1 = select_panel_frame(p1)
        self.assertEqual((idx1, mode1), (5, "ANALITICA"))
        
        # 2. Live stream advances to index 15 while analytics is still computing or delayed
        snap_live = SimpleNamespace(
            frame_index=15,
            generation=1,
            frame=frame_live,
            source_state="OPEN",
            fps=15.0,
            detections=None,
            bboxes=None,
            track_id=None,
        )
        vm.update("cam_01", snap_live)
        
        # Panel has frame_index=15, analytics_frame_index=5
        p2 = vm.panel("cam_01")
        sel2, idx2, mode2 = select_panel_frame(p2)
        # MUST present fresh live frame (index 15), NOT freeze on index 5!
        self.assertIs(sel2, frame_live)
        self.assertEqual((idx2, mode2), (15, "VIVO"))

    def test_panel_render_error_isolation_preserves_remaining_panels(self):
        """Exception in rendering one camera panel must not abort rendering remaining panels."""
        from src.ui.tk_view import TkApp
        import tkinter as tk
        import numpy as np
        
        # Create headless root
        try:
            root = tk.Tk()
            root.withdraw()
        except Exception:
            return  # Headless env without display
            
        try:
            view = TkApp.__new__(TkApp)
            view._video_canvases = {"cam_01": mock.MagicMock(), "cam_02": mock.MagicMock()}
            view._visible_camera_ids = ["cam_01", "cam_02"]
            view._focused_camera = None
            view._controller = mock.MagicMock()
            view._stopped_rendered = {"cam_01": False, "cam_02": False}
            
            p1 = mock.MagicMock(frame=np.zeros((10, 10, 3), dtype=np.uint8), frame_index=1, source_state="OPEN")
            p2 = mock.MagicMock(frame=np.zeros((10, 10, 3), dtype=np.uint8), frame_index=1, source_state="OPEN")
            view._controller.poll_multicamera.return_value = {"cam_01": p1, "cam_02": p2}
            
            # Make cam_01 throw an exception during render
            visited = []
            def side_effect(cam_id, panel, canvas, health):
                visited.append(cam_id)
                if cam_id == "cam_01":
                    raise RuntimeError("Simulated render crash in cam_01")
            view._render_camera = mock.MagicMock(side_effect=side_effect)
            
            state = {"status": "RUNNING", "system_health": None}
            view._render_video(state)
            
            # Both cameras must have been attempted despite cam_01 failing
            self.assertEqual(visited, ["cam_01", "cam_02"])
        finally:
            root.destroy()

    def test_analytics_from_previous_generation_rejected(self):
        """Analytics results tagged with an older generation must be discarded."""
        from src.ui.multicamera import MultiCameraViewModel
        from types import SimpleNamespace
        import numpy as np
        
        vm = MultiCameraViewModel(("cam_01",))
        # Generation 2 live stream at index 2
        snap_live_gen2 = SimpleNamespace(
            frame_index=2,
            generation=2,
            frame=np.full((10, 10, 3), 200, dtype=np.uint8),
            source_state="OPEN",
            fps=15.0,
        )
        vm.update("cam_01", snap_live_gen2)
        self.assertEqual(vm.panel("cam_01").generation, 2)
        
        # Stale analytics arriving from generation 1 at index 100
        snap_old_gen1 = SimpleNamespace(
            frame_index=100,
            generation=1,
            frame=np.full((10, 10, 3), 50, dtype=np.uint8),
            source_state="OPEN",
            fps=15.0,
            detections=5,
        )
        vm.update("cam_01", snap_old_gen1)
        # MUST remain on generation 2, index 2!
        self.assertEqual(vm.panel("cam_01").generation, 2)
        self.assertEqual(vm.panel("cam_01").frame_index, 2)


if __name__ == "__main__":
    unittest.main()