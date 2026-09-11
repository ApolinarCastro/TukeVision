import time
import logging
from typing import Dict, Any, List, Optional
from src.agent.actions.contract import (
    ProposedAction, HumanApprovalRequest, ActionResult, AUTONOMY_2
)
from src.agent.actions.policy import ActionPolicyEngine
from src.agent.actions.executor import GovernedActionExecutor
from src.agent.actions.queue import GovernedActionQueue
from src.agent.experience.service import ExperienceService
from src.agent.experience.contract import OperationalExperience

logger = logging.getLogger("governed_action_service")

class GovernedActionService:
    """
    Central operational response service coordinating proposals, policies, approvals,
    execution, provenance tracking, and experience recording.
    """
    def __init__(
        self,
        policy_engine: Optional[ActionPolicyEngine] = None,
        executor: Optional[GovernedActionExecutor] = None,
        queue: Optional[GovernedActionQueue] = None,
        experience_service: Optional[ExperienceService] = None
    ):
        self.policy_engine = policy_engine or ActionPolicyEngine()
        self.executor = executor or GovernedActionExecutor()
        self.queue = queue or GovernedActionQueue()
        self.experience_service = experience_service

        self._actions: Dict[str, ProposedAction] = {}
        self._approvals: Dict[str, HumanApprovalRequest] = {}
        self._results: Dict[str, ActionResult] = {}
        self._investigation_index: Dict[str, List[str]] = {}

    def propose_action(self, action: ProposedAction) -> ProposedAction:
        self._actions[action.action_id] = action
        if action.investigation_id not in self._investigation_index:
            self._investigation_index[action.investigation_id] = []
        self._investigation_index[action.investigation_id].append(action.action_id)
        self.queue.push(action)
        return action

    def evaluate_and_execute(
        self,
        action_id: str,
        system_health: str = "HEALTHY",
        source_health: str = "HEALTHY",
        source_security: str = "VALIDATED",
        evidence_bundle: Optional[Dict[str, Any]] = None,
        current_timestamp: Optional[float] = None
    ) -> ActionResult:
        action = self._actions.get(action_id)
        if not action:
            return ActionResult(
                action_id=action_id,
                result_state="FAILED",
                error_code="ACTION_NOT_FOUND",
                error_message=f"Action {action_id} not found."
            )

        # Policy evaluation
        decision, reason = self.policy_engine.evaluate(
            action=action,
            system_health=system_health,
            source_health=source_health,
            source_security=source_security,
            evidence_bundle=evidence_bundle
        )

        approval = None
        if decision == "REQUIRE_HUMAN_APPROVAL":
            # Check if an existing approval exists
            approval = self._approvals.get(action.action_id)
            if not approval or approval.status != "APPROVED":
                # Create pending approval request
                if not approval:
                    approval = HumanApprovalRequest(
                        approval_id=f"APPR-{action.action_id}",
                        action_id=action.action_id,
                        requested_at=str(current_timestamp or time.time()),
                        action_summary=f"Approve action {action.action_type} on {action.target_id}",
                        reason=reason,
                        evidence_refs=action.evidence_refs,
                        risk_class=action.risk_class,
                        status="PENDING",
                        expires_at=action.expires_at
                    )
                    self._approvals[action.action_id] = approval
                action.status = "PENDING_APPROVAL"
                res = ActionResult(
                    action_id=action.action_id,
                    result_state="FAILED",
                    error_code="APPROVAL_REQUIRED",
                    error_message=f"Action requires human approval: {reason}"
                )
                self._results[action.action_id] = res
                return res

        # Execute
        result = self.executor.execute(
            action=action,
            policy_decision=decision,
            policy_reason=reason,
            approval=approval,
            current_timestamp=current_timestamp
        )
        self._results[action.action_id] = result
        return result

    def submit_human_approval(
        self,
        action_id: str,
        approver: str,
        approved: bool,
        rejection_reason: Optional[str] = None
    ) -> HumanApprovalRequest:
        approval = self._approvals.get(action_id)
        if not approval:
            approval = HumanApprovalRequest(
                approval_id=f"APPR-{action_id}",
                action_id=action_id,
                requested_at=str(time.time()),
                action_summary=f"Approval for action {action_id}",
                reason="Manual approval request created",
                status="PENDING"
            )
            self._approvals[action_id] = approval

        if approved:
            approval.status = "APPROVED"
            approval.approved_by = approver
            approval.approved_at = str(time.time())
        else:
            approval.status = "REJECTED"
            approval.approved_by = approver
            approval.rejection_reason = rejection_reason or "Operator rejected proposal"

        return approval

    def get_action(self, action_id: str) -> Optional[ProposedAction]:
        return self._actions.get(action_id)

    def get_actions_for_investigation(self, investigation_id: str) -> List[ProposedAction]:
        action_ids = self._investigation_index.get(investigation_id, [])
        return [self._actions[aid] for aid in action_ids if aid in self._actions]

    def get_pending_approvals(self) -> List[HumanApprovalRequest]:
        return [app for app in self._approvals.values() if app.status == "PENDING"]

    def get_action_audit(self, action_id: str) -> List[Dict[str, Any]]:
        return [entry for entry in self.executor.execution_audit if entry.get("action_id") == action_id]

    def trace_provenance(self, action_id: str, context_graph: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        action = self.get_action(action_id)
        if not action:
            return {"status": "NOT_FOUND"}

        provenance = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "investigation_id": action.investigation_id,
            "supporting_facts": action.supporting_fact_refs,
            "evidence_refs": action.evidence_refs,
            "camera_id": action.target_id if action.target_type == "CAMERA" else (context_graph.get("camera_id") if context_graph else "cam_01"),
            "timestamp": action.proposed_at,
            "status": action.status
        }
        return provenance

    def record_action_experience(self, action_id: str, operator_assessment: str, outcome_result: str):
        if not self.experience_service:
            return
        action = self.get_action(action_id)
        if not action:
            return

        exp = OperationalExperience(
            experience_id=f"EXP-ACT-{action.action_id}",
            problem=f"Action proposal for {action.action_type}",
            source="GovernedActionService",
            source_reference=action.action_id,
            pattern=f"action_{action.action_type}",
            evidence_refs=action.evidence_refs,
            decision=action.status,
            outcome=outcome_result,
            lesson_learned=f"Action {action.action_type} executed and verified with outcome: {operator_assessment}"
        )
        self.experience_service.record_experience(exp)

class GovernedActionMCPReadOnly:
    """
    Read-only MCP interface for action state inspection. Denies all write/mutation operations.
    """
    def __init__(self, action_service: GovernedActionService):
        self.action_service = action_service

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        act = self.action_service.get_action(action_id)
        if act:
            return act.__dict__
        return None

    def get_actions_for_investigation(self, investigation_id: str) -> List[Dict[str, Any]]:
        acts = self.action_service.get_actions_for_investigation(investigation_id)
        return [a.__dict__ for a in acts]

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        apps = self.action_service.get_pending_approvals()
        return [a.__dict__ for a in apps]

    def get_action_audit(self, action_id: str) -> List[Dict[str, Any]]:
        return self.action_service.get_action_audit(action_id)

    # Strictly Prohibited MCP Operations
    def execute_action(self, *args, **kwargs):
        raise PermissionError("MCP_DENIED: Action execution is strictly prohibited via MCP interface.")

    def approve_action(self, *args, **kwargs):
        raise PermissionError("MCP_DENIED: Action approval is strictly prohibited via MCP interface.")

    def change_policy(self, *args, **kwargs):
        raise PermissionError("MCP_DENIED: Policy modification is strictly prohibited via MCP interface.")

    def change_autonomy(self, *args, **kwargs):
        raise PermissionError("MCP_DENIED: Autonomy alteration is strictly prohibited via MCP interface.")
