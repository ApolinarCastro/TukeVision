"""LOOP-0019B-R2: transiciÃ³n STOP uniforme en las 4 cÃ¡maras.

Cubre el gap `STOP_RENDER_NOT_APPLIED_UNIFORMLY_TO_ALL_CAMERA_PANELS`:
tras STOP todas las cÃ¡maras deben terminar gris / CLOSED / OFFLINE / sin
analytics activos, independientemente del Ãºltimo metadata o frame.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src.ui.multicamera import MultiCameraViewModel
from src.ui.tk_view import (
    COLORS,
    apply_stopped_state,
    camera_status_color,
    frozen_render_required,
)

CAMERA_IDS = ("CAM-001", "CAM-002", "CAM-003", "CAM-004")


def _view():
    return MultiCameraViewModel(CAMERA_IDS)


def _snapshot(camera_id, *, frame_index, value, detection=True):
    return SimpleNamespace(
        frame_index=frame_index,
        frame=np.full((32, 48, 3), value, dtype=np.uint8),
        source_state="OPEN",
        fps=5.0,
        detections=2 if detection else None,
        track_id="TRK-7" if detection else None,
        track_status="ACTIVE" if detection else "",
        track_bbox=(1, 2, 30, 40) if detection else None,
        bboxes=((1, 2, 30, 40, 0.9, "person"),) if detection else None,
        event_type="PERSON_DETECTED" if detection else "",
        event_confidence=0.91 if detection else None,
        temporal="PERSON_PRESENCE ACTIVE 2.3s" if detection else "",
        behavior="PROLONGED_DWELL" if detection else "",
        risk="REVIEW 65" if detection else "",
        evidence="CAM-001/EVD-1/frame.jpg" if detection else "",
        resolution="640x360",
    )


def _assert_uniform(self, stopped):
    self.assertEqual(stopped["source_state"], "CLOSED")
    self.assertFalse(stopped["online"])
    self.assertIsNone(stopped["track_id"])
    self.assertEqual(stopped["track_status"], "")
    self.assertEqual(stopped["event_type"], "")
    self.assertIsNone(stopped["event_confidence"])
    self.assertEqual(stopped["temporal"], "")
    self.assertEqual(stopped["behavior"], "")
    self.assertEqual(stopped["risk"], "")
    self.assertIn("CLOSED", stopped["overlay"])
    self.assertIn("LAST FRAME", stopped["overlay"])
    self.assertIn("OFFLINE", stopped["overlay"])
    self.assertEqual(
        camera_status_color(stopped["source_state"]), COLORS["offline"]
    )


class TestUniformStopState(unittest.TestCase):
    def test_all_cameras_with_different_metadata_end_uniform(self):
        view = _view()
        for index, camera_id in enumerate(CAMERA_IDS, 1):
            view.update(
                camera_id,
                _snapshot(
                    camera_id,
                    frame_index=index * 10,
                    value=index,
                    detection=index % 2 == 0,
                ),
            )
        for camera_id in CAMERA_IDS:
            with self.subTest(camera_id=camera_id):
                _assert_uniform(self, apply_stopped_state(view.panel(camera_id)))

    def test_panel_with_last_analytics_frame_is_stopped_uniform(self):
        view = _view()
        view.update("CAM-001", _snapshot("CAM-001", frame_index=12, value=7, detection=True))
        self.assertIsNotNone(view.panel("CAM-001").analytics_frame)
        self.assertEqual(view.panel("CAM-001").analytics_frame_index, 12)
        _assert_uniform(self, apply_stopped_state(view.panel("CAM-001")))

    def test_panel_with_last_live_frame_is_stopped_uniform(self):
        view = _view()
        view.update("CAM-001", _snapshot("CAM-001", frame_index=12, value=7, detection=False))
        self.assertEqual(view.panel("CAM-001").analytics_frame_index, -1)
        _assert_uniform(self, apply_stopped_state(view.panel("CAM-001")))

    def test_panel_with_prior_detection_clears_active_analytics(self):
        view = _view()
        view.update("CAM-001", _snapshot("CAM-001", frame_index=9, value=3, detection=True))
        self.assertEqual(view.panel("CAM-001").track_id, "TRK-7")
        stopped = apply_stopped_state(view.panel("CAM-001"))
        self.assertIsNone(stopped["track_id"])
        self.assertEqual(stopped["event_type"], "")
        self.assertEqual(stopped["behavior"], "")
        self.assertEqual(stopped["risk"], "")

    def test_panel_without_prior_detection_is_stopped_uniform(self):
        view = _view()
        view.update("CAM-001", _snapshot("CAM-001", frame_index=9, value=3, detection=False))
        self.assertIsNone(view.panel("CAM-001").track_id)
        _assert_uniform(self, apply_stopped_state(view.panel("CAM-001")))

    def test_frozen_render_is_forced_for_every_camera_on_stop(self):
        rendered = {}
        for camera_id in CAMERA_IDS:
            with self.subTest(camera_id=camera_id):
                self.assertTrue(
                    frozen_render_required(rendered, camera_id, False, False)
                )
        rendered["CAM-001"] = True
        for camera_id in ("CAM-002", "CAM-003", "CAM-004"):
            with self.subTest(after_first=camera_id):
                self.assertTrue(
                    frozen_render_required(rendered, camera_id, False, False)
                )

    def test_frozen_render_skips_only_already_rendered_cameras(self):
        rendered = {camera_id: True for camera_id in CAMERA_IDS}
        for camera_id in CAMERA_IDS:
            with self.subTest(camera_id=camera_id):
                self.assertFalse(
                    frozen_render_required(rendered, camera_id, False, False)
                )
        self.assertTrue(
            frozen_render_required(rendered, "CAM-001", True, False)
        )

    def test_stop_transition_is_centralized_via_apply_stopped_state(self):
        source = Path("src/ui/tk_view.py").read_text(encoding="utf-8")
        self.assertIn("apply_stopped_state", source)
        self.assertIn("self._stopped_rendered = {", source)
        self.assertIn("_stopped_rendered[camera_id]", source)
        self.assertNotIn("self._stopped_rendered = False", source)


if __name__ == "__main__":
    unittest.main()