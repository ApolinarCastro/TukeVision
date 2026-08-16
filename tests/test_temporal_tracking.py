"""Pruebas deterministas de tracking LOCAL + actividad temporal (LOOP-0018R).

Cubren: creación de track; STARTED->ACTIVE->ENDED; actualización dentro de la
ventana; cierre por timeout; nuevo track tras timeout; independencia de IDs por
cámara; cuatro cámaras lógicas aisladas; dos objetos/personas distintos en una
cámara cuando el bbox permite distinguirlos; asociación IoU; eventos
incompatibles no mezclados; timestamps UTC; serialización LocalTrack y
TemporalActivity; duration; event_count; evidence first/latest/best; retención
acotada (event refs, completed history, active tracks, evidence refs); error
isolation; configuración inválida; métricas; determinismo; secret leak.

Usa eventos duck-typed (compatibles con InferenceEvent) para no depender de la
capa de inferencia.
"""

import json
import unittest
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from src.temporal.contract import (
    ACTIVE,
    ENDED,
    STARTED,
    LocalTrack,
    TemporalActivity,
    TemporalConfigError,
    TemporalError,
    TemporalValidationError,
    duration_ms,
    parse_iso_utc,
)
from src.temporal.tracker import LocalTracker, build_tracker, compute_iou

T0 = "2026-08-16T17:00:00.000000Z"


@dataclass
class FakeEvent:
    """Evento canónico de prueba (duck-typing compatible con InferenceEvent)."""

    event_id: str
    camera_id: str
    timestamp: str
    event_type: str = "PERSON_DETECTED"
    confidence: Optional[float] = 0.9
    evidence_ref: Optional[str] = None
    inference_ref: Optional[str] = None


def mk(camera_id, ts, event_type="PERSON_DETECTED", confidence=0.9,
       evidence_ref=None, seq=1):
    return FakeEvent(
        event_id=f"EVT-{camera_id}-{seq:06d}",
        camera_id=camera_id,
        timestamp=ts,
        event_type=event_type,
        confidence=confidence,
        evidence_ref=evidence_ref,
        inference_ref=f"INF-{camera_id}-{seq:06d}",
    )


def ts_at(seconds: int) -> str:
    from datetime import timedelta

    return (parse_iso_utc(T0) + timedelta(seconds=seconds)).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


class TestLocalTrackContract(unittest.TestCase):

    def test_minimal_track_created(self) -> None:
        track = LocalTrack(
            track_id="TRK-CAM-07-000001",
            camera_id="CAM-07",
            object_type="person",
            started_at=T0,
            last_seen_at=T0,
        )
        self.assertEqual(track.status, STARTED)
        self.assertEqual(track.event_count, 0)
        self.assertIsNone(track.confidence)

    def test_track_validation(self) -> None:
        with self.assertRaises(TemporalValidationError):
            LocalTrack("", "CAM-07", "person", T0, T0)
        with self.assertRaises(TemporalValidationError):
            LocalTrack("TRK-1", "", "person", T0, T0)
        with self.assertRaises(TemporalValidationError):
            LocalTrack("TRK-1", "CAM-07", "person", T0, T0, status="BOGUS")
        with self.assertRaises(TemporalValidationError):
            LocalTrack("TRK-1", "CAM-07", "person", T0, T0, confidence=1.5)
        with self.assertRaises(TemporalValidationError):
            LocalTrack("TRK-1", "CAM-07", "person", T0, T0,
                       last_bbox=(10, 10, 5, 20))

    def test_track_serialization_roundtrip(self) -> None:
        track = LocalTrack(
            track_id="TRK-CAM-07-000001",
            camera_id="CAM-07",
            object_type="person",
            started_at=T0,
            last_seen_at=T0,
            status=ACTIVE,
            event_count=3,
            confidence=0.9,
            last_bbox=(10, 20, 110, 220),
            event_refs=("EVT-1", "EVT-2", "EVT-3"),
            evidence_refs={"first": "E1", "latest": "E3", "best": "E3"},
        )
        data = track.to_dict()
        json.dumps(data)
        self.assertEqual(LocalTrack.from_dict(data), track)

    def test_activity_serialization_roundtrip(self) -> None:
        activity = TemporalActivity(
            activity_id="ACT-CAM-07-000001",
            track_id="TRK-CAM-07-000001",
            source_id="CAM-07",
            activity_type="PERSON_PRESENCE",
            started_at=T0,
            last_seen_at=ts_at(3),
            status=ENDED,
            ended_at=ts_at(3),
            duration_ms=3000,
            event_count=3,
            confidence=0.9,
        )
        data = activity.to_dict()
        json.dumps(data)
        self.assertEqual(TemporalActivity.from_dict(data), activity)

    def test_duration_ms(self) -> None:
        self.assertEqual(duration_ms(T0, ts_at(3)), 3000)
        self.assertEqual(duration_ms(T0, T0), 0)

    def test_invalid_timestamp(self) -> None:
        with self.assertRaises(TemporalValidationError):
            parse_iso_utc("not-a-timestamp")


class TestIoU(unittest.TestCase):

    def test_iou_basic(self) -> None:
        self.assertAlmostEqual(
            compute_iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0
        )
        self.assertAlmostEqual(
            compute_iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0
        )
        # Bounding boxes que se superponen a medias (5x10 de 10x10 -> 50/150).
        self.assertGreater(compute_iou((0, 0, 10, 10), (5, 0, 15, 10)), 0.0)

    def test_iou_no_area(self) -> None:
        self.assertEqual(compute_iou((0, 0, 0, 0), (0, 0, 0, 0)), 0.0)


class TestTrackLifecycle(unittest.TestCase):

    def test_continuity_three_events_one_track(self) -> None:
        """Prueba obligatoria de continuidad conceptual.

        CAM-07 PERSON_DETECTED @ T0, T0+1s, T0+2s -> un solo track_id,
        una sola actividad y event_count=3.
        """
        tracker = LocalTracker(clock=lambda: ts_at(99))
        tracker.register_camera("CAM-07")
        for i, seconds in enumerate((0, 1, 2)):
            tracker.ingest(mk("CAM-07", ts_at(seconds), seq=i + 1))
        tracks = tracker.active_tracks("CAM-07")
        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        self.assertEqual(track.event_count, 3)
        self.assertEqual(track.status, ACTIVE)
        self.assertEqual(len(tracker.active_activities("CAM-07")), 1)
        activity = tracker.active_activities("CAM-07")[0]
        self.assertEqual(activity.event_count, 3)
        self.assertEqual(activity.status, ACTIVE)
        self.assertEqual(activity.activity_type, "PERSON_PRESENCE")
        tracker.close()

    def test_track_started_after_first_event(self) -> None:
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        track = tracker.active_tracks("CAM-07")[0]
        self.assertEqual(track.status, STARTED)
        self.assertEqual(track.event_count, 1)
        tracker.close()

    def test_update_within_window_sets_active(self) -> None:
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(1), seq=2))
        track = tracker.active_tracks("CAM-07")[0]
        self.assertEqual(track.status, ACTIVE)
        self.assertEqual(track.event_count, 2)
        tracker.close()

    def test_timeout_ends_track(self) -> None:
        """Prueba obligatoria de timeout: tras track_timeout -> ENDED."""
        tracker = LocalTracker(track_timeout_ms=5000, association_window_ms=2000)
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        # Un evento mucho más tarde dispara el cierre por timeout.
        tracker.ingest(mk("CAM-07", ts_at(6), seq=2))
        self.assertEqual(tracker.active_count("CAM-07"), 1)  # el nuevo track
        completed = tracker.completed("CAM-07")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].status, ENDED)
        # El nuevo track es distinto del cerrado.
        self.assertNotEqual(completed[0].track_id, tracker.active_tracks("CAM-07")[0].track_id)
        tracker.close()

    def test_new_track_after_timeout_not_resurrected(self) -> None:
        """Prueba obligatoria: detección posterior crea nuevo track."""
        tracker = LocalTracker(track_timeout_ms=5000)
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        first_id = tracker.active_tracks("CAM-07")[0].track_id
        tracker.ingest(mk("CAM-07", ts_at(6), seq=2))
        second = tracker.active_tracks("CAM-07")[0]
        self.assertNotEqual(second.track_id, first_id)
        self.assertEqual(second.event_count, 1)
        tracker.close()

    def test_window_expired_creates_new_track(self) -> None:
        """Si supera la ventana de asociación se cierra el anterior y se crea
        otro nuevo (no resucita)."""
        tracker = LocalTracker(association_window_ms=2000, track_timeout_ms=100000)
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(3), seq=2))  # gap 3s > ventana 2s
        self.assertEqual(tracker.active_count("CAM-07"), 1)
        completed = tracker.completed("CAM-07")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].status, ENDED)
        tracker.close()


class TestIdIndependence(unittest.TestCase):

    def test_track_ids_independent_per_camera(self) -> None:
        tracker = LocalTracker()
        for cam in ("CAM-01", "CAM-07"):
            tracker.register_camera(cam)
        tracker.ingest(mk("CAM-01", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        track_a = tracker.active_tracks("CAM-01")[0]
        track_b = tracker.active_tracks("CAM-07")[0]
        self.assertNotEqual(track_a.track_id, track_b.track_id)
        self.assertTrue(track_a.track_id.startswith("TRK-CAM-01-"))
        self.assertTrue(track_b.track_id.startswith("TRK-CAM-07-"))
        tracker.close()

    def test_four_camera_isolation(self) -> None:
        """Prueba obligatoria: eventos intercalados en 4 cámaras mantienen
        tracks, métricas y actividades independientes."""
        tracker = LocalTracker()
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            tracker.register_camera(cam)
        interleaved = []
        for i in range(4):
            for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
                interleaved.append((cam, ts_at(i), i))
        for cam, ts, seq in interleaved:
            tracker.ingest(mk(cam, ts, seq=seq + 1))
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            tracks = tracker.active_tracks(cam)
            self.assertEqual(len(tracks), 1)
            self.assertTrue(tracks[0].camera_id == cam)
            self.assertEqual(tracks[0].event_count, 4)
            self.assertEqual(len(tracker.active_activities(cam)), 1)
        m = tracker.metrics("CAM-07")
        self.assertEqual(m["events_received"], 4)
        self.assertEqual(m["tracks_started"], 1)
        m3 = tracker.metrics("CAM-03")
        self.assertEqual(m3["tracks_started"], 1)
        tracker.close()

    def test_cross_camera_no_identity_correlation(self) -> None:
        """No existe correlación cross-camera: track de CAM-07 no se mezcla con
        CAM-03."""
        tracker = LocalTracker()
        for cam in ("CAM-03", "CAM-07"):
            tracker.register_camera(cam)
        tracker.ingest(mk("CAM-03", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-03", ts_at(1), seq=2))
        cam03 = tracker.active_tracks("CAM-03")
        cam07 = tracker.active_tracks("CAM-07")
        self.assertEqual(len(cam03), 1)
        self.assertEqual(len(cam07), 1)
        self.assertEqual(cam03[0].event_count, 2)
        self.assertEqual(cam07[0].event_count, 1)
        tracker.close()


class TestSpatialSeparation(unittest.TestCase):

    def test_two_persons_spatially_separated(self) -> None:
        """Prueba obligatoria: dos personas separadas en CAM-07 dentro de la
        misma ventana producen dos tracks cuando hay bbox suficiente."""
        tracker = LocalTracker(iou_threshold=0.1)
        tracker.register_camera("CAM-07")
        bbox_a = (10, 10, 110, 210)  # persona A (izquierda)
        bbox_b = (300, 10, 400, 210)  # persona B (derecha, sin solapamiento)
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1), bbox=bbox_a)
        tracker.ingest(mk("CAM-07", ts_at(1), seq=2), bbox=bbox_b)
        # A y B simultáneas en la misma ventana -> dos tracks activos.
        self.assertEqual(tracker.active_count("CAM-07"), 2)
        ids = {t.track_id for t in tracker.active_tracks("CAM-07")}
        self.assertEqual(len(ids), 2)
        # Un nuevo evento de A (mismo bbox) actualiza el track de A.
        tracker.ingest(mk("CAM-07", ts_at(2), seq=3), bbox=bbox_a)
        tracks = tracker.active_tracks("CAM-07")
        counts = {t.track_id: t.event_count for t in tracks}
        self.assertEqual(sorted(counts.values()), [1, 2])
        tracker.close()

    def test_bbox_update_matches_same_track(self) -> None:
        tracker = LocalTracker(iou_threshold=0.3)
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1), bbox=(10, 10, 110, 210))
        tracker.ingest(mk("CAM-07", ts_at(1), seq=2), bbox=(12, 12, 112, 212))
        self.assertEqual(tracker.active_count("CAM-07"), 1)
        self.assertEqual(tracker.active_tracks("CAM-07")[0].event_count, 2)
        tracker.close()


class TestIncompatibleEvents(unittest.TestCase):

    def test_incompatible_types_not_mixed(self) -> None:
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1, event_type="PERSON_DETECTED"))
        tracker.ingest(mk("CAM-07", ts_at(1), seq=2, event_type="OBJECT_DETECTED"))
        tracks = tracker.active_tracks("CAM-07")
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0].object_type, "person")
        self.assertEqual(tracks[1].object_type, "object")
        tracker.close()


class TestEvidence(unittest.TestCase):

    def test_evidence_first_latest_best(self) -> None:
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(
            mk("CAM-07", ts_at(0), seq=1, confidence=0.5, evidence_ref="EVID-1")
        )
        tracker.ingest(
            mk("CAM-07", ts_at(1), seq=2, confidence=0.9, evidence_ref="EVID-2")
        )
        tracker.ingest(
            mk("CAM-07", ts_at(2), seq=3, confidence=0.7, evidence_ref="EVID-3")
        )
        track = tracker.active_tracks("CAM-07")[0]
        refs = track.evidence_refs
        self.assertEqual(refs["first"], "EVID-1")
        self.assertEqual(refs["latest"], "EVID-3")
        self.assertEqual(refs["best"], "EVID-2")
        activity = tracker.active_activities("CAM-07")[0]
        self.assertEqual(activity.evidence_refs["first"], "EVID-1")
        tracker.close()

    def test_no_evidence_ref_not_fabricated(self) -> None:
        """Si no hay evidence_reference, no se inventan paths."""
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1, evidence_ref=None))
        track = tracker.active_tracks("CAM-07")[0]
        self.assertEqual(
            track.evidence_refs, {"first": None, "latest": None, "best": None}
        )
        tracker.close()


class TestBoundedRetention(unittest.TestCase):

    def test_event_refs_bounded(self) -> None:
        tracker = LocalTracker(max_event_refs=3)
        tracker.register_camera("CAM-07")
        for i in range(8):
            tracker.ingest(mk("CAM-07", ts_at(i), seq=i + 1))
        track = tracker.active_tracks("CAM-07")[0]
        self.assertLessEqual(len(track.event_refs), 3)
        tracker.close()

    def test_completed_history_bounded(self) -> None:
        tracker = LocalTracker(
            max_completed_history=2,
            track_timeout_ms=1000,
            association_window_ms=200,
        )
        tracker.register_camera("CAM-07")
        for i in range(6):
            # Cada evento con gap > ventana cierra el anterior -> 5 completados.
            tracker.ingest(mk("CAM-07", ts_at(i * 2), seq=i + 1))
        self.assertLessEqual(tracker.completed_count("CAM-07"), 2)
        tracker.close()

    def test_max_active_tracks_bounded(self) -> None:
        tracker = LocalTracker(max_active_tracks=2, association_window_ms=0)
        tracker.register_camera("CAM-07")
        # 3 objetos distintos -> se evicta el más antiguo.
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1), bbox=(0, 0, 10, 10))
        tracker.ingest(mk("CAM-07", ts_at(0), seq=2), bbox=(100, 0, 110, 10))
        tracker.ingest(mk("CAM-07", ts_at(0), seq=3), bbox=(200, 0, 210, 10))
        self.assertLessEqual(tracker.active_count("CAM-07"), 2)
        tracker.close()


class TestErrorIsolation(unittest.TestCase):

    def test_invalid_event_isolated(self) -> None:
        """Un evento inválido de CAM-03 no corrompe CAM-01/05/07."""
        tracker = LocalTracker()
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            tracker.register_camera(cam)
        tracker.ingest(mk("CAM-01", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-05", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))

        class BadEvent:
            camera_id = "CAM-03"
            timestamp = "invalid-ts"
            event_type = "PERSON_DETECTED"
            event_id = "EVT-BAD"
            confidence = 0.9
            evidence_ref = None

        result = tracker.ingest(BadEvent())
        self.assertIsNone(result)
        self.assertEqual(tracker.metrics("CAM-03")["errors"], 1)
        # Las demás cámaras siguen intactas.
        self.assertEqual(tracker.active_count("CAM-01"), 1)
        self.assertEqual(tracker.active_count("CAM-05"), 1)
        self.assertEqual(tracker.active_count("CAM-07"), 1)
        self.assertEqual(tracker.metrics("CAM-01")["errors"], 0)
        tracker.close()

    def test_unregistered_camera_raises(self) -> None:
        tracker = LocalTracker()
        with self.assertRaises(TemporalError):
            tracker.active_tracks("CAM-99")


class TestConfigFailsafe(unittest.TestCase):

    def test_invalid_config_raises(self) -> None:
        with self.assertRaises(TemporalConfigError):
            LocalTracker(association_window_ms=-1)
        with self.assertRaises(TemporalConfigError):
            LocalTracker(iou_threshold=1.5)
        with self.assertRaises(TemporalConfigError):
            LocalTracker(max_active_tracks=0)
        with self.assertRaises(TemporalConfigError):
            LocalTracker(max_evidence_refs=0)
        with self.assertRaises(TemporalConfigError):
            build_tracker({"association_window_ms": "bogus"})
        with self.assertRaises(TemporalConfigError):
            build_tracker({"iou_threshold": "high"})

    def test_build_tracker_from_config(self) -> None:
        tracker = build_tracker(
            {
                "association_window_ms": 1500,
                "track_timeout_ms": 4000,
                "iou_threshold": 0.2,
                "max_active_tracks": 4,
                "max_completed_history": 10,
                "max_event_refs": 8,
                "max_evidence_refs": 3,
            }
        )
        self.assertEqual(tracker.association_window_ms, 1500)
        self.assertEqual(tracker.track_timeout_ms, 4000)
        tracker.close()

    def test_no_config_uses_defaults(self) -> None:
        tracker = build_tracker(None)
        self.assertEqual(tracker.association_window_ms, 2000)
        self.assertEqual(tracker.track_timeout_ms, 5000)
        tracker.close()


class TestMetricsAndDeterminism(unittest.TestCase):

    def test_metrics_operational(self) -> None:
        tracker = LocalTracker(association_window_ms=2000)
        tracker.register_camera("CAM-07")
        tracker.ingest(mk("CAM-07", ts_at(0), seq=1))
        tracker.ingest(mk("CAM-07", ts_at(1), seq=2))
        totals = tracker.close()
        self.assertEqual(totals["events_received"], 2)
        self.assertEqual(totals["tracks_started"], 1)
        self.assertEqual(totals["tracks_updated"], 1)
        self.assertEqual(totals["tracks_ended"], 1)
        self.assertEqual(totals["activities_started"], 1)
        self.assertEqual(totals["activities_ended"], 1)

    def test_determinism_same_inputs_same_output(self) -> None:
        def run() -> dict:
            tracker = LocalTracker(clock=lambda: ts_at(99))
            tracker.register_camera("CAM-07")
            events = []
            for i, sec in enumerate((0, 1, 2, 8, 9)):
                ev = tracker.ingest(mk("CAM-07", ts_at(sec), seq=i + 1))
                events.append(ev.to_dict() if ev else None)
            active = [t.to_dict() for t in tracker.active_tracks("CAM-07")]
            completed = [t.to_dict() for t in tracker.completed("CAM-07")]
            return {"events": events, "active": active, "completed": completed}

        first = run()
        second = run()
        self.assertEqual(first, second)

    def test_secret_leak_redacted(self) -> None:
        tracker = LocalTracker()
        tracker.register_camera("CAM-07")
        tracker.ingest(
            mk("CAM-07", ts_at(0), seq=1,
               evidence_ref="rtsp://admin:SECRET_CANARY_8F21@192.168.1.50/cam")
        )
        track = tracker.active_tracks("CAM-07")[0]
        serialized = json.dumps(track.to_dict())
        self.assertNotIn("SECRET_CANARY_8F21", serialized)
        self.assertNotIn("admin", serialized)
        tracker.close()


if __name__ == "__main__":
    unittest.main()