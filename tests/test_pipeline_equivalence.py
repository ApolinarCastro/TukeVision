"""Equivalencia de salida del pipeline con y sin el hook on_frame.

Auditoría LOOP-0009C, sección 12:
    RUN A: pipeline sin on_frame
    RUN B: pipeline con on_frame no-op
Deben producir exactamente los mismos conteos: frames, detecciones,
tracks, observaciones, eventos, alertas y evidencias.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np

from src.app.pipeline import Pipeline
from src.evidence.store import EvidenceStore

from tests.test_pipeline import CONFIG, _detection


def _scene_tracked_object():
    from src.tracking.person_tracker import TrackedObject
    return TrackedObject(track_id=1, x1=200, y1=300, x2=300, y2=400,
                         confidence=0.9, class_id=0)


def _build_pipeline(evidence_dir: str) -> Pipeline:
    pipeline = Pipeline(config=CONFIG)
    # Evidencia en directorio temporal: cada run usa su propio dir limpio
    pipeline._evidence_store = EvidenceStore(base_dir=evidence_dir)
    return pipeline


def _run(pipeline: Pipeline, frames_count: int, on_frame=None):
    """Ejecuta el pipeline con mocks deterministas y devuelve el resumen."""
    mock_detector = MagicMock()
    mock_detector.detect.return_value = MagicMock(detections=[_detection()])
    pipeline._detector = mock_detector

    tracker_result = MagicMock()
    tracker_result.tracked_objects = [_scene_tracked_object()]
    mock_tracker = MagicMock()
    mock_tracker.update.return_value = tracker_result
    pipeline._tracker = mock_tracker

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    source = MagicMock()
    source.source_type = "FILE"
    source.metadata = MagicMock(path="data/input/video.mp4", fps=30.0)
    source.state = "OPEN"
    source.open.return_value = MagicMock(fps=30.0, width=640, height=480)
    source.frames.return_value = [
        (i, frame) for i in range(frames_count)
    ]

    return pipeline.process_source(source, on_frame=on_frame)


class TestPipelineEquivalence(unittest.TestCase):

    def test_run_a_y_run_b_producen_el_mismo_resumen(self) -> None:
        frames_count = 1200  # 40s a 30fps: supera max_stay -> evento+alerta+evidencia

        with tempfile.TemporaryDirectory() as tmp_a:
            summary_a = _run(_build_pipeline(str(Path(tmp_a) / "a")), frames_count)

        with tempfile.TemporaryDirectory() as tmp_b:
            summary_b = _run(
                _build_pipeline(str(Path(tmp_b) / "b")),
                frames_count,
                on_frame=lambda snapshot: None,
            )

        self.assertEqual(summary_a.frames_processed, summary_b.frames_processed)
        self.assertEqual(summary_a.persons_detected, summary_b.persons_detected)
        self.assertEqual(summary_a.tracks_created, summary_b.tracks_created)
        self.assertEqual(summary_a.observations_created, summary_b.observations_created)
        self.assertEqual(summary_a.events_created, summary_b.events_created)
        self.assertEqual(summary_a.alerts_created, summary_b.alerts_created)
        self.assertEqual(summary_a.evidence_created, summary_b.evidence_created)
        self.assertEqual(summary_a.final_status, summary_b.final_status)
        self.assertEqual(summary_a.final_status, "OK")

    def test_on_frame_no_op_no_altera_conteos(self) -> None:
        """El hook no crea observaciones, eventos, alertas ni evidencia."""
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = _build_pipeline(str(Path(tmp) / "a"))
            seen = {"calls": 0}

            def no_op(snapshot) -> None:
                seen["calls"] += 1

            summary = _run(pipeline, 60, on_frame=no_op)

            self.assertEqual(seen["calls"], 60)
            # El hook no crea eventos, alertas ni evidencia
            self.assertEqual(summary.events_created, 0)
            self.assertEqual(summary.alerts_created, 0)
            self.assertEqual(summary.evidence_created, 0)


if __name__ == "__main__":
    unittest.main()
