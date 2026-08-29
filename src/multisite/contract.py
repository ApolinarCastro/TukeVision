"""Phase 11: Sustained Production & Repeatable Multisite Readiness Contracts.

Defines schemas for multisite isolation, repeatable deployment packages,
deployment validation, maintenance windows, upgrades, backups, and drift detection.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Profile & Deployment States
DEPLOYMENT_STATUS_DRAFT = "DRAFT"
DEPLOYMENT_STATUS_VALIDATED = "VALIDATED"
DEPLOYMENT_STATUS_READY = "READY"
DEPLOYMENT_STATUS_ACTIVE = "ACTIVE"
DEPLOYMENT_STATUS_DEGRADED = "DEGRADED"
DEPLOYMENT_STATUS_PAUSED = "PAUSED"
DEPLOYMENT_STATUS_RETIRED = "RETIRED"
DEPLOYMENT_STATUS_FAILED = "FAILED"

# Maintenance States
MAINTENANCE_STATUS_PLANNED = "PLANNED"
MAINTENANCE_STATUS_APPROVED = "APPROVED"
MAINTENANCE_STATUS_ACTIVE = "ACTIVE"
MAINTENANCE_STATUS_COMPLETED = "COMPLETED"
MAINTENANCE_STATUS_ROLLED_BACK = "ROLLED_BACK"
MAINTENANCE_STATUS_FAILED = "FAILED"
MAINTENANCE_STATUS_CANCELLED = "CANCELLED"

# Upgrade States
UPGRADE_STATUS_PROPOSED = "PROPOSED"
UPGRADE_STATUS_VALIDATED = "VALIDATED"
UPGRADE_STATUS_APPLYING = "APPLYING"
UPGRADE_STATUS_APPLIED = "APPLIED"
UPGRADE_STATUS_VERIFIED = "VERIFIED"
UPGRADE_STATUS_ROLLED_BACK = "ROLLED_BACK"
UPGRADE_STATUS_FAILED = "FAILED"

# Drift States
DRIFT_STATUS_IN_SYNC = "IN_SYNC"
DRIFT_STATUS_DRIFT_DETECTED = "DRIFT_DETECTED"
DRIFT_STATUS_UNKNOWN = "UNKNOWN"

# Validation Results
VALIDATION_RESULT_VALID = "VALID"
VALIDATION_RESULT_VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
VALIDATION_RESULT_INVALID = "INVALID"


@dataclass
class SiteDeploymentProfile:
    """Deployment profile for a specific site instance."""
    deployment_id: str
    site_id: str
    site_name: str
    site_type: str  # e.g., "RETAIL_STORE", "DISTRIBUTION_CENTER", "LOGICAL_TEST"
    production_profile_ref: str
    configuration_version: str
    configuration_hash: str
    camera_ids: List[str]
    zone_ids: List[str]
    use_case_ids: List[str]
    operator_roles: Dict[str, List[str]]
    retention_policy_ref: str
    privacy_policy_ref: str
    security_policy_ref: str
    action_policy_ref: str
    storage_profile_ref: str
    recovery_profile_ref: str
    software_version: str = "3.10.0"
    model_runtime_version: str = "openvino-2024.1"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activated_at: Optional[str] = None
    status: str = DEPLOYMENT_STATUS_DRAFT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        data = {
            "site_id": self.site_id,
            "site_type": self.site_type,
            "configuration_version": self.configuration_version,
            "camera_ids": sorted(self.camera_ids),
            "zone_ids": sorted(self.zone_ids),
            "use_case_ids": sorted(self.use_case_ids),
            "retention_policy_ref": self.retention_policy_ref,
            "privacy_policy_ref": self.privacy_policy_ref,
            "security_policy_ref": self.security_policy_ref,
            "action_policy_ref": self.action_policy_ref,
        }
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class RepeatableDeploymentPackage:
    """Repeatable, secret-free deployment package for provisioning or cloning sites."""
    package_id: str
    schema_version: str
    software_version: str
    site_configuration: Dict[str, Any]
    camera_definitions: List[Dict[str, Any]]
    zones: List[Dict[str, Any]]
    calibration_refs: Dict[str, str]
    rules: List[Dict[str, Any]]
    roles: Dict[str, List[str]]
    retention: Dict[str, Any]
    privacy: Dict[str, Any]
    security: Dict[str, Any]
    action_policy: Dict[str, Any]
    health_configuration: Dict[str, Any]
    recovery_configuration: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    package_hash: str = ""

    def __post_init__(self):
        if not self.package_hash:
            raw = json.dumps({
                "schema_version": self.schema_version,
                "software_version": self.software_version,
                "site_configuration": self.site_configuration,
                "camera_definitions": self.camera_definitions,
                "zones": self.zones,
                "rules": self.rules,
            }, sort_keys=True)
            self.package_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class SiteTemplate:
    """Reusable blueprint with safe defaults for instantiating new sites."""
    template_id: str
    site_type: str
    schema_version: str
    default_retention_days: int = 30
    default_max_cameras: int = 32
    default_privacy_level: str = "MAXIMUM_ANONYMIZATION"
    default_action_policy: str = "DEFAULT_DENY"
    allowed_use_cases: List[str] = field(default_factory=lambda: ["SAFETY", "QUEUE", "INTRUSION"])
    required_fields: List[str] = field(default_factory=lambda: [
        "site_id", "site_name", "cameras", "zones"
    ])


@dataclass
class MultiSiteHealth:
    """Aggregated health status across multiple site deployments."""
    checked_at: str
    sites: Dict[str, Dict[str, str]] = field(default_factory=dict)
    overall_status: str = "HEALTHY"

    def record_site_health(self, site_id: str, component_health: Dict[str, str]) -> None:
        self.sites[site_id] = component_health
        # Recalculate overall health
        has_unavailable = any(
            status == "UNAVAILABLE" for comp in self.sites.values() for status in comp.values()
        )
        has_degraded = any(
            status == "DEGRADED" for comp in self.sites.values() for status in comp.values()
        )
        if has_unavailable:
            self.overall_status = "DEGRADED"
        elif has_degraded:
            self.overall_status = "DEGRADED"
        else:
            self.overall_status = "HEALTHY"


@dataclass
class SiteResourceBudget:
    """Resource budget to enforce fair CPU/Inference allocation across sites."""
    site_id: str
    camera_count: int
    inference_budget_fps: float = 30.0
    reasoning_budget_req_per_min: int = 60
    queue_limits: int = 100
    priority: int = 1  # 1 = Standard, 2 = High


@dataclass
class MaintenanceWindow:
    """Controlled maintenance window descriptor."""
    maintenance_id: str
    site_ids: List[str]
    reason: str
    requested_by: str
    approved_by: str
    planned_start: str
    planned_end: str
    affected_components: List[str]
    rollback_ref: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    status: str = MAINTENANCE_STATUS_PLANNED


@dataclass
class UpgradeRecord:
    """Versioned upgrade record for tracking software/schema transitions."""
    upgrade_id: str
    from_version: str
    to_version: str
    site_ids: List[str]
    precheck_ref: str
    migration_ref: str
    validation_ref: str
    rollback_ref: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    status: str = UPGRADE_STATUS_PROPOSED


@dataclass
class BackupManifest:
    """Cryptographically verifiable backup manifest for disaster recovery."""
    backup_id: str
    site_ids: List[str]
    created_at: str
    software_version: str
    schema_version: str
    configuration_hash: str
    included_stores: List[str]
    excluded_secrets: List[str]
    hashes: Dict[str, str] = field(default_factory=dict)
    status: str = "VALIDATED"


@dataclass
class ConfigurationDriftState:
    """Status representing difference between expected configuration and active runtime."""
    site_id: str
    expected_hash: str
    active_hash: str
    status: str = DRIFT_STATUS_IN_SYNC
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    discrepancies: List[str] = field(default_factory=list)
