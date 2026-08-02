"""Pruebas unitarias para src.evidence.store (sin dependencias externas)."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.evidence.store import EvidenceStore, EvidenceExistsError, InvalidEvidenceError
from src.evidence.models import EvidenceMetadata


class TestEvidenceStore(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "evidence"
        self.store = EvidenceStore(base_dir=str(self.base))
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.metadata = EvidenceMetadata(
            alert_id="ALR-00001",
            event_id="EVT-00001",
            observation_ids=("OBS-00001", "OBS-00002"),
            track_id=1,
            zone_id="ZONE-001",
            duration_seconds=90.0,
            risk_score=80,
            rule_id="RULE-PERMANENCIA-001",
            timestamp="2026-08-02T12:00:00Z",
            frame_sha256="",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_saves_frame_and_metadata(self) -> None:
        """Verifica que guarda fotograma y metadatos."""
        result = self.store.save(self.frame, self.metadata)
        frame_path = self.base / "ALR-00001" / "frame.jpg"
        meta_path = self.base / "ALR-00001" / "metadata.json"
        self.assertTrue(frame_path.exists())
        self.assertTrue(meta_path.exists())
        self.assertIsNotNone(result)

    def test_metadata_is_valid_json(self) -> None:
        """Verifica que los metadatos son JSON válido."""
        self.store.save(self.frame, self.metadata)
        with (self.base / "ALR-00001" / "metadata.json").open(
            "r", encoding="utf-8"
        ) as fh:
            data = json.load(fh)
        self.assertEqual(data["alert_id"], "ALR-00001")
        self.assertEqual(data["event_id"], "EVT-00001")
        self.assertEqual(data["zone_id"], "ZONE-001")
        self.assertEqual(data["risk_score"], 80)
        self.assertEqual(data["rule_id"], "RULE-PERMANENCIA-001")
        self.assertEqual(list(data["observation_ids"]), ["OBS-00001", "OBS-00002"])

    def test_calculates_frame_sha256(self) -> None:
        """Verifica que se calcula el SHA-256 del fotograma."""
        self.store.save(self.frame, self.metadata)
        with (self.base / "ALR-00001" / "metadata.json").open(
            "r", encoding="utf-8"
        ) as fh:
            data = json.load(fh)
        self.assertRegex(data["frame_sha256"], r"^[0-9a-f]{64}$")

    def test_does_not_overwrite_existing_evidence(self) -> None:
        """Verifica que no sobrescribe evidencia existente."""
        self.store.save(self.frame, self.metadata)
        with self.assertRaises(EvidenceExistsError):
            self.store.save(self.frame, self.metadata)

    def test_exists(self) -> None:
        """Verifica el método exists."""
        self.assertFalse(self.store.exists("ALR-00001"))
        self.store.save(self.frame, self.metadata)
        self.assertTrue(self.store.exists("ALR-00001"))

    def test_rejects_none_frame(self) -> None:
        """Verifica rechazo de fotograma nulo."""
        with self.assertRaises(InvalidEvidenceError):
            self.store.save(None, self.metadata)

    def test_rejects_missing_metadata(self) -> None:
        """Verifica rechazo de metadatos sin alert_id."""
        with self.assertRaises(InvalidEvidenceError):
            self.store.save(self.frame, None)

    def test_load_metadata(self) -> None:
        """Verifica carga de metadatos."""
        self.store.save(self.frame, self.metadata)
        data = self.store.load_metadata("ALR-00001")
        self.assertEqual(data["track_id"], 1)
        self.assertEqual(data["duration_seconds"], 90.0)

    def test_load_missing_metadata_returns_none(self) -> None:
        """Verifica que carga de metadatos inexistente devuelve None."""
        self.assertIsNone(self.store.load_metadata("ALR-NOPE"))


if __name__ == "__main__":
    unittest.main()
