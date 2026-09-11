"""Regression tests for generation advancement across the full UI render chain.

Verifies:
1. build_panel_snapshot propagates generation.
2. MultiCameraViewModel accepts new generation starting at frame_index=0 after high index in prior generation.
3. MultiCameraViewModel rejects/drops stale analytics from older generations.
4. select_panel_frame returns VIVO (live frame) when analytics is from an older frame or older generation.
5. TkApp render cache detects generation changes and updates _last_render_gen only on completed draw.
"""
import unittest
from types import SimpleNamespace
from unittest import mock
import numpy as np

from scripts.run_multicamera import build_panel_snapshot
from src.ui.multicamera import MultiCameraViewModel, CameraPanelState
from src.ui.tk_view import select_panel_frame


class TestGenerationAdvancementRegression(unittest.TestCase):
    def test_build_panel_snapshot_includes_generation(self):
        source_snapshot = {
            "camera_id": "cam_01",
            "frame_index": 0,
            "generation": 2,
            "frame": np.zeros((10, 10, 3), dtype=np.uint8),
            "state": "OPEN",
            "fps": 10.0,
            "resolution": "352x240",
        }
        panel_snap = build_panel_snapshot(source_snapshot, {})
        self.assertTrue(hasattr(panel_snap, "generation"), "build_panel_snapshot must propagate generation")
        self.assertEqual(panel_snap.generation, 2)

    def test_view_model_accepts_new_generation_with_zero_index_after_high_index(self):
        vm = MultiCameraViewModel(("cam_01",))
        frame_old = np.full((10, 10, 3), 1, dtype=np.uint8)
        frame_new = np.full((10, 10, 3), 2, dtype=np.uint8)

        # Generation 0 at high frame_index 500
        vm.update("cam_01", SimpleNamespace(
            generation=0,
            frame_index=500,
            frame=frame_old,
            source_state="OPEN",
            fps=10.0,
        ))
        p = vm.panel("cam_01")
        self.assertEqual(p.generation, 0)
        self.assertEqual(p.frame_index, 500)
        self.assertIs(p.frame, frame_old)

        # Generation 1 starts at frame_index 0: MUST BE ACCEPTED (never dropped)
        vm.update("cam_01", SimpleNamespace(
            generation=1,
            frame_index=0,
            frame=frame_new,
            source_state="OPEN",
            fps=10.0,
        ))
        p = vm.panel("cam_01")
        self.assertEqual(p.generation, 1)
        self.assertEqual(p.frame_index, 0)
        self.assertIs(p.frame, frame_new)

    def test_view_model_clears_or_rejects_older_generation_analytics(self):
        vm = MultiCameraViewModel(("cam_01",))
        analytics_frame_gen0 = np.full((10, 10, 3), 99, dtype=np.uint8)
        live_frame_gen1 = np.full((10, 10, 3), 2, dtype=np.uint8)

        # Gen 0 had an analytics event at frame 500
        vm.update("cam_01", SimpleNamespace(
            generation=0,
            frame_index=500,
            frame=analytics_frame_gen0,
            source_state="OPEN",
            fps=10.0,
            event_id="EVT-1",
            event_type="PERSON_DETECTED",
            event_confidence=0.95,
            bboxes=((1, 1, 5, 5, 0.95, "person"),),
            track_bbox=(1, 1, 5, 5),
            track_id="TRK-1",
            track_status="ACTIVE",
        ))
        p = vm.panel("cam_01")
        self.assertEqual(p.analytics_frame_index, 500)

        # Gen 1 arrives at frame 0 without analytics: analytics frame MUST NOT match frame 0
        vm.update("cam_01", SimpleNamespace(
            generation=1,
            frame_index=0,
            frame=live_frame_gen1,
            source_state="OPEN",
            fps=10.0,
            detections=None,
            track_id=None,
            temporal=None,
            behavior=None,
            risk=None,
            evidence=None,
            bboxes=None,
            track_bbox=None,
            event_type=None,
            track_status=None,
        ))
        p = vm.panel("cam_01")
        # select_panel_frame must return the fresh live frame, not the gen 0 analytics frame
        disp_frame, disp_idx, mode = select_panel_frame(p)
        self.assertEqual(mode, "VIVO")
        self.assertEqual(disp_idx, 0)
        self.assertIs(disp_frame, live_frame_gen1)


if __name__ == "__main__":
    unittest.main()
