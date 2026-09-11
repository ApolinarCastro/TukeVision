"""Tests for MCP Local Read-Only Server (Slice 9)."""

import pytest
import json
from pathlib import Path

from src.mcp_server import mcp, setup_mcp_dependencies, get_store_scene_state, search_evidence, get_evidence_bundle
from src.spatial.store_map import StoreOperationalMap
from src.spatial.viewshed import ViewshedEngine
from src.spatial.entity_state import SpatialStateManager
from src.spatial.homography import HomographyEngine
from src.evidence.index import SemanticEvidenceIndex
from src.evidence.bundle import EvidenceBundle

@pytest.fixture
def mcp_env(tmp_path):
    # Mock Store Map
    viewshed = ViewshedEngine()
    homography = HomographyEngine()
    spatial = SpatialStateManager(homography)
    store_map = StoreOperationalMap("STORE-MCP", viewshed, spatial)
    
    # Mock Evidence Index
    db_path = tmp_path / "mcp_test.db"
    index = SemanticEvidenceIndex(db_path=str(db_path))
    
    # Create a dummy bundle
    b1 = EvidenceBundle(
        bundle_id="EVD-MCP-01",
        source_camera="cam_01",
        observed_at="2026-08-28T10:00:00Z",
        created_at="2026-08-28T10:00:01Z",
        metadata={"test": "true"}
    )
    
    # Save dummy json
    json_path = tmp_path / "evd_mcp_01.json"
    import dataclasses
    with open(json_path, "w") as f:
        json.dump(dataclasses.asdict(b1), f)
        
    index.index_bundle(b1, str(json_path))
    
    setup_mcp_dependencies(store_map, index, None)
    return mcp

def test_mcp_get_store_scene_state(mcp_env):
    state = get_store_scene_state()
    assert "error" not in state
    assert state["store_id"] == "STORE-MCP"
    assert "cameras" in state
    assert "entities" in state
    
def test_mcp_search_evidence(mcp_env):
    res = search_evidence(camera_id="cam_01")
    assert "error" not in res
    assert len(res["results"]) == 1
    assert res["results"][0]["bundle_id"] == "EVD-MCP-01"

def test_mcp_get_evidence_bundle(mcp_env):
    res = get_evidence_bundle("EVD-MCP-01")
    assert "error" not in res
    assert res["bundle_id"] == "EVD-MCP-01"
    assert res["source_camera"] == "cam_01"
    
def test_mcp_read_only_protection():
    # Verify that MCP only exposes the 3 read methods
    tools = mcp.tools
    assert "get_store_scene_state" in tools
    assert "search_evidence" in tools
    assert "get_evidence_bundle" in tools
    assert "index_bundle" not in tools # Not exposed!
    assert "update_observation" not in tools # Not exposed!
