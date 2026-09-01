import logging
import json
import time
from typing import Dict, Any, List
from src.agent.tool_policy import AgentToolPolicy

logger = logging.getLogger("agent_audit")
_policy = AgentToolPolicy()

class AgentAuditLog:
    """
    Records Agent Monitor actions securely and persistently.
    """
    def __init__(self, log_path: str = "data/agent_audit.jsonl"):
        self.log_path = log_path
        
    def record_investigation_step(
        self,
        investigation_id: str,
        candidate_id: str,
        tool: str,
        args: Dict[str, Any],
        result_reference: str,
        facts_generated: List[str],
        inferences_generated: List[str],
        priority_change: str,
        duration: float,
        error: str = ""
    ):
        """
        Logs a single tool execution and its analytical consequence during an investigation.
        """
        sanitized_args = _policy.sanitize_arguments(args)
        
        record = {
            "timestamp": time.time(),
            "investigation_id": investigation_id,
            "candidate_id": candidate_id,
            "tool": tool,
            "arguments_sanitized": sanitized_args,
            "result_reference": result_reference,
            "facts_generated": facts_generated,
            "inferences_generated": inferences_generated,
            "priority_change": priority_change,
            "error": error,
            "duration": duration
        }
        
        log_line = json.dumps(record)
        
        # Also emit via standard python logger
        logger.info(f"AUDIT_RECORD tool={tool} inv={investigation_id} facts={len(facts_generated)}")
        
        # Append to persistent JSONL log
        import os
        from pathlib import Path
        path = Path(self.log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(log_line + "\n")
