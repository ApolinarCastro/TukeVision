"""Evidence routing tests (MACRO-OC-02, Bloques B/C).

Covers:
  - EVIDENCE_ISOLATION: STORE_A_EVIDENCE != STORE_B_EVIDENCE (roots and JPEGs)
  - REVIEW_ISOLATION: per-store review JSONL targets, never shared
  - RUNTIME_HOST_USER_ROUTING: store/organization context on records/clips
  - ROOT_ESCAPE_GUARD: evidence references cannot escape a store root
  - Reuses the existing PersistentEvidenceStore/EvidenceClipAdapter/
    BoundedReviewExporter (no second EvidenceStore created).
"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.domain.catalog import StoreCatalog
from src.evidence.routing import (
    EvidenceRoutingError,
    RoutingEvidenceClipAdapter,
    RoutingEvidenceStore,
    StoreEvidenceRouter,
)
from src.review.contracts import SignalReviewRecord

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG = REPO_ROOT / "config" / "multistore.example.json"


def load_example():
    with open(EXAMPLE_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)

FRAME = np.zeros((64, 96, 3), dtype="uint8")
FRAME[8:48, 16:80] = 255


def make_record(camera_id, signal_id, signal_type, store_id, organization_id):
    return SignalReviewRecord(
        review_id=f"SRR-{signal_id}",
        signal_id=signal_id,
        signal_type=signal_type,
        camera_id=camera_id,
        store_id=store_id,
        organization_id=organization_id,
        track_id="T-1",
        trajectory_id=None,
        rule_id="prolonged_dwell",
        timestamp_start="2026-08-19T00:00:00Z",
        timestamp_end="2026-08-19T00:00:10Z",
        rule_score=70.0,
        source_refs=(),
        evidence_refs=(),
        structured_explanation={},
        human_classification="NOT_REVIEWED",
    )


class TestStoreEvidenceRouter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "evidence"
        self.catalog = StoreCatalog.from_dict(load_example())
        self.router = StoreEvidenceRouter(
            self.catalog,
            evidence_base=str(self.base),
            evidence_config={"max_per_camera": 4, "jpeg_quality": 90},
            clip_config={"max_clips_per_camera": 4, "max_clip_duration_seconds": 10.0},
            review_config={"max_records_total": 8, "max_records_per_camera": 2},
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_per_store_roots_and_review_targets_are_disjoint(self):
        principal = self.router.root_for_store("store_nicopoly_principal")
        norte = self.router.root_for_store("store_nicopoly_norte")
        self.assertNotEqual(principal, norte)
        self.assertIn("store_nicopoly_principal", str(principal))
        self.assertIn("store_nicopoly_norte", str(norte))
        self.assertNotEqual(
            self.router.review_target_for("store_nicopoly_principal"),
            self.router.review_target_for("store_nicopoly_norte"),
        )

    def test_context_for_camera_resolves_store(self):
        context = self.router.context_for_camera("cam_caja_01")
        self.assertEqual(context.store_id, "store_nicopoly_principal")
        self.assertEqual(context.organization_id, "org_nicopoly")
        self.assertEqual(context.store_name, "Nicopoly Tienda Central")

    def test_unknown_camera_raises_routing_error(self):
        with self.assertRaises(EvidenceRoutingError):
            self.router.context_for_camera("cam_inexistente")

    def test_evidence_isolation_across_stores(self):
        routing_store = RoutingEvidenceStore(self.router)
        cam_a = "cam_caja_01"
        cam_b = "cam_norte_caja_01"
        ref_a = routing_store.persist_selected(
            FRAME, camera_id=cam_a, timestamp="2026-08-19T00:00:00Z",
            producer="activity-policy", observation_ref="OBS-A",
        )
        ref_b = routing_store.persist_selected(
            FRAME, camera_id=cam_b, timestamp="2026-08-19T00:00:00Z",
            producer="activity-policy", observation_ref="OBS-B",
        )
        store_a = self.router.persistent_store_for(cam_a)
        store_b = self.router.persistent_store_for(cam_b)
        self.assertEqual(store_a.store_id, "store_nicopoly_principal")
        self.assertEqual(store_b.store_id, "store_nicopoly_norte")
        self.assertNotEqual(store_a.root, store_b.root)
        # Store A cannot resolve an artifact owned by Store B.
        self.assertFalse(store_a.verify(ref_b["relative_path"]))
        self.assertFalse(store_b.verify(ref_a["relative_path"]))
        # Each record carries its store/org context.
        meta = json.loads(
            store_a.resolve(ref_a["relative_path"]).with_name("metadata.json").read_text("utf-8")
        )
        self.assertEqual(meta["store_id"], "store_nicopoly_principal")
        self.assertEqual(meta["organization_id"], "org_nicopoly")

    def test_root_escape_guard(self):
        routing_store = RoutingEvidenceStore(self.router)
        cam_a = "cam_caja_01"
        routing_store.persist_selected(
            FRAME, camera_id=cam_a, timestamp="2026-08-19T00:00:00Z",
            producer="activity-policy", observation_ref="OBS-A",
        )
        self.assertIsNone(self.router.resolve_evidence("../escape.jpg", cam_a))
        self.assertIsNone(self.router.resolve_evidence("/etc/passwd", cam_a))

    def test_review_isolation_per_store(self):
        exporter = self.router.review_exporter()
        record_a = make_record(
            "cam_caja_01", "BS-A", "PROLONGED_DWELL",
            "store_nicopoly_principal", "org_nicopoly",
        )
        record_b = make_record(
            "cam_norte_caja_01", "BS-B", "PROLONGED_DWELL",
            "store_nicopoly_norte", "org_nicopoly",
        )
        self.assertTrue(exporter.offer(record_a))
        self.assertTrue(exporter.offer(record_b))
        exporter.export_jsonl()
        target_a = self.router.review_target_for("store_nicopoly_principal")
        target_b = self.router.review_target_for("store_nicopoly_norte")
        records_a = [json.loads(line) for line in target_a.read_text("utf-8").splitlines() if line]
        records_b = [json.loads(line) for line in target_b.read_text("utf-8").splitlines() if line]
        self.assertEqual([r["signal_id"] for r in records_a], ["BS-A"])
        self.assertEqual([r["signal_id"] for r in records_b], ["BS-B"])
        self.assertEqual(records_a[0]["store_id"], "store_nicopoly_principal")
        self.assertEqual(records_b[0]["store_id"], "store_nicopoly_norte")

    def test_review_stats_aggregate_across_stores(self):
        exporter = self.router.review_exporter()
        exporter.offer(make_record(
            "cam_caja_01", "BS-A", "PROLONGED_DWELL",
            "store_nicopoly_principal", "org_nicopoly",
        ))
        exporter.offer(make_record(
            "cam_norte_caja_01", "BS-B", "PROLONGED_DWELL",
            "store_nicopoly_norte", "org_nicopoly",
        ))
        stats = exporter.stats()
        self.assertEqual(stats["total_available"], 2)
        self.assertEqual(len(stats["stores"]), 2)

    def test_clip_adapter_routes_per_camera(self):
        adapter = RoutingEvidenceClipAdapter(self.router, max_clip_duration_seconds=10.0)
        self.assertEqual(adapter.max_clip_duration_seconds, 10.0)
        metadata = adapter.unavailable(
            camera_id="cam_caja_01",
            signal_id="BS-A",
            start_timestamp=0.0,
            end_timestamp=0.0,
            reason="clip_disabled",
        )
        self.assertEqual(metadata["availability"], "UNAVAILABLE")
        self.assertEqual(metadata["store_id"], "store_nicopoly_principal")

    def test_routing_summary_is_auditable(self):
        summary = self.router.routing_summary()
        self.assertEqual(summary["organization_id"], "org_nicopoly")
        self.assertEqual(len(summary["stores"]), 2)
        for store in summary["stores"]:
            self.assertTrue(store["root"])
            self.assertTrue(store["review_target"])


if __name__ == "__main__":
    unittest.main()