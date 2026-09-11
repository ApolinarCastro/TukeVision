"""Tests for Semantic Evidence Index (Slice 8)."""

import pytest
import shutil
from pathlib import Path
from src.evidence.bundle import EvidenceBundle
from src.evidence.index import SemanticEvidenceIndex

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_evidence_index.db"
    yield str(db_file)
    if db_file.exists():
        db_file.unlink()

def test_semantic_index_lifecycle(temp_db):
    index = SemanticEvidenceIndex(db_path=temp_db)
    
    # 1. Index a bundle
    b1 = EvidenceBundle(
        bundle_id="EVD-001",
        source_camera="cam_01",
        observed_at="2026-08-28T10:00:00Z",
        created_at="2026-08-28T10:00:01Z",
        entity_id="ENT-1",
        situation_id="SIT-LOITERING",
        metadata={"color": "red", "type": "person"}
    )
    
    b2 = EvidenceBundle(
        bundle_id="EVD-002",
        source_camera="cam_02",
        observed_at="2026-08-28T10:05:00Z",
        created_at="2026-08-28T10:05:01Z",
        entity_id="ENT-2",
        metadata={"color": "blue", "type": "vehicle"}
    )
    
    index.index_bundle(b1, "/data/evd_001.json")
    index.index_bundle(b2, "/data/evd_002.json")
    
    # 2. Search by Camera
    results = index.search_bundles(camera_id="cam_01")
    assert len(results) == 1
    assert results[0]["bundle_id"] == "EVD-001"
    
    # 3. Search by Time Range
    results_time = index.search_bundles(
        start_time="2026-08-28T10:01:00Z",
        end_time="2026-08-28T10:10:00Z"
    )
    assert len(results_time) == 1
    assert results_time[0]["bundle_id"] == "EVD-002"
    
    # 4. Search by Tag (color=red)
    results_tag = index.search_bundles(tags={"color": "red"})
    assert len(results_tag) == 1
    assert results_tag[0]["bundle_id"] == "EVD-001"
    
    # 5. Search by Situation (which maps to a tag)
    results_sit = index.search_bundles(tags={"situation": "SIT-LOITERING"})
    assert len(results_sit) == 1
    
    # 6. Search by Entity
    results_ent = index.search_bundles(entity_id="ENT-2")
    assert len(results_ent) == 1
    assert results_ent[0]["bundle_id"] == "EVD-002"
    
    # 7. No matches
    assert len(index.search_bundles(tags={"color": "green"})) == 0
