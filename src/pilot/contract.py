from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Roles
ROLE_VIEWER = "VIEWER"
ROLE_OPERATOR = "OPERATOR"
ROLE_SUPERVISOR = "SUPERVISOR"
ROLE_ADMIN = "ADMIN"

VALID_ROLES = {ROLE_VIEWER, ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN}

# Allowed Use Case Categories
ALLOWED_USE_CASE_CATEGORIES = {
    "ZONE_ACTIVITY",
    "PROLONGED_PRESENCE",
    "CROSS_CAMERA_CONTINUITY",
    "OPERATIONAL_FLOW",
    "SOURCE_HEALTH_EVENT",
    "OPERATOR_REVIEW_REQUIRED"
}

@dataclass
class PilotSite:
    pilot_id: str
    site_id: str
    site_name: str
    site_type: str = "RETAIL"
    timezone: str = "UTC"
    operational_schedule: Dict[str, Any] = field(default_factory=dict)
    camera_ids: List[str] = field(default_factory=list)
    zone_ids: List[str] = field(default_factory=list)
    enabled_use_cases: List[str] = field(default_factory=list)
    operator_roles: Dict[str, str] = field(default_factory=dict)  # operator_id -> role
    privacy_policy_ref: str = "POL-PRIVACY-DEFAULT"
    retention_policy_ref: str = "POL-RETENTION-DEFAULT"
    configuration_version: str = "1.0.0"
    created_at: str = "UNKNOWN"
    updated_at: str = "UNKNOWN"
    status: str = "DRAFT"  # DRAFT, CONFIGURED, VALIDATED, ACTIVE, PAUSED, COMPLETED

@dataclass
class PilotUseCase:
    use_case_id: str
    name: str
    description: str
    enabled: bool = True
    category: str = "ZONE_ACTIVITY"
    required_cameras: List[str] = field(default_factory=list)
    required_zones: List[str] = field(default_factory=list)
    situation_types: List[str] = field(default_factory=list)
    operator_response: str = "REVIEW"
    success_metrics: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    status: str = "ACTIVE"

@dataclass
class OperationalRuleProfile:
    rule_id: str
    site_id: str
    zone_id: str
    situation_type: str
    duration_seconds: float = 60.0
    schedule: str = "08:00-22:00"
    priority: str = "NORMAL"
    operator_response: str = "ALERT"
    enabled: bool = True

@dataclass
class OperatorSession:
    session_id: str
    operator_id: str
    role: str
    session_start: str
    session_end: Optional[str] = None
    actions_performed: List[str] = field(default_factory=list)
    reviews_performed: List[str] = field(default_factory=list)
    approvals_performed: List[str] = field(default_factory=list)

@dataclass
class PilotMetrics:
    # System Metrics
    cameras_expected: int = 15
    cameras_available: int = 15
    frame_freshness_ms: float = 24.5
    inference_latency_ms: float = 38.0
    reasoning_latency_ms: float = 350.0
    resource_consumption: Dict[str, Any] = field(default_factory=dict)
    recovery_events: int = 0

    # Operational Metrics
    situations_generated: int = 0
    investigations_generated: int = 0
    operator_reviews: int = 0
    actions_proposed: int = 0
    actions_executed: int = 0
    actions_verified: int = 0
    duplicate_suppression: int = 0

    # Quality Metrics
    operator_useful: int = 0
    operator_not_useful: int = 0
    false_positive: int = 0
    unknown_feedback: int = 0

@dataclass
class PilotSession:
    session_id: str
    pilot_id: str
    started_at: str
    configuration_version: str
    configuration_hash: str
    cameras_expected: int = 15
    cameras_available: int = 15
    enabled_use_cases: List[str] = field(default_factory=list)
    operator_refs: List[str] = field(default_factory=list)
    metrics_reference: str = "METRICS-INIT"
    ended_at: Optional[str] = None
    status: str = "STARTING"  # STARTING, ACTIVE, DEGRADED, COMPLETED, FAILED

@dataclass
class PilotReport:
    report_id: str
    site_id: str
    session_id: str
    configuration_version: str
    duration_seconds: float
    camera_availability: float
    system_health: str
    situations_count: int
    investigations_count: int
    actions_executed_count: int
    operator_outcomes_count: int
    quality_summary: Dict[str, int]
    resource_summary: Dict[str, Any]
    recoveries_count: int
    known_limitations: List[str]
    open_defects: List[str]
    evidence_references: List[str]

@dataclass
class InferenceCoverageHealth:
    camera_id: str
    frames_received: int = 0
    inference_requests: int = 0
    inference_executed: int = 0
    last_inference_at: Optional[str] = None
    status: str = "HEALTHY"  # HEALTHY, ACTIVE_CAMERA_WITHOUT_INFERENCE, UNAVAILABLE

@dataclass
class UC001OperationalInputContract:
    site_id: str = "SITE-NICOPOLY-01"
    camera_inventory_ready: bool = True
    camera_zone_mapping_ready: bool = True
    operational_schedule_ready: bool = False  # Client input pending
    floor_zone_info_ready: bool = True
    use_cases_ready: bool = True
    operator_roles_ready: bool = True
    retention_policy_ready: bool = True
    thresholds_ready: bool = True
    status: str = "READY_WITH_MISSING_OPERATIONAL_INPUT"
