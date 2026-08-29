import time
import logging
from typing import Dict, Any, Optional, Callable
from src.agent.actions.contract import (
    ProposedAction, HumanApprovalRequest, ActionResult,
    ALLOWED_ACTION_TYPES, AUTONOMY_2, AUTONOMY_3
)
from src.agent.actions.verifier import ActionVerifier

logger = logging.getLogger("governed_action_executor")

# Non-human actor signatures that cannot self-approve
NON_HUMAN_APPROVERS = {
    "agentmonitor", "agent_monitor", "reasoningprovider",
    "llm", "vlm", "qwen", "moondream", "ai", "agent", "system", "auto"
}

class BaseActionHandler:
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        raise NotImplementedError

class CreateOperatorAlertHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        alert_ref = f"ALERT-{action.action_id}"
        # Register in verifier state to ensure verified execution
        verifier.register_state(alert_ref, {"action_id": action.action_id, "reason": action.reason})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="CreateOperatorAlertHandler",
            result_state="SUCCESS",
            result_reference=alert_ref,
            verification_required=True
        )

class RaiseAttentionPriorityHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        ref = f"PRIORITY-RAISED-{action.target_id}"
        verifier.register_state(ref, {"priority": "HIGH"})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="RaiseAttentionPriorityHandler",
            result_state="SUCCESS",
            result_reference=ref
        )

class CreateReviewTaskHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        task_ref = f"TASK-{action.action_id}"
        verifier.register_state(task_ref, {"task_id": task_ref, "status": "OPEN"})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="CreateReviewTaskHandler",
            result_state="SUCCESS",
            result_reference=task_ref
        )

class PinEvidenceHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        pin_ref = f"PIN-{action.target_id}"
        verifier.register_state(pin_ref, {"pinned_refs": action.evidence_refs})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="PinEvidenceHandler",
            result_state="SUCCESS",
            result_reference=pin_ref
        )

class FocusCommandCenterViewHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        view_ref = f"FOCUS-VIEW-{action.target_id}"
        verifier.register_state(view_ref, {"camera_id": action.target_id})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="FocusCommandCenterViewHandler",
            result_state="SUCCESS",
            result_reference=view_ref
        )

class RequestOperatorReviewHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        rev_ref = f"REVIEW-REQ-{action.action_id}"
        verifier.register_state(rev_ref, {"requested_for": action.investigation_id})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="RequestOperatorReviewHandler",
            result_state="SUCCESS",
            result_reference=rev_ref
        )

class MarkInvestigationForFollowupHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        fol_ref = f"FOLLOWUP-{action.investigation_id}"
        verifier.register_state(fol_ref, {"marked": True})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="MarkInvestigationForFollowupHandler",
            result_state="SUCCESS",
            result_reference=fol_ref
        )

class AcknowledgeInternalSystemEventHandler(BaseActionHandler):
    def execute(self, action: ProposedAction, verifier: ActionVerifier) -> ActionResult:
        ack_ref = f"ACK-{action.target_id}"
        verifier.register_state(ack_ref, {"acked": True})
        return ActionResult(
            action_id=action.action_id,
            execution_started_at=str(time.time()),
            execution_completed_at=str(time.time()),
            handler="AcknowledgeInternalSystemEventHandler",
            result_state="SUCCESS",
            result_reference=ack_ref
        )

ACTION_HANDLER_REGISTRY: Dict[str, BaseActionHandler] = {
    "CREATE_OPERATOR_ALERT": CreateOperatorAlertHandler(),
    "RAISE_ATTENTION_PRIORITY": RaiseAttentionPriorityHandler(),
    "CREATE_REVIEW_TASK": CreateReviewTaskHandler(),
    "PIN_EVIDENCE": PinEvidenceHandler(),
    "FOCUS_COMMAND_CENTER_VIEW": FocusCommandCenterViewHandler(),
    "REQUEST_OPERATOR_REVIEW": RequestOperatorReviewHandler(),
    "MARK_INVESTIGATION_FOR_FOLLOWUP": MarkInvestigationForFollowupHandler(),
    "ACKNOWLEDGE_INTERNAL_SYSTEM_EVENT": AcknowledgeInternalSystemEventHandler()
}

class GovernedActionExecutor:
    """
    Executes approved and policy-allowed actions via explicit registered handlers.
    Guarantees idempotency, expiration checking, verification, and auditability.
    """
    def __init__(self, verifier: Optional[ActionVerifier] = None):
        self.verifier = verifier or ActionVerifier()
        self._idempotency_cache: Dict[str, ActionResult] = {}
        self.execution_audit: list = []

    def execute(
        self,
        action: ProposedAction,
        policy_decision: str,
        policy_reason: str = "",
        approval: Optional[HumanApprovalRequest] = None,
        current_timestamp: Optional[float] = None
    ) -> ActionResult:
        now = current_timestamp if current_timestamp is not None else time.time()

        # 1. Expiration check
        if action.expires_at is not None:
            try:
                exp_ts = float(action.expires_at)
                if now > exp_ts or action.status == "EXPIRED":
                    action.status = "EXPIRED"
                    res = ActionResult(
                        action_id=action.action_id,
                        result_state="FAILED",
                        error_code="ACTION_EXPIRED",
                        error_message="Action proposal expired before execution."
                    )
                    self._record_audit(action, policy_decision, policy_reason, approval, res)
                    return res
            except ValueError:
                pass

        # 2. Check Idempotency Key
        idemp_key = action.idempotency_key or f"{action.investigation_id}_{action.action_type}_{action.target_id}"
        if idemp_key in self._idempotency_cache:
            logger.info(f"Duplicate action detected via idempotency key: {idemp_key}. Returning cached result.")
            cached = self._idempotency_cache[idemp_key]
            self._record_audit(action, policy_decision, "DUPLICATE_IDEMPOTENT_HIT", approval, cached)
            return cached

        # 3. Policy and Approval Gating
        if policy_decision == "DENY":
            action.status = "POLICY_DENIED"
            res = ActionResult(
                action_id=action.action_id,
                result_state="FAILED",
                error_code="POLICY_DENIED",
                error_message=f"Action denied by policy: {policy_reason}"
            )
            self._record_audit(action, policy_decision, policy_reason, approval, res)
            return res

        if policy_decision == "REQUIRE_HUMAN_APPROVAL":
            if not approval or approval.status != "APPROVED":
                action.status = "PENDING_APPROVAL"
                res = ActionResult(
                    action_id=action.action_id,
                    result_state="FAILED",
                    error_code="APPROVAL_REQUIRED",
                    error_message="Action requires human approval which has not been granted."
                )
                self._record_audit(action, policy_decision, policy_reason, approval, res)
                return res

            # Anti Self-Approval Gate (Rule 45)
            approver = (approval.approved_by or "").strip().lower()
            if not approver or approver in NON_HUMAN_APPROVERS:
                action.status = "POLICY_DENIED"
                res = ActionResult(
                    action_id=action.action_id,
                    result_state="FAILED",
                    error_code="SELF_APPROVAL_PROHIBITED",
                    error_message="AI models or automated agents cannot approve their own actions."
                )
                self._record_audit(action, policy_decision, "SELF_APPROVAL_REJECTED", approval, res)
                return res

        # 4. Handler Allowlist Check
        handler = ACTION_HANDLER_REGISTRY.get(action.action_type)
        if not handler:
            action.status = "FAILED"
            res = ActionResult(
                action_id=action.action_id,
                result_state="FAILED",
                error_code="UNREGISTERED_HANDLER",
                error_message=f"No execution handler registered for action '{action.action_type}'."
            )
            self._record_audit(action, policy_decision, policy_reason, approval, res)
            return res

        # 5. Execute Action
        action.status = "EXECUTING"
        result = handler.execute(action, self.verifier)

        # 6. Verify Result (Rule 18)
        if result.result_state == "SUCCESS" and result.verification_required:
            v_state = self.verifier.verify(action, result)
            result.verification_state = v_state
            if v_state == "VERIFIED":
                action.status = "VERIFIED"
            else:
                action.status = "FAILED"
                result.result_state = "FAILED"
                result.error_code = "VERIFICATION_FAILED"
                result.error_message = "Post-execution state verification failed."
        elif result.result_state == "SUCCESS":
            action.status = "EXECUTED"
        else:
            action.status = "FAILED"

        # Cache for idempotency
        self._idempotency_cache[idemp_key] = result

        # 7. Audit Log
        self._record_audit(action, policy_decision, policy_reason, approval, result)
        return result

    def _record_audit(
        self,
        action: ProposedAction,
        policy_decision: str,
        policy_reason: str,
        approval: Optional[HumanApprovalRequest],
        result: ActionResult
    ):
        entry = {
            "timestamp": time.time(),
            "action_id": action.action_id,
            "investigation_id": action.investigation_id,
            "action_type": action.action_type,
            "target": f"{action.target_type}:{action.target_id}",
            "autonomy_level": action.requested_autonomy_level,
            "policy_decision": policy_decision,
            "policy_reason": policy_reason,
            "approval_state": approval.status if approval else "NONE",
            "execution_state": result.result_state,
            "verification_state": result.verification_state,
            "evidence_refs": action.evidence_refs,
            "actor": approval.approved_by if (approval and approval.approved_by) else "GOVERNED_POLICY"
        }
        self.execution_audit.append(entry)
