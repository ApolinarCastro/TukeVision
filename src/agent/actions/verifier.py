import logging
from typing import Dict, Any, Optional
from src.agent.actions.contract import ProposedAction, ActionResult

logger = logging.getLogger("action_verifier")

class ActionVerifier:
    """
    Verifies that the executed action actually produced the expected operational state.
    """
    def __init__(self):
        self._state_registry: Dict[str, Any] = {}

    def register_state(self, key: str, value: Any):
        self._state_registry[key] = value

    def clear_state(self, key: str):
        self._state_registry.pop(key, None)

    def verify(self, action: ProposedAction, result: ActionResult) -> str:
        """
        Returns 'VERIFIED' or 'VERIFICATION_FAILED'.
        """
        if result.result_state != "SUCCESS":
            return "VERIFICATION_FAILED"

        # Verification rule based on action type
        if action.action_type == "CREATE_OPERATOR_ALERT":
            alert_id = result.result_reference
            if alert_id in self._state_registry:
                return "VERIFIED"
            return "VERIFICATION_FAILED"

        elif action.action_type == "CREATE_REVIEW_TASK":
            task_id = result.result_reference
            if task_id in self._state_registry:
                return "VERIFIED"
            return "VERIFICATION_FAILED"

        elif action.action_type == "PIN_EVIDENCE":
            pin_id = result.result_reference
            if pin_id in self._state_registry:
                return "VERIFIED"
            return "VERIFICATION_FAILED"

        elif action.action_type in (
            "RAISE_ATTENTION_PRIORITY",
            "FOCUS_COMMAND_CENTER_VIEW",
            "REQUEST_OPERATOR_REVIEW",
            "MARK_INVESTIGATION_FOR_FOLLOWUP",
            "ACKNOWLEDGE_INTERNAL_SYSTEM_EVENT"
        ):
            if result.result_reference and result.result_reference != "UNKNOWN":
                return "VERIFIED"
            return "VERIFICATION_FAILED"

        return "VERIFICATION_FAILED"
