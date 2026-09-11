import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.run_multicamera import (
    build_panel_snapshot,
)
from src.domain.catalog import StoreCatalog
from src.domain.models import SourceType
from src.observability.runtime_trace import BoundedRuntimeTrace
from src.ui.tk_view import (
    annotate_frame,
    fit_frame_to_panel,
    multicamera_control_state,
    panel_status_text,
    select_panel_frame,
)

import numpy as np


class TestMulticameraEntrypoint(unittest.TestCase):
    def test_launcher_selects_mode_without_secrets(self):
        launcher = Path("start_tukevision.ps1").read_text(encoding="utf-8")
        entrypoint = Path("scripts/run_multicamera.py").read_text(encoding="utf-8")
        self.assertIn('Mode -ieq "Multicamera"', launcher)
        self.assertIn("run_multicamera.py", launcher)
        self.assertIn("SourceManager", entrypoint)
        self.assertIn("OperationalPipeline", entrypoint)
        self.assertNotIn("rtsp://", launcher.lower())
        self.assertNotIn("password=", launcher.lower())
        self.assertNotIn("VideoCapture", entrypoint)

    def test_canonical_result_is_adapted_without_fabricating_values(self):
        event = SimpleNamespace(
            metadata={"detections": 2, "bboxes": [[10, 20, 80, 120, 0.91, "person"]]},
            event_type="PERSON_DETECTED", confidence=0.91,
        )
        track = SimpleNamespace(track_id="TRK-7", status="ACTIVE", last_bbox=(10, 20, 80, 120))
        activity = SimpleNamespace(activity_type="PERSON_PRESENCE", status="ACTIVE", duration_ms=2300)
        signal = SimpleNamespace(signal_type="PROLONGED_DWELL")
        risk = SimpleNamespace(risk_event_type="REVIEW", risk_score=65)
        behavior = SimpleNamespace(signals=(signal,), risk_event=risk)
        source = {"frame_index": 9, "frame": object(), "state": "OPEN", "fps": 4.0,
                  "resolution": "640x360"}
        result = {"event": event, "track": track, "temporal_activity": activity,
                  "behavior": behavior, "evidence": {"relative_path": "CAM-001/EVD/frame.jpg"}}
        panel = build_panel_snapshot(source, result)
        self.assertEqual(panel.detections, 2)
        self.assertEqual(panel.track_id, "TRK-7")
        self.assertEqual(panel.temporal, "PERSON_PRESENCE ACTIVE 2.3s")
        self.assertEqual(panel.behavior, "PROLONGED_DWELL")
        self.assertEqual(panel.risk, "REVIEW 65")
        self.assertEqual(panel.evidence, "CAM-001/EVD/frame.jpg")
        self.assertEqual(panel.bboxes[0][:4], (10, 20, 80, 120))
        self.assertEqual(panel.event_type, "PERSON_DETECTED")
        self.assertEqual(panel.track_status, "ACTIVE")
        self.assertEqual(panel.resolution, "640x360")

    def test_real_bbox_and_track_are_drawn_without_mutating_source(self):
        frame = np.zeros((100, 160, 3), dtype=np.uint8)
        panel = SimpleNamespace(
            frame_index=9,
            bboxes=((10, 20, 80, 90, 0.91, "person"),),
            track_id="TRK-7", track_bbox=(10, 20, 80, 90),
            event_type="PERSON_DETECTED", analytics_frame_index=9,
        )
        annotated = annotate_frame(frame, panel)
        self.assertEqual(int(frame.sum()), 0)
        self.assertGreater(int(annotated.sum()), 0)
        self.assertTrue(np.any(annotated[20, 10] != 0))

    def test_stale_analytics_are_not_drawn_over_a_newer_video_frame(self):
        frame = np.zeros((100, 160, 3), dtype=np.uint8)
        panel = SimpleNamespace(
            frame_index=10,
            bboxes=((10, 20, 80, 90, 0.91, "person"),),
            track_id="TRK-7", track_bbox=(10, 20, 80, 90),
            analytics_frame_index=9,
        )

        annotated = annotate_frame(frame, panel)

        self.assertEqual(int(annotated.sum()), 0)

    def test_panel_selects_exact_analytics_frame_for_persistent_overlay(self):
        live_frame = np.zeros((100, 160, 3), dtype=np.uint8)
        analytics_frame = np.full((100, 160, 3), 17, dtype=np.uint8)
        # Case A: Live stream has advanced beyond analyzed frame (frame_index=10, analytics_frame_index=9)
        # Operator screen must present fresh live frame without freezing on old analytics frame
        panel_advancing = SimpleNamespace(
            frame=live_frame,
            frame_index=10,
            analytics_frame=analytics_frame,
            analytics_frame_index=9,
            bboxes=((10, 20, 80, 90, 0.91, "person"),),
            track_id="TRK-7",
            track_bbox=(10, 20, 80, 90),
        )
        selected, selected_index, mode = select_panel_frame(panel_advancing)
        self.assertIs(selected, live_frame)
        self.assertEqual(selected_index, 10)
        self.assertEqual(mode, "VIVO")

        # Case B: Current frame matches analytics frame (frame_index=9, analytics_frame_index=9)
        # Exact analytics frame and overlays are displayed
        panel_fresh = SimpleNamespace(
            frame=live_frame,
            frame_index=9,
            analytics_frame=analytics_frame,
            analytics_frame_index=9,
            bboxes=((10, 20, 80, 90, 0.91, "person"),),
            track_id="TRK-7",
            track_bbox=(10, 20, 80, 90),
        )
        selected_fresh, selected_index_fresh, mode_fresh = select_panel_frame(panel_fresh)
        annotated = annotate_frame(
            selected_fresh,
            panel_fresh,
            displayed_frame_index=selected_index_fresh,
        )
        self.assertIs(selected_fresh, analytics_frame)
        self.assertEqual(selected_index_fresh, 9)
        self.assertEqual(mode_fresh, "ANALITICA")
        self.assertGreater(int(annotated.sum()), int(analytics_frame.sum()))

    def test_recorder_cameras_resolve_main_stream_descriptor_subtype(self):
        config = {
            "multistore": {
                "enabled": True,
                "organization": {
                    "organization_id": "ORG-TEST",
                    "organization_name": "Test",
                    "created_at": "2026-08-19T00:00:00Z",
                },
                "stores": [{
                    "store_id": "STORE-001",
                    "organization_id": "ORG-TEST",
                    "store_name": "Tienda Test",
                    "timezone": "UTC",
                    "evidence_namespace": "data/runtime_evidence/STORE-001",
                    "recorders": [{
                        "recorder_id": "DVR-001",
                        "store_id": "STORE-001",
                        "recorder_name": "DVR Principal",
                        "recorder_type": "DVR",
                        "host": "192.168.10.20",
                        "port": 554,
                        "vendor": "Dahua",
                        "credentials_ref": "TK_TEST_CREDS",
                        "total_channels": 16,
                        "cameras": [
                            {
                                "camera_id": "CAM-007",
                                "store_id": "STORE-001",
                                "channel_number": 7,
                                "camera_name": "Camara 07",
                                "source_type": "RTSP_STREAM",
                                "host": "192.168.10.20",
                                "stream_main": "rtsp://192.168.10.20/cam/realmonitor",
                                "evidence_namespace": "data/runtime_evidence/STORE-001/CAM-007/",
                            },
                            {
                                "camera_id": "CAM-001",
                                "store_id": "STORE-001",
                                "channel_number": 1,
                                "camera_name": "Camara 01",
                                "source_type": "RTSP_STREAM",
                                "host": "192.168.10.20",
                                "stream_sub": "rtsp://192.168.10.20/cam/realmonitor",
                                "evidence_namespace": "data/runtime_evidence/STORE-001/CAM-001/",
                            },
                        ],
                    }],
                    "direct_cameras": [],
                }],
            }
        }
        catalog = StoreCatalog.from_dict(config)
        entries = catalog.camera_descriptors(password_resolver=lambda ref: "s3cret")
        by_id = {entry.camera_id: entry.descriptor for entry in entries}
        self.assertEqual(by_id["CAM-007"].channel, 7)
        self.assertEqual(by_id["CAM-007"].subtype, 0)
        self.assertEqual(by_id["CAM-001"].subtype, 1)
        self.assertEqual(by_id["CAM-007"].password, "s3cret")
        self.assertNotIn("s3cret", repr(by_id["CAM-007"]))

    def test_panel_text_exposes_operator_verification_fields(self):
        panel = SimpleNamespace(
            frame=object(),
            frame_index=11,
            analytics_frame=object(),
            source_state="OPEN", resolution="640x360", detections=2,
            track_id="TRK-7", track_status="ACTIVE",
            event_type="PERSON_DETECTED", event_confidence=0.91,
            analytics_frame_index=9,
            bboxes=((10, 20, 80, 90, 0.91, "person"),),
            track_bbox=(10, 20, 80, 90),
            temporal="PERSON_PRESENCE ACTIVE 2.3s",
            behavior="PROLONGED_DWELL", risk="REVIEW 65",
            evidence="CAM-001/EVD/frame.jpg",
        )
        text = panel_status_text(panel)
        self.assertIn("PERSON_DETECTED 91%", text)
        self.assertIn("Track: TRK-7 (ACTIVE)", text)
        self.assertIn("Imagen: VIVO 11", text)
        self.assertIn("Video: 11", text)
        self.assertIn("Analítico: 9", text)
        self.assertIn("Evidencia: frame.jpg", text)

    def test_runtime_trace_is_bounded_and_records_ui_boundary(self):
        trace = BoundedRuntimeTrace(("CAM-001",))
        result = {
            "observation": object(),
            "event": SimpleNamespace(metadata={"detections": 2}),
            "track": object(), "temporal_activity": object(),
            "behavior": SimpleNamespace(signals=(object(),)),
            "evidence": {"relative_path": "CAM-001/EVD/frame.jpg"},
        }
        trace.observe_pipeline_result("CAM-001", 10, result)
        trace.mark_ui_model_received("CAM-001", 10)
        trace.mark_ui_rendered("CAM-001", 10)
        snapshot = trace.snapshot()["CAM-001"]
        self.assertEqual(snapshot["FRAME_RECEIVED"], 1)
        self.assertEqual(snapshot["DETECTIONS_RETURNED"], 2)
        self.assertEqual(snapshot["UI_MODEL_RECEIVED"], 1)
        self.assertEqual(snapshot["UI_RENDERED"], 1)
        self.assertNotIn("frame", snapshot)

    def test_multicamera_controls_follow_runtime_and_hide_legacy(self):
        running = multicamera_control_state("RUNNING")
        stopped = multicamera_control_state("STOPPED")
        self.assertFalse(running["show_legacy"])
        self.assertTrue(running["stop_enabled"])
        self.assertFalse(stopped["stop_enabled"])

    def test_panel_fit_is_consistent_without_upscaling_source(self):
        frame = np.full((100, 200, 3), 255, dtype=np.uint8)
        fitted = fit_frame_to_panel(frame, width=400, height=240)
        self.assertEqual(fitted.shape, (240, 400, 3))
        self.assertEqual(int(np.count_nonzero(fitted == 255)), frame.size)


if __name__ == "__main__":
    unittest.main()
