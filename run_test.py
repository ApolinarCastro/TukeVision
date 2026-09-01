import json
import dataclasses
from pathlib import Path
from src.evidence.bundle import EvidenceBundle

b1 = EvidenceBundle(
    bundle_id="EVD-MCP-01",
    source_camera="cam_01",
    observed_at="2026-08-28T10:00:00Z",
    created_at="2026-08-28T10:00:01Z",
    tags={},
    metadata={"test": "true"}
)

try:
    with open("tmp_test_mcp_01.json", "w") as f:
        json.dump(dataclasses.asdict(b1), f)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
