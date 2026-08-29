import logging
from typing import Tuple, Dict, Any, Optional
from src.agent.actions.contract import (
    ProposedAction, ALLOWED_ACTION_TYPES, FORBIDDEN_ACTION_TYPES,
    AUTONOMY_0, AUTONOMY_1, AUTONOMY_2, AUTONOMY_3
)

logger = logging.getLogger("action_policy_engine")

class ActionEvidenceGate:
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def evaluate(cls, action: ProposedAction, evidence_bundle: Optional[Dict[str, Any]] = None) -> str:
        if not action.evidence_refs:
            return cls.INSUFFICIENT
        if evidence_bundle:
            state = evidence_bundle.get("state", cls.SUFFICIENT)
            return state
        return cls.SUFFICIENT

class ActionPolicyEngine:
    def __init__(
        self,
        action_execution_enabled: bool = True,
        autonomy_2_enabled: bool = True,
        autonomy_3_enabled: bool = False,
        agent_mode: str = "NORMAL"
    ):
        self.action_execution_enabled = action_execution_enabled
        self.autonomy_2_enabled = autonomy_2_enabled
        self.autonomy_3_enabled = autonomy_3_enabled  # Hardcoded False for Phase 7
        self.agent_mode = agent_mode

    def evaluate(
        self,
        action: ProposedAction,
        system_health: str = "HEALTHY",
        source_health: str = "HEALTHY",
        source_security: str = "VALIDATED",
        evidence_bundle: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Evaluates a ProposedAction against safety, autonomy, and health policies.
        Returns (DECISION, REASON) where DECISION is ALLOW, DENY, or REQUIRE_HUMAN_APPROVAL.
        """
        # 1. Global Action Execution Kill Switch
        if not self.action_execution_enabled:
            return "DENY", "ACTION_KILL_SWITCH_ACTIVE: Global action execution is disabled."

        # 2. Agent Safe Mode
        if self.agent_mode == "SAFE":
            return "DENY", "SAFE_MODE_ACTIVE: Agent is in safe mode; all automated actions are disabled."

        # 3. Default Deny on Unknown or Forbidden Actions
        if action.action_type in FORBIDDEN_ACTION_TYPES:
            return "DENY", f"FORBIDDEN_ACTION: Action type '{action.action_type}' is strictly prohibited."
        if action.action_type not in ALLOWED_ACTION_TYPES:
            return "DENY", f"UNKNOWN_ACTION: Action type '{action.action_type}' is not in the allowlist (Default DENY)."

        # 4. Source Health & Security Gates
        if source_health in ("DEGRADED", "STALE", "UNAVAILABLE"):
            return "REQUIRE_HUMAN_APPROVAL", f"DEGRADED_SOURCE_HEALTH: Source health is '{source_health}', human review required."
        if source_security in ("UNTRUSTED", "SUSPICIOUS", "TAMPERED"):
            return "DENY", f"UNTRUSTED_SOURCE_SECURITY: Source security state is '{source_security}'."

        # 5. Evidence Sufficiency Gate
        evidence_state = ActionEvidenceGate.evaluate(action, evidence_bundle)
        if evidence_state in (ActionEvidenceGate.INSUFFICIENT, ActionEvidenceGate.UNKNOWN):
            return "DENY", f"EVIDENCE_INSUFFICIENT: Action '{action.action_type}' lacks verified evidence support."
        if evidence_state == ActionEvidenceGate.DEGRADED:
            return "REQUIRE_HUMAN_APPROVAL", "EVIDENCE_DEGRADED: Evidence is degraded, human approval required."

        # 6. Autonomy 3 (Sensitive Action) Governance
        if action.requested_autonomy_level == AUTONOMY_3 or action.risk_class == "SENSITIVE":
            if not self.autonomy_3_enabled:
                return "REQUIRE_HUMAN_APPROVAL", "AUTONOMY_3_DISABLED: Sensitive action requires human approval and cannot execute autonomously."
            return "REQUIRE_HUMAN_APPROVAL", "SENSITIVE_ACTION: Autonomy 3 always requires human approval."

        # 7. Autonomy 2 (Limited Action) Evaluation
        if action.requested_autonomy_level == AUTONOMY_2:
            if not self.autonomy_2_enabled:
                return "REQUIRE_HUMAN_APPROVAL", "AUTONOMY_2_DISABLED: Limited action autonomy is disabled; routed to approval."
            if action.risk_class == "LOW" and action.action_type in ALLOWED_ACTION_TYPES:
                return "ALLOW", f"AUTONOMY_2_PERMITTED: Internal reversible action '{action.action_type}' permitted."
            return "REQUIRE_HUMAN_APPROVAL", f"RISK_LEVEL_{action.risk_class}: Action requires human approval."

        # 8. Autonomy 0 or 1 (Observe / Investigate only)
        if action.requested_autonomy_level in (AUTONOMY_0, AUTONOMY_1):
            return "DENY", "READ_ONLY_AUTONOMY: Autonomy 0/1 cannot execute operational actions."

        # Fallback default deny
        return "DENY", "DEFAULT_DENY: No explicit policy rule permitted execution."
