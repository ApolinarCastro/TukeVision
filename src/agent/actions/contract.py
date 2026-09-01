from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Autonomy Levels
AUTONOMY_0 = "AUTONOMY_0"  # OBSERVE
AUTONOMY_1 = "AUTONOMY_1"  # INVESTIGATE
AUTONOMY_2 = "AUTONOMY_2"  # LIMITED_ACTION
AUTONOMY_3 = "AUTONOMY_3"  # SENSITIVE_ACTION (DISABLED in Phase 7)

# Allowed Actions in Phase 7
ALLOWED_ACTION_TYPES = {
    "CREATE_OPERATOR_ALERT",
    "RAISE_ATTENTION_PRIORITY",
    "CREATE_REVIEW_TASK",
    "PIN_EVIDENCE",
    "FOCUS_COMMAND_CENTER_VIEW",
    "REQUEST_OPERATOR_REVIEW",
    "MARK_INVESTIGATION_FOR_FOLLOWUP",
    "ACKNOWLEDGE_INTERNAL_SYSTEM_EVENT"
}

# Explicitly Forbidden Actions
FORBIDDEN_ACTION_TYPES = {
    "door_unlock", "door_lock",
    "alarm_activation", "alarm_deactivation",
    "camera_configuration_change", "ptz_control",
    "speaker_audio_command", "contact_police",
    "contact_security_company", "contact_emergency",
    "email_external", "sms", "whatsapp",
    "pos_modification", "inventory_modification",
    "employee_sanction", "access_control_modification",
    "network_configuration", "firewall_modification",
    "shell_execution", "filesystem_write_arbitrary",
    "database_admin_operation", "camera_credential_change",
    "automatic_code_modification", "automatic_model_modification"
}

@dataclass
class ProposedAction:
    action_id: str
    investigation_id: str
    situation_id: str
    action_type: str
    target_type: str
    target_id: str
    reason: str
    supporting_fact_refs: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    requested_autonomy_level: str = AUTONOMY_2
    risk_class: str = "LOW"  # LOW, MEDIUM, HIGH, SENSITIVE
    proposed_at: str = "UNKNOWN"
    expires_at: Optional[str] = None
    idempotency_key: Optional[str] = None
    status: str = "PROPOSED"  # PROPOSED, POLICY_DENIED, PENDING_APPROVAL, APPROVED, REJECTED, EXECUTING, EXECUTED, VERIFIED, FAILED, EXPIRED, CANCELLED

@dataclass
class HumanApprovalRequest:
    approval_id: str
    action_id: str
    requested_at: str
    action_summary: str
    reason: str
    evidence_refs: List[str] = field(default_factory=list)
    risk_class: str = "LOW"
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED, CANCELLED
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[str] = None

@dataclass
class ActionResult:
    action_id: str
    execution_started_at: str = "UNKNOWN"
    execution_completed_at: str = "UNKNOWN"
    handler: str = "UNKNOWN"
    result_state: str = "UNKNOWN"  # SUCCESS, FAILED, PARTIAL, CANCELLED
    result_reference: str = "UNKNOWN"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    verification_required: bool = True
    verification_state: str = "UNVERIFIED"  # UNVERIFIED, VERIFIED, VERIFICATION_FAILED
