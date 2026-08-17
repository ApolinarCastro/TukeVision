"""Pruebas deterministas del wiring de la cadena 2.2 (LOOP-0018T, C1).

Cubre el adapter AdvanceChain: composición SourceManager->ActivityLayer->
SelectiveInference->LocalTracker usando EXCLUSIVAMENTE los contratos
existentes. Verifica:

- build() config-driven con backend determinista (sin YOLO/cámaras reales).
- register_from_source_manager registra cámaras en las 3 capas (gap H1).
- feed() recorre toda la cadena: observación -> evento -> track.
- aislamiento por cámara (fallo de una no bloquea las demás).
- resumen auditable sin secretos ni frames.
- configuración inválida fail-safe explícito.
- shutdown limpio (close en orden inverso) e idempotente.
"""

import json
import unittest

import numpy as np

from src.app.advance_chain import AdvanceChain, AdvanceChainError
from src.inference.events import OBJECT_DETECTED
from src.observations.activity import FRAME_SAMPLE, PROFILE_BALANCED

# Reloj fijo para determinismo (timestamp UTC canónico del sistema).
FIXED_TS = "2026-08-16T17:00:00.000000Z"

# Frame 640x480 BGR con un bloque blanco -> detección determinista.
BRIGHT_FRAME = np.zeros((480, 640, 3), dtype="uint8")
BRIGHT_FRAME[100:200, 300:400] = 255
BLACK_FRAME = np.zeros((480, 640, 3), dtype="uint8")


class BrokenFrame:
    """Frame cuyo array-ificado lanza RuntimeError (fallo del backend aislado)."""

    def __array__(self, dtype=None):
        raise RuntimeError("backend boom")


class FakeSourceManager:
    """Duck-typed SourceManager: expone list_sources()/health() sin abrir nada."""

    def __init__(self, camera_ids):
        self._camera_ids = list(camera_ids)

    def list_sources(self):
        return [
            {"camera_id": cid, "host": "rtsp://cam.local", "channel": 1,
             "subtype": 1, "running": False}
            for cid in self._camera_ids
        ]

    def health(self, camera_id):
        class _H:
            fps = 15.0
        return _H()


def make_config(backend="deterministic", **overrides):
    cfg = {
        "observation": {
            "default_profile": PROFILE_BALANCED,
            "profiles": {
                "QUALITY": {"max_analysis_fps": 5.0},
                "BALANCED": {"max_analysis_fps": 2.0},
                "ECONOMY": {"max_analysis_fps": 1.0},
            },
        },
        "inference": {
            "backend": backend,
            "confidence_threshold": 0.5,
            "simulated_latency_ms": 0.0,
            "event_queue_maxlen": 16,
            "event_queue_overflow": "drop_oldest",
            "events": [
                {"type": "OBJECT_DETECTED", "min_confidence": 0.5},
                {"type": "PERSON_DETECTED", "min_confidence": 0.5, "class_name": "person"},
            ],
        },
        "temporal": {
            "association_window_ms": 2000,
            "track_timeout_ms": 5000,
            "iou_threshold": 0.05,
            "max_active_tracks": 8,
            "max_completed_history": 32,
            "max_event_refs": 16,
            "max_evidence_refs": 3,
        },
    }
    if overrides:
        cfg = json.loads(json.dumps(cfg))
        cfg.update(overrides)
    return cfg


class TestAdvanceChainBuild(unittest.TestCase):

    def test_build_config_driven(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        self.assertIsInstance(chain, AdvanceChain)
        chain.close()

    def test_build_invalid_config_raises(self):
        with self.assertRaises(AdvanceChainError):
            AdvanceChain.build("not-a-dict", FakeSourceManager(["CAM-01"]))

    def test_build_missing_inference_block_raises(self):
        with self.assertRaises(AdvanceChainError):
            AdvanceChain.build({"observation": {}}, FakeSourceManager(["CAM-01"]))

    def test_feed_after_close_raises(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()
        chain.close()
        with self.assertRaises(AdvanceChainError):
            chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)


class TestAdvanceChainRegistration(unittest.TestCase):

    def test_registers_cameras_in_all_layers(self):
        sm = FakeSourceManager(["CAM-01", "CAM-02"])
        chain = AdvanceChain.build(make_config(), sm)
        registered = chain.register_from_source_manager()
        self.assertEqual(sorted(registered), ["CAM-01", "CAM-02"])
        self.assertEqual(chain.list_cameras(), ["CAM-01", "CAM-02"])
        self.assertEqual(chain._activity.list_cameras(), ["CAM-01", "CAM-02"])
        self.assertEqual(chain._selective.list_cameras(), ["CAM-01", "CAM-02"])
        for cid in ("CAM-01", "CAM-02"):
            metrics = chain._tracker.metrics(cid)
            self.assertEqual(metrics["camera_id"], cid)
        chain.close()


class TestAdvanceChainFeed(unittest.TestCase):

    def test_feed_walks_whole_chain(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()

        result = chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)

        self.assertEqual(result["camera_id"], "CAM-01")
        # Actividad BALANCED: frame 0 siempre se analiza -> observación.
        self.assertIsNotNone(result["observation"])
        self.assertEqual(result["observation"].observation_type, FRAME_SAMPLE)
        # Inferencia determinista sobre frame brillante -> evento OBJECT_DETECTED
        # (el backend determinista etiqueta la señal brillante como "object").
        self.assertIsNotNone(result["event"])
        self.assertEqual(result["event"].event_type, OBJECT_DETECTED)
        # Tracking: evento -> LocalTrack (obligatorio con event).
        self.assertIsNotNone(result["track"])
        self.assertEqual(result["track"].camera_id, "CAM-01")
        chain.close()

    def test_policy_skip_yields_no_observation(self):
        # BALANCED ~2fps a 15fps: frame 1 salteado -> sin observación ni evento.
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()
        result = chain.feed("CAM-01", 1, 15.0, BRIGHT_FRAME)
        self.assertIsNone(result["observation"])
        self.assertIsNone(result["event"])
        self.assertIsNone(result["track"])
        chain.close()

    def test_black_frame_yields_event_none_but_observation(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()
        result = chain.feed("CAM-01", 0, 15.0, BLACK_FRAME)
        self.assertIsNotNone(result["observation"])
        self.assertIsNone(result["event"])
        self.assertIsNone(result["track"])
        chain.close()


class TestAdvanceChainIsolation(unittest.TestCase):

    def test_camera_isolation(self):
        sm = FakeSourceManager(["CAM-OK", "CAM-BAD"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()

        # CAM-BAD falla: frame cuyo array-ificado lanza -> backend aislado.
        bad = chain.feed("CAM-BAD", 0, 15.0, BrokenFrame())
        # CAM-OK sigue funcionando.
        ok = chain.feed("CAM-OK", 0, 15.0, BRIGHT_FRAME)

        self.assertIsNone(bad["event"])
        self.assertIsNotNone(ok["event"])
        summary = chain.summary()
        self.assertEqual(
            summary["inference"]["metrics"]["CAM-BAD"]["inference_errors"], 1
        )
        chain.close()


class TestAdvanceChainSummary(unittest.TestCase):

    def test_summary_is_auditable_and_secret_free(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()
        chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)
        summary = chain.summary()
        text = json.dumps(summary, default=str)
        self.assertIn("CAM-01", text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("secret", text.lower())
        chain.close()


class TestAdvanceChainClose(unittest.TestCase):

    def test_close_is_clean_and_idempotent(self):
        sm = FakeSourceManager(["CAM-01"])
        chain = AdvanceChain.build(make_config(), sm)
        chain.register_from_source_manager()
        chain.feed("CAM-01", 0, 15.0, BRIGHT_FRAME)
        closed = chain.close()
        self.assertIn("tracker", closed)
        self.assertIn("selective", closed)
        self.assertIn("activity", closed)
        self.assertEqual(chain.close(), {"already_closed": True})


if __name__ == "__main__":
    unittest.main()