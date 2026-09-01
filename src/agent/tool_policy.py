import re
from typing import Set

class AgentToolPolicy:
    """
    Enforces a strict ALLOWLIST for the Agent Monitor's tool execution.
    Default policy is DENY.
    """
    def __init__(self):
        self.allowed_tools: Set[str] = {
            "get_scene_state",
            "get_camera_state",
            "get_entities_in_zone",
            "get_entity_state",
            "get_entity_trajectory",
            "get_camera_coverage",
            "get_coverage_gaps",
            "get_evidence_bundle",
            "search_evidence",
            "get_source_security_state",
            "get_active_situations",
            "get_investigation_candidate",
            "get_related_evidence"
        }
        
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Returns True if the tool is explicitly allowed.
        """
        return tool_name in self.allowed_tools

    def sanitize_arguments(self, args: dict) -> dict:
        """
        Removes sensitive information (e.g. RTSP passwords, API keys) from arguments.
        """
        sanitized = {}
        for key, value in args.items():
            key_lower = key.lower()
            if "password" in key_lower or "secret" in key_lower or "credential" in key_lower or "token" in key_lower:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str):
                # Basic regex for rtsp://user:pass@host
                sanitized[key] = re.sub(r'(rtsp://)([^:]+):([^@]+)@', r'\1***:***@', value)
            else:
                sanitized[key] = value
        return sanitized
