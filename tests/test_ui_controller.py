"""Pruebas del controlador y estado de la interfaz (sin Tk ni ventana).

Cubren: estado inicial, transiciones READY->RUNNING->STOPPED, error de
fuente, actualización de snapshot, actualización de alertas, redacción
RTSP, señal de stop, backpressure de cola y cierre seguro.
"""

import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

from src.alerts.models import Alert
from src.app.pipeline import PipelineSummary
from src.app.pipeline import FrameSnapshot
from src.tracking.person_tracker import TrackedObject
from src.ui.controller import UiController, StopRequested, build_source
from src.ui.state import AppStatus, UiState, followed_track_id, redact_source_display

CONFIG = {
    "video": {"max_width": 640, "process_every_n_frames": 1},
    "detection": {
        "model": "yolo11n.pt", "class_ids": [0], "confidence_threshold": 0.35,
        "device": "cpu", "image_size": 640,
    },
    "zone": {"id": "ZONE-001", "name": "Zona piloto",
             "polygon": [[100, 100], [540, 100], [540, 420], [100, 420]]},
    "business": {"store_id": "STORE-001", "camera_id": "CAM-001",
                 "max_stay_seconds": 30.0, "remain_interval_frames": 30},
    "alerts": {"risk_threshold": 60},
}


def _obj(track_id, x1=200, y1=200, x2=260, y2=360):
    return TrackedObject(track_id=track_id, x1=x1, y1=y1, x2=x2, y2=y2,
                         confidence=0.9, class_id=0)


def _frame(height=480, width=640):
    return np.zeros((height, width, 3), dtype=np.uint8)


def _snapshot(frame_index=1, tracked=(), stays=None, in_zone=(),
              latest_alert=None, latest_evidence_path=None,
              risk_text="", source_state="OPEN", persons_detected=0):
    return FrameSnapshot(
        frame_index=frame_index,
        frame=_frame(),
        source_type="FILE",
        source_path="data/input/video.mp4",
        source_state=source_state,
        fps=30.0,
        tracked_objects=tuple(tracked),
        stays_seconds=stays or {},
        in_zone_track_ids=tuple(in_zone),
        risk_text=risk_text,
        latest_alert=latest_alert,
        latest_evidence_path=latest_evidence_path,
        frames_processed=frame_index + 1,
        persons_detected=persons_detected,
        alerts_total=1 if latest_alert else 0,
        evidence_total=1 if latest_evidence_path else 0,
    )


def _alert(alert_id="ALR-00001"):
    return Alert(alert_id=alert_id, event_id="EVT-00001", risk_score=80,
                 rule_id="RULE-PERMANENCIA-001",
                 created_at="2026-01-01T00:00:00Z", status="NEW",
                 explanation="x")


def _ok_pipeline(frames=3, alert_every=100):
    """Pipeline fake que emite snapshots y devuelve resumen OK."""

    class FakePipeline:
        def process_source(self, source, on_frame=None):
            for i in range(frames):
                if on_frame is not None:
                    on_frame(_snapshot(frame_index=i, tracked=(_obj(1),),
                                       stays={1: float(i)},
                                       in_zone=(1,),
                                       persons_detected=i + 1))
            return PipelineSummary(
                video_path="data/input/video.mp4", frames_processed=frames,
                persons_detected=frames, tracks_created=1,
                observations_created=frames, events_created=0,
                alerts_created=0, evidence_created=0,
                output_video="out.mp4", final_status="OK",
            )

    return FakePipeline()


class _BlockingPipeline:
    """Pipeline fake que se mantiene en ejecución hasta una señal."""

    def __init__(self, release: threading.Event) -> None:
        self._release = release
        self.frames = 0

    def process_source(self, source, on_frame=None):
        while not self._release.is_set():
            if on_frame is not None:
                on_frame(_snapshot(frame_index=0, tracked=(_obj(1),),
                                   stays={1: 1.0}, in_zone=(1,),
                                   persons_detected=1))
            time.sleep(0.005)
        return PipelineSummary(video_path="x", frames_processed=self.frames,
                               persons_detected=0, tracks_created=0,
                               observations_created=0, events_created=0,
                               alerts_created=0, evidence_created=0,
                               output_video="o", final_status="OK")


class TestUiState(unittest.TestCase):

    def test_estado_inicial(self) -> None:
        controller = UiController(config=CONFIG)
        state = controller.poll_state()
        self.assertEqual(state["status"], AppStatus.READY)
        self.assertEqual(state["zone_id"], "ZONE-001")
        self.assertIsNone(state["followed_track"])

    def test_followed_prioriza_zona(self) -> None:
        snap = _snapshot(tracked=(_obj(1), _obj(2)), stays={1: 5.0, 2: 20.0},
                         in_zone=(1,))
        self.assertEqual(followed_track_id(snap), 1)

    def test_followed_sin_zona_mayor_permanencia(self) -> None:
        snap = _snapshot(tracked=(_obj(1), _obj(2)), stays={1: 5.0, 2: 20.0})
        self.assertEqual(followed_track_id(snap), 2)

    def test_followed_vacio(self) -> None:
        self.assertIsNone(followed_track_id(_snapshot()))


class TestRedaction(unittest.TestCase):

    def test_rtsp_nunca_muestra_url(self) -> None:
        snap = _snapshot()
        snap.__dict__["source_type"] = "RTSP"
        snap.__dict__["source_path"] = "rtsp://user:pass@host/stream"
        text = redact_source_display("RTSP", snap)
        self.assertEqual(text, "RTSP: REDACTED")
        self.assertNotIn("user", text)
        self.assertNotIn("pass", text)


class TestControllerTransitions(unittest.TestCase):

    def test_ready_a_running(self) -> None:
        release = threading.Event()
        controller = UiController(
            config=CONFIG,
            pipeline_factory=lambda: _BlockingPipeline(release),
        )
        controller.start("FILE", "data/input/video.mp4")
        self.assertEqual(controller.status, AppStatus.RUNNING)
        release.set()
        controller.join(timeout=5)
        self.assertEqual(controller.status, AppStatus.STOPPED)
        self.assertEqual(controller.poll_state()["final_status"], "OK")

    def test_no_doble_inicio(self) -> None:
        release = threading.Event()
        controller = UiController(
            config=CONFIG,
            pipeline_factory=lambda: _BlockingPipeline(release),
        )
        controller.start("FILE", "data/input/video.mp4")
        with self.assertRaises(ValueError):
            controller.start("FILE", "data/input/other.mp4")
        release.set()
        controller.join(timeout=5)

    def test_snapshot_update(self) -> None:
        controller = UiController(config=CONFIG, pipeline_factory=_ok_pipeline)
        controller.start("FILE", "data/input/video.mp4")
        controller.join(timeout=5)
        state = controller.poll_state()
        self.assertEqual(state["followed_track"], 1)
        self.assertEqual(state["frames_processed"], 3)
        self.assertEqual(state["persons_detected"], 3)

    def test_backpressure_cola_tamano_1(self) -> None:
        controller = UiController(config=CONFIG, pipeline_factory=_ok_pipeline)
        controller.start("FILE", "data/input/video.mp4")
        controller.join(timeout=5)
        # Tras el fin, la cola conserva a lo sumo 1 elemento
        snap = controller.poll_visual()
        leftover = controller.poll_visual()
        self.assertIsNotNone(snap)
        self.assertIsNone(leftover)
        self.assertEqual(snap.frame_index, 2)  # el último

    def test_alert_update(self) -> None:
        def pipeline():
            class Fake:
                def process_source(self, source, on_frame=None):
                    on_frame(_snapshot(latest_alert=_alert(), latest_evidence_path="evidence/ALR-00001"))
                    return PipelineSummary(video_path="x", frames_processed=1,
                                           persons_detected=0, tracks_created=0,
                                           observations_created=0, events_created=0,
                                           alerts_created=1, evidence_created=1,
                                           output_video="o", final_status="OK")
            return Fake()

        controller = UiController(config=CONFIG, pipeline_factory=pipeline)
        controller.start("FILE", "data/input/video.mp4")
        controller.join(timeout=5)
        state = controller.poll_state()
        self.assertEqual(len(state["alert_log"]), 1)
        self.assertEqual(state["alert_log"][0]["alert_id"], "ALR-00001")
        self.assertEqual(state["latest_risk_score"], 80)
        self.assertIn("evidence/ALR-00001", state["evidence_paths"])

    def test_source_error(self) -> None:
        def bad_builder(kind, value, config):
            raise ValueError("Ruta inválida")

        controller = UiController(config=CONFIG, pipeline_factory=_ok_pipeline,
                                  source_builder=bad_builder)
        controller.start("FILE", "data/input/nonexistent.mp4")
        controller.join(timeout=5)
        state = controller.poll_state()
        self.assertEqual(state["status"], AppStatus.STOPPED)
        self.assertEqual(state["final_status"], "ERROR")
        self.assertIn("Ruta inválida", state["error"])

    def test_stop_signal(self) -> None:
        release = threading.Event()

        def pipeline():
            class Fake:
                def process_source(self, source, on_frame=None):
                    while not release.is_set():
                        on_frame(_snapshot(frame_index=0))
                        time.sleep(0.01)
                    return PipelineSummary(video_path="x", frames_processed=1,
                                           persons_detected=0, tracks_created=0,
                                           observations_created=0, events_created=0,
                                           alerts_created=0, evidence_created=0,
                                           output_video="o", final_status="OK")
            return Fake()

        controller = UiController(config=CONFIG, pipeline_factory=pipeline)
        controller.start("FILE", "data/input/video.mp4")
        time.sleep(0.1)
        controller.stop()
        controller.join(timeout=5)
        release.set()
        state = controller.poll_state()
        self.assertEqual(state["final_status"], "STOPPED_BY_USER")

    def test_stop_requested_lanza_desde_on_frame(self) -> None:
        controller = UiController(config=CONFIG, pipeline_factory=_ok_pipeline)
        controller._stop.set()
        with self.assertRaises(StopRequested):
            controller._on_frame(_snapshot())

    def test_close_libera_y_limpia(self) -> None:
        controller = UiController(config=CONFIG, pipeline_factory=_ok_pipeline)
        controller.start("FILE", "data/input/video.mp4")
        controller.close()
        self.assertEqual(controller.status, AppStatus.STOPPED)
        self.assertIsNone(controller.poll_visual())


class TestBuildSource(unittest.TestCase):

    def test_file_y_webcam_y_rtsp(self) -> None:
        from src.capture.video_source import VideoSource
        from src.capture.live_sources import WebcamSource, RTSPSource
        self.assertIsInstance(build_source("FILE", "x.mp4", CONFIG), VideoSource)
        self.assertIsInstance(build_source("WEBCAM", "0", CONFIG), WebcamSource)
        self.assertIsInstance(
            build_source("RTSP", "rtsp://h/s", CONFIG), RTSPSource
        )

    def test_rtsp_sin_url_error(self) -> None:
        with self.assertRaises(ValueError):
            build_source("RTSP", "", CONFIG)

    def test_fuente_no_soportada(self) -> None:
        with self.assertRaises(ValueError):
            build_source("HLS", "x", CONFIG)


if __name__ == "__main__":
    unittest.main()
