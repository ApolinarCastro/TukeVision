"""Targeted Unit Tests for Production Hardening, Media Signing, Semantic Investigation, and Liveness."""

import unittest
from unittest import mock
import tempfile
from pathlib import Path

from src.evidence.models import EvidenceMetadata, MediaSigningStatus
from src.evidence.bundle import EvidenceBundle
from src.evidence.index import SemanticEvidenceIndex, SemanticInvestigationEngine
from src.visualization.operational_intelligence import EvidenceBundleViewItem


class TestProductionHardening(unittest.TestCase):
    def test_media_signing_status_and_defaults(self):
        # By default, local DVR streams must declare SOURCE_UNSIGNED, never fabricate SIGNED_VALID
        meta = EvidenceMetadata(
            alert_id="ALT-01",
            event_id="EVT-01",
            observation_ids=("OBS-01",),
            track_id=1,
            zone_id="Z1",
            duration_seconds=5.0,
            risk_score=10,
            rule_id="RULE-1",
            timestamp="2026-08-30T12:00:00Z",
            frame_sha256="abc123sha",
        )
        self.assertEqual(meta.signing_status, MediaSigningStatus.SOURCE_UNSIGNED)
        self.assertEqual(meta.verification_status, "NOT_APPLICABLE")

    def test_evidence_bundle_view_item_media_signing_contract(self):
        bundle = EvidenceBundleViewItem(
            bundle_id="BND-01",
            source_camera="cam_01",
            observed_at="2026-08-30T12:00:00Z",
            entity_id="TRK-1",
            situation_id="SIT-01",
            confidence=0.92,
            detector_runtime="openvino",
            model_id="yolo11n",
            hashes={"key_frame.jpg": "hash123"},
            key_frame_path="key.jpg",
            roi_crop_path="crop.jpg",
        )
        self.assertEqual(bundle.signing_status, "SOURCE_UNSIGNED")
        self.assertEqual(bundle.verification_status, "NOT_APPLICABLE")

    def test_semantic_investigation_on_demand_scope_and_source_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test_evidence.db")
            idx = SemanticEvidenceIndex(db_path)
            engine = SemanticInvestigationEngine(idx)

            b = EvidenceBundle(
                bundle_id="BND-100",
                source_camera="cam_02",
                observed_at="2026-08-30T12:30:00Z",
                created_at="2026-08-30T12:30:01Z",
                metadata={"site_id": "store_principal", "rule": "LOITERING"},
                situation_id="SIT-100",
                entity_id="TRK-42",
            )
            idx.index_bundle(b, "path/to/bnd100.json")

            # Query historical scope
            results = engine.query_historical_scope(
                site_id="store_principal",
                camera_id="cam_02",
                start_time="2026-08-30T12:00:00Z",
                end_time="2026-08-30T13:00:00Z",
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["bundle_id"], "BND-100")
            self.assertEqual(results[0]["source_camera"], "cam_02")
            self.assertIn("dvr://store_principal/cam_02", results[0]["source_link"])
            self.assertEqual(results[0]["provenance"], "ON_DEMAND_HISTORICAL_MATCH")
