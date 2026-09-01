import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# Production Profile Statuses
PROD_STATUS_DRAFT = "DRAFT"
PROD_STATUS_READY = "READY"
PROD_STATUS_ACTIVE = "ACTIVE"
PROD_STATUS_DEGRADED = "DEGRADED"
PROD_STATUS_SAFE_MODE = "SAFE_MODE"
PROD_STATUS_PAUSED = "PAUSED"
PROD_STATUS_STOPPED = "STOPPED"
PROD_STATUS_FAILED = "FAILED"

# Promotion Statuses
PROMO_STATUS_PROPOSED = "PROPOSED"
PROMO_STATUS_VALIDATED = "VALIDATED"
PROMO_STATUS_PROMOTED = "PROMOTED"
PROMO_STATUS_REJECTED = "REJECTED"
PROMO_STATUS_ROLLED_BACK = "ROLLED_BACK"

# Change Record Statuses
CHANGE_STATUS_PROPOSED = "PROPOSED"
CHANGE_STATUS_VALIDATED = "VALIDATED"
CHANGE_STATUS_APPLIED = "APPLIED"
CHANGE_STATUS_REJECTED = "REJECTED"
CHANGE_STATUS_ROLLED_BACK = "ROLLED_BACK"
CHANGE_STATUS_FAILED = "FAILED"

# Health States
HEALTH_HEALTHY = "HEALTHY"
HEALTH_DEGRADED = "DEGRADED"
HEALTH_UNAVAILABLE = "UNAVAILABLE"
HEALTH_UNKNOWN = "UNKNOWN"

# Incident Severities
SEVERITY_INFO = "INFO"
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

# Incident Statuses
INCIDENT_OPEN = "OPEN"
INCIDENT_INVESTIGATING = "INVESTIGATING"
INCIDENT_MITIGATED = "MITIGATED"
INCIDENT_RESOLVED = "RESOLVED"
INCIDENT_KNOWN_LIMITATION = "KNOWN_LIMITATION"

@dataclass
class ProductionProfile:
    production_id: str
    site_id: str
    pilot_origin_id: str
    configuration_version: str = "1.0.0-PROD"
    configuration_hash: str = "UNKNOWN"
    enabled_at: str = "UNKNOWN"
    operational_schedule: Dict[str, Any] = field(default_factory=lambda: {"hours": "08:00-22:00"})
    camera_ids: List[str] = field(default_factory=list)
    zone_ids: List[str] = field(default_factory=list)
    enabled_use_cases: List[str] = field(default_factory=list)
    operator_roles: Dict[str, str] = field(default_factory=dict)
    retention_policy_ref: str = "POLICY-RET-PROD-30D"
    privacy_policy_ref: str = "POLICY-PRIVACY-PROD-NO-BIOMETRIC"
    security_policy_ref: str = "POLICY-SEC-PROD-DEF-DENY"
    action_policy_ref: str = "POLICY-ACTION-PROD-AUTONOMY2"
    recovery_policy_ref: str = "POLICY-RECOVERY-PROD-ISOLATED"
    status: str = PROD_STATUS_READY

@dataclass
class ProductionPromotionRecord:
    promotion_id: str
    source_phase: str = "PHASE_9"
    source_commit: str = "533284a0184a0df74a197aa86fd1ebf85f1ea897"
    source_tag: str = "v3-phase9-real-pilot-active-stable-20260829"
    site_id: str = ""
    configuration_hash: str = "UNKNOWN"
    promoted_at: str = "UNKNOWN"
    promoted_by: str = "ADMIN_PROMOTION_GATE"
    validation_refs: List[str] = field(default_factory=list)
    status: str = PROMO_STATUS_PROPOSED

@dataclass
class ProductionChangeRecord:
    change_id: str
    production_id: str
    change_type: str  # e.g., THRESHOLD_ADJUSTMENT, SCHEDULE_ADJUSTMENT, ROLE_CHANGE
    requested_by: str
    reason: str
    before_hash: str
    after_hash: str
    risk_class: str = "LOW"
    validation_refs: List[str] = field(default_factory=list)
    applied_at: str = "UNKNOWN"
    rollback_ref: Optional[str] = None
    status: str = CHANGE_STATUS_PROPOSED

@dataclass
class ProductionHealth:
    cameras: str = HEALTH_HEALTHY
    ingestion: str = HEALTH_HEALTHY
    perception: str = HEALTH_HEALTHY
    tracking: str = HEALTH_HEALTHY
    spatial: str = HEALTH_HEALTHY
    evidence: str = HEALTH_HEALTHY
    agent: str = HEALTH_HEALTHY
    cascade: str = HEALTH_HEALTHY
    experience: str = HEALTH_HEALTHY
    actions: str = HEALTH_HEALTHY
    storage: str = HEALTH_HEALTHY
    security: str = HEALTH_HEALTHY
    operators: str = HEALTH_HEALTHY

    def overall_status(self) -> str:
        all_states = [
            self.cameras, self.ingestion, self.perception, self.tracking,
            self.spatial, self.evidence, self.agent, self.cascade,
            self.experience, self.actions, self.storage, self.security,
            self.operators
        ]
        if any(s == HEALTH_UNAVAILABLE for s in all_states):
            return HEALTH_UNAVAILABLE
        if any(s == HEALTH_DEGRADED for s in all_states):
            return HEALTH_DEGRADED
        return HEALTH_HEALTHY

@dataclass
class ProductionIncident:
    incident_id: str
    production_id: str
    component: str
    severity: str  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    detected_at: str
    symptoms: str
    evidence_refs: List[str] = field(default_factory=list)
    impact: str = "LOCAL_ISOLATED"
    root_cause: str = "INVESTIGATING"
    resolution: str = "PENDING"
    recovery_ref: Optional[str] = None
    closed_at: Optional[str] = None
    status: str = INCIDENT_OPEN

@dataclass
class RecoveryPlan:
    component: str
    failure_condition: str
    detection: str
    safe_state: str
    recovery_action: str
    maximum_attempts: int = 3
    escalation: str = "NOTIFY_OPERATOR_AND_DEGRADE"
    verification: str = "FUNCTIONAL_CHECK_PASS"

@dataclass
class ProductionWindow:
    window_id: str
    production_id: str
    configuration_hash: str
    started_at: str
    ended_at: Optional[str] = None
    cameras_expected: int = 15
    operators: List[str] = field(default_factory=list)
    status: str = "ACTIVE"
    metrics_ref: Optional[str] = None

@dataclass
class ProductionOperationsSummary:
    period_start: str
    period_end: str
    health: str
    camera_availability: float
    incidents: int
    recoveries: int
    situations: int
    investigations: int
    actions: int
    operator_outcomes: int
    resource_summary: Dict[str, Any] = field(default_factory=dict)
    open_issues: List[str] = field(default_factory=list)
