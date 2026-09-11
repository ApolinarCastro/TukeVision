import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from src.pilot.contract import VALID_ROLES, ALLOWED_USE_CASE_CATEGORIES
from src.pilot.validator import SiteConfigurationValidator

logger = logging.getLogger("client_operational_input")

REQUIRED_INPUT_FIELDS = [
    "site_id",
    "camera_inventory_ref",
    "camera_zone_mapping_ref",
    "schedule_ref",
    "zone_ref",
    "use_case_ref",
    "operator_role_ref",
    "retention_ref",
    "rule_ref"
]

@dataclass
class ClientOperationalInputRecord:
    input_id: str
    pilot_id: str
    site_id: str
    source: str = "CLIENT_PORTAL"
    received_at: str = "UNKNOWN"
    camera_inventory_ref: Optional[str] = None
    camera_zone_mapping_ref: Optional[str] = None
    schedule_ref: Optional[str] = None
    zone_ref: Optional[str] = None
    use_case_ref: Optional[str] = None
    operator_role_ref: Optional[str] = None
    retention_ref: Optional[str] = None
    rule_ref: Optional[str] = None
    validation_state: str = "INCOMPLETE"  # COMPLETE, INCOMPLETE, INVALID, VALID_WITH_WARNINGS
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    hash: str = "UNKNOWN"

class ClientOperationalInputValidator:
    """
    Validates client operational input packages, strictly enforcing completeness,
    structural integrity, and secret protection without assuming missing fields.
    """
    @classmethod
    def validate(cls, record: ClientOperationalInputRecord, raw_data: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
        missing: List[str] = []
        issues: List[str] = []

        # 1. Secret Protection Scan
        if raw_data:
            clean, sec_reason = SiteConfigurationValidator.validate_secrets(raw_data)
            if not clean:
                issues.append(f"SECRET_POLICY_VIOLATION: {sec_reason}")
                record.validation_state = "INVALID"
                return "INVALID", issues

        # 2. Required Fields Check (Fail-Closed)
        for req in REQUIRED_INPUT_FIELDS:
            val = getattr(record, req, None)
            if not val or val == "MISSING" or val == "UNKNOWN":
                missing.append(req)

        record.missing_fields = missing
        if missing:
            record.validation_state = "INCOMPLETE"
            return "INCOMPLETE", [f"MISSING_REQUIRED_INPUT: {f}" for f in missing]

        # 3. Compute Hash for Inmutable Audit
        content_repr = f"{record.site_id}:{record.camera_inventory_ref}:{record.schedule_ref}:{record.rule_ref}"
        record.hash = hashlib.sha256(content_repr.encode("utf-8")).hexdigest()[:16]
        record.validation_state = "COMPLETE"
        return "COMPLETE", []

@dataclass
class RealSiteActivationPackage:
    package_id: str
    site_id: str
    pilot_id: str
    input_hash: str
    configuration_version: str = "1.0.0-PROD"
    configuration_hash: str = "UNKNOWN"
    created_at: str = "UNKNOWN"
    status: str = "PREPARED"  # PREPARED, ACTIVE, PAUSED, REVOKED
