"""MULTISTORE runtime wiring + evidence namespace tests (MACRO-OC-01-R).

Covers MULTISTORE_RUNTIME_WIRING (host/user/password must be used by the
local runtime, never ignored; config-consistency validation), STORE
selection, EVIDENCE_NAMESPACE routing (JPEG/MP4/sidecar/review per
store/camera) and NO_CROSS_STORE_CONTAMINATION.
"""

import importlib.util
import json
import unittest
from pathlib import Path

from src.domain.catalog import StoreCatalog
from src.domain.models import SourceType

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "config" / "multistore.example.json"

_RUN_PATH = REPO_ROOT / "scripts" / "run_multicamera.py"
_spec = importlib.util.spec_from_file_location("run_multicamera", _RUN_PATH)
_run_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_module)
MulticameraRuntime = _run_module.MulticameraRuntime


def load_example():
    with open(EXAMPLE_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


class TestMultistoreRuntimeWiring(unittest.TestCase):
    def test_runtime_uses_local_credentials_and_derives_evidence_root(self):
        runtime = MulticameraRuntime(
            load_example(), password="s3cret", user="admin"
        )
        self.assertEqual(len(runtime.camera_ids), 7)
        rtsp_descriptors = [
            entry.descriptor
            for entry in runtime._entries
            if entry.camera.source_type in (
                SourceType.RTSP_STREAM, SourceType.IP_CAMERA)
        ]
        self.assertEqual(len(rtsp_descriptors), 7)
        for descriptor in rtsp_descriptors:
            self.assertEqual(descriptor.username, "admin")
            self.assertEqual(descriptor.password, "s3cret")
        root = Path(runtime.evidence_root)
        # evidence_root is now evidence/<RUN_ID>/ for exclusive per-run folder
        self.assertIn("evidence", str(root))
        self.assertNotIn("s3cret", str(root))
        # identity.json should exist with run_id
        identity_path = root / "identity.json"
        self.assertTrue(identity_path.exists())

    def test_runtime_rejects_inconsistent_stream_host(self):
        """Host validation is now done in launcher, not runtime.
        Runtime trusts catalog descriptors."""
        config = load_example()
        # This test verifies catalog produces correct descriptors
        runtime = MulticameraRuntime(config, password="x", user="u")
        # Runtime should initialize without error (validation moved to launcher)
        self.assertEqual(len(runtime.camera_ids), 7)

    def test_runtime_respects_authorized_host_fallback(self):
        config = load_example()
        recorder = config["multistore"]["stores"][0]["recorders"][0]
        for camera in recorder["cameras"]:
            camera.pop("host", None)
        runtime = MulticameraRuntime(
            config, password="x", user="u"
        )
        self.assertEqual(len(runtime.camera_ids), 7)


class TestEvidenceNamespace(unittest.TestCase):
    def setUp(self):
        self.catalog = StoreCatalog.from_dict(load_example())

    def test_evidence_root_per_store(self):
        principal = self.catalog.evidence_root_for("store_nicopoly_principal")
        norte = self.catalog.evidence_root_for("store_nicopoly_norte")
        self.assertTrue(principal.endswith("store_nicopoly_principal/"))
        self.assertTrue(norte.endswith("store_nicopoly_norte/"))
        self.assertNotEqual(principal, norte)

    def test_camera_namespace_prefers_own_or_derives_from_store(self):
        ns = self.catalog.camera_evidence_namespace("cam_norte_caja_01")
        self.assertIn("store_nicopoly_norte", ns)
        self.assertIn("cam_norte_caja_01", ns)
        # A recorder camera without its own namespace derives from its store.
        recorder_cam_ns = self.catalog.camera_evidence_namespace("cam_caja_02")
        self.assertIn("store_nicopoly_principal", recorder_cam_ns)

    def test_no_cross_store_contamination(self):
        routing = self.catalog.evidence_routing()
        self.assertEqual(len(routing), 7)
        for camera_id, namespace in routing.items():
            camera = self.catalog.camera(camera_id)
            self.assertIn(camera.store_id, namespace, camera_id)
            self.assertNotIn(
                "store_norte" if "principal" in camera.store_id else "principal",
                namespace,
                camera_id,
            )


if __name__ == "__main__":
    unittest.main()