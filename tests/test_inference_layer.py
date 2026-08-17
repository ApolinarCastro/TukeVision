"""Pruebas deterministas de la capa de inferencia selectiva (LOOP-0018Q).

Cubren: contrato/serialización de InferenceResult; perfiles
QUALITY/BALANCED/ECONOMY (processed/skipped); independencia por 4 cámaras;
threshold configurable; InferenceResult -> Event; event_id y timestamp;
evidence_reference; cola bounded; aislamiento de fallos del backend;
configuración inválida; secret leak; determinismo; shutdown/close.

No abren cámaras reales ni ejecutan YOLO: se usa DeterministicInferenceEngine
con generadores sintéticos y reloj inyectable.
"""

import json
import unittest
from unittest.mock import Mock

from src.inference.contract import (
    InferenceDetection,
    InferenceEngine,
    InferenceError,
    InferenceResult,
    InferenceValidationError,
)
from src.inference.engines import DeterministicInferenceEngine
from src.inference.events import (
    BoundedEventQueue,
    DROP_NEWEST,
    DROP_OLDEST,
    EventDetector,
    InferenceEvent,
    OBJECT_DETECTED,
    PERSON_DETECTED,
)
from src.inference.selective import (
    SelectiveInferenceError,
    SelectiveInferencePipeline,
    build_pipeline,
)
from src.observations.activity import (
    PROFILE_BALANCED,
    PROFILE_ECONOMY,
    PROFILE_QUALITY,
)

FIXED_TS = "2026-08-16T17:00:00.000000Z"
FIXED_CLOCK = lambda: FIXED_TS  # noqa: E731

CANARY = "rtsp://admin:SECRET_CANARY_8F21@192.168.1.50/cam"

# Detección determinista por brillo: frame 640x480 BGR con un bloque blanco.
BRIGHT_FRAME = __import__("numpy").zeros((480, 640, 3), dtype="uint8")
BRIGHT_FRAME[100:200, 300:400] = 255
BLACK_FRAME = __import__("numpy").zeros((480, 640, 3), dtype="uint8")


def det_gen_person(camera_id: str, frame_index: int):
    return [(0, "person", 0.9, 10, 20, 110, 220)]


def det_gen_empty(camera_id: str, frame_index: int):
    return []


def make_rules():
    return [
        {"type": OBJECT_DETECTED, "min_confidence": 0.35},
        {"type": PERSON_DETECTED, "min_confidence": 0.5, "class_name": "person"},
    ]


# ---------------------------------------------------------------------------
# Contrato y serialización de InferenceResult
# ---------------------------------------------------------------------------
class TestInferenceResultContract(unittest.TestCase):

    def test_minimal_result_created(self) -> None:
        result = InferenceResult(
            inference_id="INF-CAM-07-000001",
            camera_id="CAM-07",
            timestamp=FIXED_TS,
            engine_name="deterministic",
            model_name="deterministic:signal",
            producer="deterministic:selective",
            detections=(),
            latency_ms=1.0,
        )
        self.assertEqual(result.camera_id, "CAM-07")
        self.assertIsNone(result.confidence)

    def test_detection_validation(self) -> None:
        with self.assertRaises(InferenceValidationError):
            InferenceDetection(0, "person", 1.5, 0, 0, 10, 10)
        with self.assertRaises(InferenceValidationError):
            InferenceDetection(0, "person", 0.9, 50, 0, 10, 10)

    def test_required_fields(self) -> None:
        with self.assertRaises(InferenceValidationError):
            InferenceResult(
                inference_id="", camera_id="CAM-07", timestamp=FIXED_TS,
                engine_name="e", model_name="m", producer="p",
                detections=(), latency_ms=1.0,
            )
        with self.assertRaises(InferenceValidationError):
            InferenceResult(
                inference_id="INF-1", camera_id="", timestamp=FIXED_TS,
                engine_name="e", model_name="m", producer="p",
                detections=(), latency_ms=1.0,
            )

    def test_negative_latency_rejected(self) -> None:
        with self.assertRaises(InferenceValidationError):
            InferenceResult(
                inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
                engine_name="e", model_name="m", producer="p",
                detections=(), latency_ms=-1.0,
            )

    def test_result_immutable(self) -> None:
        result = InferenceResult(
            inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
            engine_name="e", model_name="m", producer="p",
            detections=(), latency_ms=1.0,
        )
        with self.assertRaises(Exception):
            result.camera_id = "CAM-01"

    def test_to_dict_roundtrip_with_detections(self) -> None:
        result = InferenceResult(
            inference_id="INF-CAM-07-000001",
            camera_id="CAM-07",
            timestamp=FIXED_TS,
            engine_name="deterministic",
            model_name="deterministic:signal",
            producer="deterministic:selective",
            detections=(
                InferenceDetection(0, "person", 0.9, 10, 20, 110, 220),
            ),
            latency_ms=3.5,
            confidence=0.9,
            observation_ref="OBS-CAM-07-000042",
            evidence_ref="EVD-1",
            metadata={"frame_index": 42, "fps": 15.0},
        )
        data = result.to_dict()
        restored = InferenceResult.from_dict(data)
        self.assertEqual(restored, result)

    def test_to_dict_json_serializable(self) -> None:
        result = InferenceResult(
            inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
            engine_name="e", model_name="m", producer="p",
            detections=(InferenceDetection(0, "person", 0.9, 0, 0, 10, 10),),
            latency_ms=1.0,
        )
        json.dumps(result.to_dict())

    def test_no_opencv_objects_in_result(self) -> None:
        with self.assertRaises(InferenceValidationError):
            InferenceResult(
                inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
                engine_name="e", model_name="m", producer="p",
                detections=(), latency_ms=1.0,
                metadata={"thing": object()},
            ).to_dict()

    def test_metadata_too_large_rejected(self) -> None:
        result = InferenceResult(
            inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
            engine_name="e", model_name="m", producer="p",
            detections=(), latency_ms=1.0,
            metadata={"blob": "x" * 5000},
        )
        with self.assertRaises(InferenceValidationError):
            result.to_dict()


# ---------------------------------------------------------------------------
# Perfiles QUALITY / BALANCED / ECONOMY (processed/skipped)
# ---------------------------------------------------------------------------
class TestPolicyProfilesSelective(unittest.TestCase):

    def _run_pipeline(self, profile: str) -> SelectiveInferencePipeline:
        policy_cfg = {
            "default_profile": profile,
            "profiles": {
                PROFILE_QUALITY: {"max_analysis_fps": 5.0},
                PROFILE_BALANCED: {"max_analysis_fps": 2.0},
                PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
            },
        }
        pipeline = SelectiveInferencePipeline(
            policy_config=policy_cfg,
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=1.0, clock=FIXED_CLOCK
            ),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        return pipeline

    def test_economy_consumes_less_than_balanced_less_than_quality(self) -> None:
        counts = {}
        for profile in (PROFILE_QUALITY, PROFILE_BALANCED, PROFILE_ECONOMY):
            pipeline = self._run_pipeline(profile)
            for i in range(60):  # 60 frames a 15 fps
                pipeline.feed("CAM-07", i, fps=15.0, frame=BRIGHT_FRAME)
            m = pipeline.metrics()["CAM-07"]
            counts[profile] = m["processed"]
            pipeline.close()
        self.assertGreater(counts[PROFILE_QUALITY], counts[PROFILE_BALANCED])
        self.assertGreater(counts[PROFILE_BALANCED], counts[PROFILE_ECONOMY])

    def test_considered_minus_skipped_equals_processed(self) -> None:
        pipeline = self._run_pipeline(PROFILE_BALANCED)
        for i in range(60):
            pipeline.feed("CAM-07", i, fps=15.0, frame=BRIGHT_FRAME)
        m = pipeline.metrics()["CAM-07"]
        self.assertEqual(
            m["considered"],
            m["processed"] + m["skipped_by_policy"],
        )
        pipeline.close()

    def test_default_profile_safe_not_continuous(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        for i in range(60):
            pipeline.feed("CAM-07", i, fps=15.0, frame=BRIGHT_FRAME)
        m = pipeline.metrics()["CAM-07"]
        self.assertEqual(m["profile"], PROFILE_BALANCED)
        self.assertLessEqual(m["processed"], 8)
        pipeline.close()

    def test_per_camera_profile_override(self) -> None:
        pipeline = SelectiveInferencePipeline(
            policy_config={
                "default_profile": PROFILE_ECONOMY,
                "profiles": {
                    PROFILE_QUALITY: {"max_analysis_fps": 5.0},
                    PROFILE_BALANCED: {"max_analysis_fps": 2.0},
                    PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
                },
            },
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-01")
        pipeline.set_camera_profile("CAM-01", PROFILE_QUALITY)
        self.assertEqual(pipeline.profile_for("CAM-01"), PROFILE_QUALITY)


# ---------------------------------------------------------------------------
# Independencia por 4 cámaras
# ---------------------------------------------------------------------------
class TestFourCameraSelectiveIsolation(unittest.TestCase):

    def _build(self):
        pipeline = SelectiveInferencePipeline(
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            clock=FIXED_CLOCK,
        )
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            pipeline.register_camera(cam)
        return pipeline

    def test_four_logical_cameras_independent_state(self) -> None:
        pipeline = self._build()
        self.assertEqual(
            pipeline.list_cameras(), ["CAM-01", "CAM-03", "CAM-05", "CAM-07"]
        )
        # CAM-03 con perfil distinto no afecta las demás.
        pipeline.set_camera_profile("CAM-03", PROFILE_QUALITY)
        for cam in pipeline.list_cameras():
            for i in range(30):
                pipeline.feed(cam, i, fps=15.0, frame=BRIGHT_FRAME)
        metrics = pipeline.metrics()
        self.assertEqual(metrics["CAM-01"]["profile"], PROFILE_BALANCED)
        self.assertEqual(metrics["CAM-03"]["profile"], PROFILE_QUALITY)
        self.assertGreater(
            metrics["CAM-03"]["processed"], metrics["CAM-01"]["processed"]
        )
        # Eventos aislados por cámara.
        for cam in pipeline.list_cameras():
            events = pipeline.consume(cam)
            self.assertTrue(all(e.camera_id == cam for e in events))
        pipeline.close()

    def test_events_not_mixed_across_cameras(self) -> None:
        pipeline = self._build()
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            pipeline.feed(cam, 0, fps=15.0, frame=BRIGHT_FRAME)
        events_01 = pipeline.consume("CAM-01")
        events_03 = pipeline.consume("CAM-03")
        self.assertTrue(all(e.camera_id == "CAM-01" for e in events_01))
        self.assertTrue(all(e.camera_id == "CAM-03" for e in events_03))
        pipeline.close()


# ---------------------------------------------------------------------------
# Backend failure isolation
# ---------------------------------------------------------------------------
class _FailingEngine(InferenceEngine):
    engine_name = "failing"
    model_name = "failing:model"
    producer = "failing:producer"

    def __init__(self, fail_camera: str) -> None:
        self._fail_camera = fail_camera
        self._closed = False

    def infer(self, frame, camera_id, observation_ref=None, evidence_ref=None, metadata=None):
        if camera_id == self._fail_camera:
            raise InferenceError(f"backend-failed-{camera_id}")
        return InferenceResult(
            inference_id=f"INF-{camera_id}-000001",
            camera_id=camera_id,
            timestamp=FIXED_TS,
            engine_name="failing",
            model_name="failing:model",
            producer="failing:producer",
            detections=(InferenceDetection(0, "person", 0.9, 0, 0, 10, 10),),
            latency_ms=1.0,
        )

    def close(self) -> None:
        self._closed = True


class TestBackendFailureIsolation(unittest.TestCase):

    def test_failure_isolated_to_one_camera(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=_FailingEngine(fail_camera="CAM-03"),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            clock=FIXED_CLOCK,
        )
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            pipeline.register_camera(cam)

        # CAM-03 falla en el backend; las demás deben seguir intactas.
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            for i in range(30):
                pipeline.feed(cam, i, fps=15.0, frame=BRIGHT_FRAME)

        metrics = pipeline.metrics()
        self.assertGreater(metrics["CAM-03"]["inference_errors"], 0)
        self.assertEqual(metrics["CAM-03"]["processed"], 4)
        self.assertEqual(metrics["CAM-03"]["events_generated"], 0)
        for cam in ("CAM-01", "CAM-05", "CAM-07"):
            self.assertEqual(metrics[cam]["inference_errors"], 0)
            self.assertEqual(metrics[cam]["events_generated"], 4)
        pipeline.close()

    def test_no_infinite_retry(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=_FailingEngine(fail_camera="CAM-03"),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-03")
        for i in range(30):
            pipeline.feed("CAM-03", i, fps=15.0)
        m = pipeline.metrics()["CAM-03"]
        self.assertEqual(m["inference_errors"], m["processed"])
        self.assertEqual(m["inference_errors"], 4)
        pipeline.close()


# ---------------------------------------------------------------------------
# Event detection: InferenceResult -> Event, thresholds, traceability
# ---------------------------------------------------------------------------
class TestEventDetection(unittest.TestCase):

    def _result(self, detections, camera_id="CAM-07") -> InferenceResult:
        return InferenceResult(
            inference_id="INF-X-000001",
            camera_id=camera_id,
            timestamp=FIXED_TS,
            engine_name="deterministic",
            model_name="deterministic:signal",
            producer="deterministic:selective",
            detections=tuple(detections),
            latency_ms=1.0,
        )

    def test_object_detected_event(self) -> None:
        detector = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.35}],
            clock=FIXED_CLOCK,
        )
        result = self._result([InferenceDetection(0, "person", 0.9, 0, 0, 10, 10)])
        event = detector.detect(result)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, OBJECT_DETECTED)
        self.assertEqual(event.camera_id, "CAM-07")
        self.assertEqual(event.timestamp, FIXED_TS)
        self.assertEqual(event.inference_ref, "INF-X-000001")

    def test_event_propagates_bounded_real_detection_boxes(self) -> None:
        detector = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.35}],
            clock=FIXED_CLOCK,
        )
        detections = [
            InferenceDetection(0, "person", 0.9, i, i + 1, i + 10, i + 20)
            for i in range(20)
        ]
        event = detector.detect(self._result(detections))
        self.assertEqual(event.metadata["detections"], 20)
        self.assertEqual(len(event.metadata["bboxes"]), 16)
        self.assertEqual(event.metadata["bboxes"][0][:4], [0, 1, 10, 20])

    def test_below_threshold_no_event(self) -> None:
        detector = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.5}],
            clock=FIXED_CLOCK,
        )
        result = self._result([InferenceDetection(0, "person", 0.4, 0, 0, 10, 10)])
        self.assertIsNone(detector.detect(result))

    def test_person_detected_class_filter(self) -> None:
        detector = EventDetector(
            rules=[
                {"type": OBJECT_DETECTED, "min_confidence": 0.35},
                {"type": PERSON_DETECTED, "min_confidence": 0.5, "class_name": "person"},
            ],
            clock=FIXED_CLOCK,
        )
        person = self._result([InferenceDetection(0, "person", 0.9, 0, 0, 10, 10)])
        self.assertEqual(detector.detect(person).event_type, PERSON_DETECTED)

        car = self._result([InferenceDetection(2, "car", 0.9, 0, 0, 10, 10)])
        self.assertEqual(detector.detect(car).event_type, OBJECT_DETECTED)

    def test_threshold_config_driven(self) -> None:
        # Umbral configurable: 0.5 -> el evento de 0.4 no se genera.
        strict = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.5}],
            clock=FIXED_CLOCK,
        )
        lax = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.1}],
            clock=FIXED_CLOCK,
        )
        result = self._result([InferenceDetection(0, "person", 0.4, 0, 0, 10, 10)])
        self.assertIsNone(strict.detect(result))
        self.assertIsNotNone(lax.detect(result))

    def test_event_serialization_roundtrip(self) -> None:
        detector = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.35}],
            clock=FIXED_CLOCK,
        )
        result = self._result(
            [InferenceDetection(0, "person", 0.9, 0, 0, 10, 10)],
            camera_id="CAM-01",
        )
        event = detector.detect(result)
        data = event.to_dict()
        json.dumps(data)
        restored = InferenceEvent.from_dict(data)
        self.assertEqual(restored, event)

    def test_event_requires_inference_ref(self) -> None:
        with self.assertRaises(Exception):
            InferenceEvent(
                event_id="EVT-1",
                camera_id="CAM-07",
                timestamp=FIXED_TS,
                event_type=OBJECT_DETECTED,
                confidence=0.9,
                producer="p",
                model="m",
                observation_ref=None,
                inference_ref="",
            )

    def test_evidence_reference_propagates(self) -> None:
        detector = EventDetector(
            rules=[{"type": OBJECT_DETECTED, "min_confidence": 0.35}],
            clock=FIXED_CLOCK,
        )
        result = self._result([InferenceDetection(0, "person", 0.9, 0, 0, 10, 10)])
        event = detector.detect(result)
        self.assertIsNone(event.evidence_ref)

    def test_no_rules_means_no_event(self) -> None:
        detector = EventDetector(rules=[], clock=FIXED_CLOCK)
        result = self._result([InferenceDetection(0, "person", 0.9, 0, 0, 10, 10)])
        self.assertIsNone(detector.detect(result))


# ---------------------------------------------------------------------------
# Cola bounded de eventos
# ---------------------------------------------------------------------------
class TestBoundedEventQueue(unittest.TestCase):

    def _event(self, seq: int) -> InferenceEvent:
        return InferenceEvent(
            event_id=f"EVT-{seq}",
            camera_id="CAM-07",
            timestamp=FIXED_TS,
            event_type=OBJECT_DETECTED,
            confidence=0.9,
            producer="p",
            model="m",
            observation_ref=None,
            inference_ref=f"INF-{seq}",
        )

    def test_drop_oldest(self) -> None:
        q = BoundedEventQueue(maxlen=3, overflow=DROP_OLDEST)
        for i in range(5):
            q.push(self._event(i))
        self.assertEqual(len(q), 3)
        remaining = q.drain()
        self.assertEqual([e.event_id for e in remaining], ["EVT-2", "EVT-3", "EVT-4"])
        self.assertEqual(q.dropped, 2)

    def test_drop_newest(self) -> None:
        q = BoundedEventQueue(maxlen=3, overflow=DROP_NEWEST)
        for i in range(5):
            q.push(self._event(i))
        self.assertEqual(len(q), 3)
        remaining = q.drain()
        self.assertEqual([e.event_id for e in remaining], ["EVT-0", "EVT-1", "EVT-2"])
        self.assertEqual(q.dropped, 2)

    def test_invalid_maxlen(self) -> None:
        with self.assertRaises(Exception):
            BoundedEventQueue(maxlen=0)

    def test_invalid_overflow(self) -> None:
        with self.assertRaises(Exception):
            BoundedEventQueue(overflow="bogus")

    def test_pipeline_event_queue_bounded(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            event_queue_maxlen=4,
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        for i in range(30):  # BALANCED -> frames 0,8,16,24 = 4 eventos
            pipeline.feed("CAM-07", i, fps=15.0, frame=BRIGHT_FRAME)
        self.assertLessEqual(pipeline.queued("CAM-07"), 4)
        pipeline.close()


# ---------------------------------------------------------------------------
# Configuración inválida / fail-safe / determinismo / secretos / shutdown
# ---------------------------------------------------------------------------
class TestConfigFailsafeAndDeterminism(unittest.TestCase):

    def test_build_pipeline_from_config(self) -> None:
        # Config-driven: reglas y cola se leen del bloque `inference`.
        pipeline = build_pipeline(
            {
                "backend": "deterministic",
                "confidence_threshold": 0.5,
                "event_queue_maxlen": 8,
                "event_queue_overflow": "drop_oldest",
                "events": [
                    {"type": OBJECT_DETECTED, "min_confidence": 0.5},
                    {
                        "type": PERSON_DETECTED,
                        "min_confidence": 0.5,
                        "class_name": "person",
                    },
                ],
            }
        )
        pipeline.register_camera("CAM-07")
        # Umbral 0.5 config-driven: la detección 0.9 genera evento.
        event = pipeline.feed("CAM-07", 0, fps=15.0, frame=BRIGHT_FRAME)
        self.assertIsNotNone(event)
        # El backend determinista por brillo emite clase genérica "object":
        # la regla OBJECT_DETECTED (0.5) aplica y se respeta el threshold.
        self.assertEqual(event.event_type, OBJECT_DETECTED)
        self.assertGreaterEqual(event.confidence, 0.5)
        totals = pipeline.close()
        self.assertEqual(totals["events_generated"], 1)

    def test_build_pipeline_invalid_backend_raises(self) -> None:
        from src.inference.contract import InferenceConfigError

        with self.assertRaises(InferenceConfigError):
            build_pipeline({"backend": "bogus"})

    def test_build_pipeline_events_not_list_raises(self) -> None:
        with self.assertRaises(SelectiveInferenceError):
            build_pipeline({"backend": "deterministic", "events": {"type": OBJECT_DETECTED}})

    def test_build_pipeline_no_valid_rules_raises(self) -> None:
        with self.assertRaises(SelectiveInferenceError):
            build_pipeline(
                {
                    "backend": "deterministic",
                    "events": [{"type": "BOGUS", "min_confidence": 0.5}],
                }
            )

    def test_build_pipeline_invalid_queue_raises(self) -> None:
        with self.assertRaises(SelectiveInferenceError):
            build_pipeline(
                {
                    "backend": "deterministic",
                    "event_queue_maxlen": 0,
                    "events": [{"type": OBJECT_DETECTED, "min_confidence": 0.5}],
                }
            )
        with self.assertRaises(SelectiveInferenceError):
            build_pipeline(
                {
                    "backend": "deterministic",
                    "event_queue_overflow": "bogus",
                    "events": [{"type": OBJECT_DETECTED, "min_confidence": 0.5}],
                }
            )

    def test_invalid_default_profile_falls_back(self) -> None:
        pipeline = SelectiveInferencePipeline(
            policy_config={"default_profile": "ULTRA"},
            engine=DeterministicInferenceEngine(
                generator=det_gen_empty, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        self.assertEqual(pipeline.profile_for("CAM-07"), PROFILE_BALANCED)
        pipeline.close()

    def test_invalid_rule_ignored(self) -> None:
        detector = EventDetector(
            rules=[
                {"type": OBJECT_DETECTED, "min_confidence": 0.35},
                {"type": "BOGUS", "min_confidence": 0.5},
                {"min_confidence": 0.5},
            ],
            clock=FIXED_CLOCK,
        )
        self.assertEqual(len(detector.rules), 1)

    def test_determinism_same_inputs_same_output(self) -> None:
        def run() -> dict:
            pipeline = SelectiveInferencePipeline(
                engine=DeterministicInferenceEngine(
                    generator=det_gen_person, simulated_latency_ms=1.0, clock=FIXED_CLOCK
                ),
                event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
                clock=FIXED_CLOCK,
            )
            pipeline.register_camera("CAM-07")
            events = []
            for i in range(30):
                e = pipeline.feed("CAM-07", i, fps=15.0, frame=BRIGHT_FRAME)
                if e is not None:
                    events.append(e.to_dict())
            totals = pipeline.totals()
            pipeline.close()
            return {"events": events, "totals": totals}

        first = run()
        second = run()
        self.assertEqual(first, second)

    def test_secret_in_metadata_redacted(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=0.0, clock=FIXED_CLOCK
            ),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        event = pipeline.feed(
            "CAM-07", 0, fps=15.0, frame=BRIGHT_FRAME,
            metadata={"source_url": CANARY},
        )
        self.assertIsNotNone(event)
        serialized = json.dumps(event.to_dict())
        self.assertNotIn("SECRET_CANARY_8F21", serialized)
        self.assertNotIn("admin", serialized)
        self.assertIn("REDACTED:REDACTED", serialized)
        pipeline.close()

    def test_secret_in_observation_ref_not_exposed(self) -> None:
        result = InferenceResult(
            inference_id="INF-1", camera_id="CAM-07", timestamp=FIXED_TS,
            engine_name="e", model_name="m", producer="p",
            detections=(), latency_ms=1.0,
            observation_ref=CANARY,
        )
        serialized = json.dumps(result.to_dict())
        self.assertNotIn("SECRET_CANARY_8F21", serialized)
        self.assertNotIn("admin", serialized)
        self.assertIn("REDACTED:REDACTED", serialized)

    def test_shutdown_closes_engine(self) -> None:
        engine = DeterministicInferenceEngine(
            generator=det_gen_empty, simulated_latency_ms=0.0, clock=FIXED_CLOCK
        )
        pipeline = SelectiveInferencePipeline(
            engine=engine, clock=FIXED_CLOCK,
        )
        pipeline.register_camera("CAM-07")
        pipeline.feed("CAM-07", 0, fps=15.0)
        totals = pipeline.close()
        self.assertIn("considered", totals)
        with self.assertRaises(SelectiveInferenceError):
            pipeline.feed("CAM-07", 1, fps=15.0)
        with self.assertRaises(InferenceError):
            engine.infer(BLACK_FRAME, "CAM-07")

    def test_metrics_per_camera_and_totals(self) -> None:
        pipeline = SelectiveInferencePipeline(
            engine=DeterministicInferenceEngine(
                generator=det_gen_person, simulated_latency_ms=1.0, clock=FIXED_CLOCK
            ),
            event_detector=EventDetector(rules=make_rules(), clock=FIXED_CLOCK),
            clock=FIXED_CLOCK,
        )
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            pipeline.register_camera(cam)
            for i in range(60):
                pipeline.feed(cam, i, fps=15.0, frame=BRIGHT_FRAME)
        metrics = pipeline.metrics()
        totals = pipeline.totals()
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            m = metrics[cam]
            self.assertEqual(
                m["considered"], m["processed"] + m["skipped_by_policy"]
            )
        total_considered = sum(metrics[c]["considered"] for c in metrics)
        self.assertEqual(total_considered, totals["considered"])
        total_processed = sum(metrics[c]["processed"] for c in metrics)
        self.assertEqual(total_processed, totals["processed"])
        pipeline.close()


if __name__ == "__main__":
    unittest.main()
