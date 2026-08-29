"""Local MCP Server (Read-Only).

Provides tools for external agents to query the operational state of the store
and retrieve evidence bundles securely without modification privileges.
"""

import json
from typing import Dict, Any, Optional
import logging

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Dummy fallback for testing environments without the mcp sdk
    class FastMCP:
        def __init__(self, name):
            self.name = name
            self.tools = {}
        def tool(self):
            def decorator(func):
                self.tools[func.__name__] = func
                return func
            return decorator

from src.spatial.store_map import StoreOperationalMap
from src.evidence.index import SemanticEvidenceIndex
from src.evidence.bundle import EvidenceBundleStore

logger = logging.getLogger("tukevision.mcp_server")

# Global instances (to be injected at runtime)
# In a real environment, these would be initialized centrally.
_store_map: Optional[StoreOperationalMap] = None
_evidence_index: Optional[SemanticEvidenceIndex] = None
_bundle_store: Optional[EvidenceBundleStore] = None

mcp = FastMCP("TukeVision Operational Intelligence")

def setup_mcp_dependencies(
    store_map: StoreOperationalMap,
    evidence_index: SemanticEvidenceIndex,
    bundle_store: EvidenceBundleStore
):
    global _store_map, _evidence_index, _bundle_store
    _store_map = store_map
    _evidence_index = evidence_index
    _bundle_store = bundle_store

@mcp.tool()
def get_store_scene_state() -> Dict[str, Any]:
    """Retrieve the current unified operational map of the store."""
    if not _store_map:
        return {"error": "Store Operational Map not initialized."}
        
    state = _store_map.generate_scene_state()
    # Serialize dataclasses to dict (simplified)
    import dataclasses
    
    def to_dict_recursive(obj):
        if dataclasses.is_dataclass(obj):
            d = dataclasses.asdict(obj)
            return to_dict_recursive(d)
        elif isinstance(obj, dict):
            return {k: to_dict_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_dict_recursive(i) for i in obj]
        elif hasattr(obj, "value"):
            return obj.value
        else:
            return obj
            
    raw_json = json.dumps(to_dict_recursive(state))
    return json.loads(raw_json)

@mcp.tool()
def search_evidence(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    camera_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Search for relevant evidence bundles using semantic parameters."""
    if not _evidence_index:
        return {"error": "Semantic Evidence Index not initialized."}
        
    try:
        results = _evidence_index.search_bundles(
            start_time=start_time,
            end_time=end_time,
            camera_id=camera_id,
            tags=tags
        )
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_evidence_bundle(bundle_id: str) -> Dict[str, Any]:
    """Retrieve the complete metadata and file paths for a specific evidence bundle."""
    # To retrieve the full bundle, we would typically load it from disk or db.
    # The index tells us where it is, or we use bundle_store if it supports fetching.
    if not _evidence_index:
        return {"error": "Semantic Evidence Index not initialized."}
        
    # Hacky way: search by id using tags (we might not have a direct query in index)
    # Let's execute a direct query for simplicity of the MCP layer
    with _evidence_index._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT path_to_json FROM bundles WHERE bundle_id = ?", (bundle_id,))
        row = cursor.fetchone()
        
    if not row:
        return {"error": f"Bundle {bundle_id} not found."}
        
    try:
        with open(row["path_to_json"], "r") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load bundle data: {str(e)}"}
