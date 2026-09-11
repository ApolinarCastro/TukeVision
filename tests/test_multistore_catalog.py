"""MULTISTORE catalog + lifecycle tests (MACRO-OC-01-R, Block 9).

Covers MULTISTORE_CATALOG (enum/string parsing, summary(), credential
resolution, descriptor mapping, partial stores, DVR/NVR, direct IP) and
STORE_LIFECYCLE (store selection, active stores, store_status). Secrets
must never appear in the catalog summary.
"""

import json
import os
import unittest
from pathlib import Path

from src.capture.source_manager import CameraDescriptor
from src.domain.catalog import StoreCatalog
from src.domain.models import RecorderType, SourceType, ZoneRole

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "config" / "multistore.example.json"


def load_example():
    with open(EXAMPLE_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


class TestMultistoreCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = StoreCatalog.from_dict(load_example())

    def test_two_stores_loaded_in_order(self):
        self.assertEqual(self.catalog.store_ids(), [
            "store_nicopoly_principal", "store_nicopoly_norte",
        ])

    def test_summary_exposes_structure_without_secrets(self):
        summary = self.catalog.summary()
        self.assertEqual(summary["organization_id"], "org_nicopoly")
        self.assertEqual(summary["total_stores"], 2)
        self.assertEqual(len(summary["stores"]), 2)
        self.assertGreater(summary["total_cameras"], 0)
        blob = json.dumps(summary)
        self.assertNotIn("password", blob.lower())
        self.assertNotIn("rtsp://", blob)

    def test_recorder_type_and_role_are_enums_not_strings(self):
        store = self.catalog.store("store_nicopoly_principal")
        recorder = store.recorders[0]
        self.assertIsInstance(recorder.recorder_type, RecorderType)
        self.assertEqual(recorder.recorder_type, RecorderType.DVR)
        self.assertEqual(store.recorders[1].recorder_type, RecorderType.NVR)
        for camera in store.recorders[0].cameras:
            self.assertIsInstance(camera.role, ZoneRole)
        direct = store.direct_cameras[0]
        self.assertIsInstance(direct.source_type, SourceType)
        self.assertEqual(direct.source_type, SourceType.IP_CAMERA)

    def test_camera_descriptors_resolve_credentials_and_map(self):
        entries = self.catalog.camera_descriptors(
            credential_resolver=lambda ref: ("admin", "s3cret")
        )
        self.assertEqual(len(entries), 7)
        rtsp_entries = [e for e in entries if e.camera.source_type in (
            SourceType.RTSP_STREAM, SourceType.IP_CAMERA)]
        self.assertEqual(len(rtsp_entries), 7)
        for entry in rtsp_entries:
            self.assertIsInstance(entry.descriptor, CameraDescriptor)
            self.assertEqual(entry.descriptor.username, "admin")
            self.assertEqual(entry.descriptor.password, "s3cret")

    def test_legacy_config_maps_to_single_legacy_store(self):
        legacy = {
            "business": {"store_id": "STORE-001"},
            "zone": {"name": "Zona piloto"},
            "correlation": {"transitions": []},
        }
        catalog = StoreCatalog.from_dict(legacy)
        self.assertEqual(catalog.store_ids(), ["STORE-001"])
        self.assertEqual(len(catalog.cameras()), 4)
        self.assertTrue(
            all(c.source_type == SourceType.VIDEO_FILE for c in catalog.cameras())
        )


class TestStoreLifecycle(unittest.TestCase):
    def setUp(self):
        self.catalog = StoreCatalog.from_dict(load_example())

    def test_active_stores_require_at_least_one_enabled_camera(self):
        active = {store.store_id for store in self.catalog.active_stores()}
        self.assertEqual(
            active, {"store_nicopoly_principal", "store_nicopoly_norte"}
        )

    def test_store_status_summarizes_lifecycle_without_secrets(self):
        status = self.catalog.store_status("store_nicopoly_principal")
        self.assertEqual(status["store_id"], "store_nicopoly_principal")
        self.assertEqual(status["recorders"], 2)
        self.assertEqual(status["direct_cameras"], 1)
        self.assertEqual(status["total_cameras"], 6)
        self.assertEqual(status["enabled_cameras"], 6)
        self.assertIn("cam_caja_01", status["camera_ids"])
        self.assertEqual(
            status["evidence_namespace"],
            "data/evidence/store_nicopoly_principal/",
        )

    def test_unknown_store_raises(self):
        from src.domain.errors import CatalogError
        with self.assertRaises(CatalogError):
            self.catalog.store("store_inexistente")


if __name__ == "__main__":
    unittest.main()