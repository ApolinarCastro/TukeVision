"""Pruebas deterministas de la Activity/Observation Layer (LOOP-0018P).

Cubren: schema/serialización de ActivityObservation; timestamps UTC; ausencia
de secretos; aislamiento de 4 cámaras; cola bounded + política de overflow;
orden/identidad; perfiles QUALITY/BALANCED/ECONOMY; configuración inválida
fail-safe; productor defectuoso aislado; shutdown; determinismo.

No abre cámaras reales: todo el comportamiento se certifica con productores
sintéticos y un reloj inyectable (determinismo).
"""

import json
import unittest

from src.observations.activity import (
    ACTIVE,
    ActivityError,
    ActivityLayer,
    ActivityObservation,
    BoundedObservationQueue,
    DROP_NEWEST,
    DROP_OLDEST,
    FRAME_SAMPLE,
    InvalidObservationError,
    ObservationPolicy,
    PROFILE_BALANCED,
    PROFILE_ECONOMY,
    PROFILE_QUALITY,
    SIGNAL,
)

# Reloj fijo para determinismo (timestamp UTC canónico del sistema).
FIXED_TS = "2026-08-16T17:00:00.000000Z"
FIXED_CLOCK = lambda: FIXED_TS  # noqa: E731


def make_payload(frame_index: int, camera_id: str) -> dict:
    return {"frame_index": frame_index, "source": camera_id, "confidence": 1.0}


# ---------------------------------------------------------------------------
# Schema y serialización
# ---------------------------------------------------------------------------
class TestObservationSchema(unittest.TestCase):

    def test_minimal_observation_created(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-CAM-07-000001",
            camera_id="CAM-07",
            timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE,
            state=ACTIVE,
            payload={"frame_index": 1},
        )
        self.assertEqual(obs.camera_id, "CAM-07")
        self.assertEqual(obs.observation_type, FRAME_SAMPLE)
        self.assertEqual(obs.state, ACTIVE)
        self.assertIsNone(obs.confidence)
        self.assertEqual(obs.origin, "activity")

    def test_requires_camera_id(self) -> None:
        with self.assertRaises(InvalidObservationError):
            ActivityObservation(
                observation_id="OBS-1", camera_id="", timestamp=FIXED_TS,
                observation_type=FRAME_SAMPLE, state=ACTIVE, payload={},
            )

    def test_rejects_invalid_type(self) -> None:
        with self.assertRaises(InvalidObservationError):
            ActivityObservation(
                observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
                observation_type="NOT_A_TYPE", state=ACTIVE, payload={},
            )

    def test_rejects_invalid_state(self) -> None:
        with self.assertRaises(InvalidObservationError):
            ActivityObservation(
                observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
                observation_type=FRAME_SAMPLE, state="BOGUS", payload={},
            )

    def test_rejects_confidence_out_of_range(self) -> None:
        with self.assertRaises(InvalidObservationError):
            ActivityObservation(
                observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
                observation_type=FRAME_SAMPLE, state=ACTIVE, payload={},
                confidence=1.5,
            )

    def test_rejects_non_dict_payload(self) -> None:
        with self.assertRaises(InvalidObservationError):
            ActivityObservation(
                observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
                observation_type=FRAME_SAMPLE, state=ACTIVE, payload=[1, 2, 3],
            )

    def test_observation_is_immutable(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE, payload={},
        )
        with self.assertRaises(Exception):
            obs.camera_id = "CAM-01"

    def test_to_dict_roundtrip(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-CAM-07-000042",
            camera_id="CAM-07",
            timestamp=FIXED_TS,
            observation_type=SIGNAL,
            state=ACTIVE,
            payload={"frame_index": 42, "fps": 15.0},
            confidence=0.99,
            origin="activity:test",
            evidence_ref="EVD-1",
        )
        data = obs.to_dict()
        self.assertIsInstance(data, dict)
        self.assertNotIn("password", json.dumps(data).lower())
        restored = ActivityObservation.from_dict(data)
        self.assertEqual(restored, obs)

    def test_to_dict_is_json_serializable(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE,
            payload={"frame_index": 1},
        )
        json.dumps(obs.to_dict())  # no debe lanzar

    def test_payload_too_large_rejected(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE,
            payload={"blob": "x" * 5000},
        )
        with self.assertRaises(InvalidObservationError):
            obs.to_dict()

    def test_no_opencv_objects_in_payload(self) -> None:
        # Si alguien mete un objeto no serializable, to_dict debe fallar.
        class NotSerializable:
            pass

        obs = ActivityObservation(
            observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE,
            payload={"thing": NotSerializable()},
        )
        with self.assertRaises(InvalidObservationError):
            obs.to_dict()


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------
class TestTimestamps(unittest.TestCase):

    def test_default_clock_utc(self) -> None:
        layer = ActivityLayer()
        layer.register_camera("CAM-07", fps=15.0)
        obs = layer.feed("CAM-07", 0)
        self.assertIsNotNone(obs)
        # ISO-8601 con sufijo Z (UTC canónico).
        self.assertRegex(obs.timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertTrue(obs.timestamp.endswith("Z"))

    def test_injected_clock_deterministic(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        obs = layer.feed("CAM-07", 0)
        self.assertEqual(obs.timestamp, FIXED_TS)


# ---------------------------------------------------------------------------
# Ausencia de secretos
# ---------------------------------------------------------------------------
class TestSecretLeak(unittest.TestCase):

    CANARY = "rtsp://admin:SECRET_CANARY_8F21@192.168.1.50/cam"

    def test_payload_url_redacted_on_serialization(self) -> None:
        obs = ActivityObservation(
            observation_id="OBS-1", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE,
            payload={"source_path": self.CANARY},
        )
        data = obs.to_dict()
        serialized = json.dumps(data)
        self.assertNotIn("SECRET_CANARY_8F21", serialized)
        self.assertNotIn("admin", serialized)
        self.assertIn("REDACTED:REDACTED", serialized)

    def test_metadata_with_secret_url_redacted(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        obs = layer.feed(
            "CAM-07", 0,
            metadata={"source_type": self.CANARY},
        )
        self.assertIsNotNone(obs)
        serialized = json.dumps(obs.to_dict())
        self.assertNotIn("SECRET_CANARY_8F21", serialized)
        self.assertNotIn("admin", serialized)
        self.assertIn("REDACTED:REDACTED", serialized)


# ---------------------------------------------------------------------------
# Cola bounded y política de overflow
# ---------------------------------------------------------------------------
class TestBoundedQueue(unittest.TestCase):

    def _obs(self, seq: int) -> ActivityObservation:
        return ActivityObservation(
            observation_id=f"OBS-{seq}", camera_id="CAM-07", timestamp=FIXED_TS,
            observation_type=FRAME_SAMPLE, state=ACTIVE, payload={"i": seq},
        )

    def test_drop_oldest_keeps_newest(self) -> None:
        q = BoundedObservationQueue("CAM-07", maxlen=3, overflow=DROP_OLDEST)
        for i in range(5):
            q.push(self._obs(i))
        self.assertEqual(len(q), 3)
        remaining = q.drain()
        self.assertEqual([o.payload["i"] for o in remaining], [2, 3, 4])
        self.assertEqual(q.dropped, 2)

    def test_drop_newest_keeps_oldest(self) -> None:
        q = BoundedObservationQueue("CAM-07", maxlen=3, overflow=DROP_NEWEST)
        for i in range(5):
            q.push(self._obs(i))
        self.assertEqual(len(q), 3)
        remaining = q.drain()
        self.assertEqual([o.payload["i"] for o in remaining], [0, 1, 2])
        self.assertEqual(q.dropped, 2)

    def test_fifo_order(self) -> None:
        q = BoundedObservationQueue("CAM-07", maxlen=8)
        for i in range(4):
            q.push(self._obs(i))
        self.assertEqual([o.payload["i"] for o in q.drain()], [0, 1, 2, 3])

    def test_peek_does_not_consume(self) -> None:
        q = BoundedObservationQueue("CAM-07", maxlen=8)
        q.push(self._obs(7))
        self.assertEqual(q.peek().payload["i"], 7)
        self.assertEqual(len(q), 1)

    def test_invalid_maxlen(self) -> None:
        with self.assertRaises(ActivityError):
            BoundedObservationQueue("CAM-07", maxlen=0)

    def test_invalid_overflow(self) -> None:
        with self.assertRaises(ActivityError):
            BoundedObservationQueue("CAM-07", overflow="bogus")

    def test_layer_queue_bounded_by_default(self) -> None:
        layer = ActivityLayer(queue_maxlen=4, clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        for i in range(10):
            layer.feed("CAM-07", i)
        # 15fps con perfil BALANCED (2fps) => interval=8: frames 0 y 8 analizados.
        self.assertEqual(layer.queued("CAM-07"), 2)
        self.assertLessEqual(layer.queued("CAM-07"), 4)


# ---------------------------------------------------------------------------
# Aislamiento de 4 cámaras y productor defectuoso
# ---------------------------------------------------------------------------
def _defective_producer(camera_id, frame_index, metadata=None):
    if camera_id == "CAM-03":
        raise RuntimeError(f"producer-failure-{camera_id}")
    return make_payload(frame_index, camera_id)


class TestFourCameraIsolation(unittest.TestCase):

    def test_four_logical_sources_independent(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            layer.register_camera(cam, fps=15.0)
        self.assertEqual(layer.list_cameras(), ["CAM-01", "CAM-03", "CAM-05", "CAM-07"])

        # Cada cámara genera observaciones con identidad inequívoca.
        for cam in layer.list_cameras():
            obs = layer.feed(cam, 0)
            self.assertIsNotNone(obs)
            self.assertEqual(obs.camera_id, cam)
            self.assertIn(f"OBS-{cam}-", obs.observation_id)

        for cam in layer.list_cameras():
            consumed = layer.consume(cam)
            self.assertEqual(len(consumed), 1)
            self.assertEqual(consumed[0].camera_id, cam)

    def test_defective_producer_isolated(self) -> None:
        layer = ActivityLayer(
            producer=_defective_producer,
            clock=FIXED_CLOCK,
        )
        for cam in ("CAM-01", "CAM-03", "CAM-05", "CAM-07"):
            layer.register_camera(cam, fps=15.0)

        # CAM-03 falla en el productor; las demás deben seguir intactas.
        obs_03 = layer.feed("CAM-03", 0)
        self.assertIsNone(obs_03)
        self.assertEqual(layer.camera_state("CAM-03"), "ERROR")
        self.assertEqual(layer.stats()["CAM-03"]["counters"]["producer_errors"], 1)

        for cam in ("CAM-01", "CAM-05", "CAM-07"):
            obs = layer.feed(cam, 0)
            self.assertIsNotNone(obs)
            self.assertEqual(layer.queued(cam), 1)
            self.assertEqual(layer.camera_state(cam), "ACTIVE")


# ---------------------------------------------------------------------------
# Perfiles QUALITY/BALANCED/ECONOMY
# ---------------------------------------------------------------------------
class TestPolicyProfiles(unittest.TestCase):

    def test_profiles_have_distinct_intervals(self) -> None:
        # A 15 fps: QUALITY(5fps)->3, BALANCED(2fps)->8, ECONOMY(1fps)->15
        for profile, expected in (
            (PROFILE_QUALITY, 3),
            (PROFILE_BALANCED, 8),
            (PROFILE_ECONOMY, 15),
        ):
            cfg_policy = ObservationPolicy({
                "default_profile": profile,
                "profiles": {
                    PROFILE_QUALITY: {"max_analysis_fps": 5.0},
                    PROFILE_BALANCED: {"max_analysis_fps": 2.0},
                    PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
                },
            })
            self.assertEqual(
                cfg_policy.sampling_interval_frames("CAM-07", 15.0),
                expected,
                msg=f"perfil {profile}",
            )

    def test_quality_analyzes_more_frames_than_economy(self) -> None:
        policy = ObservationPolicy({
            "default_profile": PROFILE_QUALITY,
            "profiles": {
                PROFILE_QUALITY: {"max_analysis_fps": 5.0},
                PROFILE_BALANCED: {"max_analysis_fps": 2.0},
                PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
            },
        })
        frames = [i for i in range(30)]
        analyzed_q = sum(1 for f in frames if policy.should_analyze("CAM-07", f, 15.0))

        policy_e = ObservationPolicy({
            "default_profile": PROFILE_ECONOMY,
            "profiles": {
                PROFILE_QUALITY: {"max_analysis_fps": 5.0},
                PROFILE_BALANCED: {"max_analysis_fps": 2.0},
                PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
            },
        })
        analyzed_e = sum(1 for f in frames if policy_e.should_analyze("CAM-07", f, 15.0))
        self.assertGreater(analyzed_q, analyzed_e)

    def test_default_profile_is_safe_not_continuous(self) -> None:
        policy = ObservationPolicy()  # sin config => BALANCED (2fps)
        self.assertEqual(policy.default_profile, PROFILE_BALANCED)
        analyzed = sum(1 for f in range(60) if policy.should_analyze("CAM-07", f, 15.0))
        # 60 frames a 15fps = 4s; 2fps => <= 8 análisis. NO 60 (15fps x 4).
        self.assertLessEqual(analyzed, 8)

    def test_per_camera_profile_override(self) -> None:
        policy = ObservationPolicy({
            "default_profile": PROFILE_ECONOMY,
            "cameras": {"CAM-01": PROFILE_QUALITY},
        })
        self.assertEqual(policy.profile_for("CAM-01"), PROFILE_QUALITY)
        self.assertEqual(policy.profile_for("CAM-07"), PROFILE_ECONOMY)

    def test_policy_describe_auditable(self) -> None:
        policy = ObservationPolicy()
        info = policy.describe("CAM-07", 15.0)
        self.assertEqual(info["profile"], PROFILE_BALANCED)
        self.assertEqual(info["sampling_interval_frames"], 8)
        self.assertEqual(info["max_analysis_fps"], 2.0)


# ---------------------------------------------------------------------------
# Configuración inválida fail-safe
# ---------------------------------------------------------------------------
class TestInvalidConfigFailsafe(unittest.TestCase):

    def test_invalid_default_profile_falls_back(self) -> None:
        policy = ObservationPolicy({"default_profile": "ULTRA"})
        self.assertEqual(policy.default_profile, PROFILE_BALANCED)

    def test_invalid_max_analysis_fps_clamped(self) -> None:
        policy = ObservationPolicy({
            "default_profile": PROFILE_QUALITY,
            "profiles": {PROFILE_QUALITY: {"max_analysis_fps": "abc"}},
        })
        # Cae al default seguro de QUALITY.
        self.assertEqual(policy.max_analysis_fps("CAM-07"), 5.0)

    def test_none_config_is_safe(self) -> None:
        policy = ObservationPolicy(None)
        self.assertEqual(policy.default_profile, PROFILE_BALANCED)
        self.assertEqual(policy.max_analysis_fps("CAM-07"), 2.0)

    def test_garbage_config_is_safe(self) -> None:
        policy = ObservationPolicy({"profiles": "garbage", "default_profile": []})
        self.assertEqual(policy.default_profile, PROFILE_BALANCED)
        self.assertEqual(policy.max_analysis_fps("CAM-07"), 2.0)

    def test_layer_with_broken_config_is_safe(self) -> None:
        layer = ActivityLayer(config={"observation": {"default_profile": "NOPE"}})
        layer.register_camera("CAM-07", fps=15.0)
        obs = layer.feed("CAM-07", 0)
        self.assertIsNotNone(obs)
        self.assertEqual(layer.stats()["CAM-07"]["profile"], PROFILE_BALANCED)


# ---------------------------------------------------------------------------
# Shutdown y determinismo
# ---------------------------------------------------------------------------
class TestShutdownAndDeterminism(unittest.TestCase):

    def test_shutdown_returns_stats_and_clears_queues(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        layer.feed("CAM-07", 0)
        self.assertEqual(layer.queued("CAM-07"), 1)
        stats = layer.close()
        self.assertIn("CAM-07", stats)
        self.assertEqual(layer.queued("CAM-07"), 0)

    def test_operations_after_close_rejected(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        layer.close()
        with self.assertRaises(ActivityError):
            layer.register_camera("CAM-01", fps=15.0)
        with self.assertRaises(ActivityError):
            layer.feed("CAM-07", 5)

    def test_determinism_same_inputs_same_output(self) -> None:
        def run() -> list:
            layer = ActivityLayer(clock=FIXED_CLOCK)
            layer.register_camera("CAM-07", fps=15.0)
            results = []
            for i in range(30):
                obs = layer.feed("CAM-07", i)
                if obs is not None:
                    results.append(obs.to_dict())
            return results

        first = run()
        second = run()
        self.assertEqual(first, second)

    def test_observation_ids_unique_and_ordered(self) -> None:
        layer = ActivityLayer(clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        ids = []
        for i in range(60):
            obs = layer.feed("CAM-07", i)
            if obs is not None:
                ids.append(obs.observation_id)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(ids == sorted(ids))

    def test_consume_limit(self) -> None:
        layer = ActivityLayer(queue_maxlen=16, clock=FIXED_CLOCK)
        layer.register_camera("CAM-07", fps=15.0)
        for i in range(30):
            layer.feed("CAM-07", i)
        # 15fps BALANCED(2fps) => interval=8: frames 0,8,16,24 -> 4 observaciones.
        self.assertEqual(layer.queued("CAM-07"), 4)
        drained = layer.consume("CAM-07", limit=1)
        self.assertEqual(len(drained), 1)
        self.assertEqual(layer.queued("CAM-07"), 3)


if __name__ == "__main__":
    unittest.main()