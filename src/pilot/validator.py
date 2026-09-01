import re
import logging
from typing import Dict, Any, Tuple, List, Optional
from src.pilot.contract import PilotSite, VALID_ROLES

logger = logging.getLogger("site_configuration_validator")

SECRET_PATTERNS = [
    re.compile(r"password\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE),
    re.compile(r"rtsp://[^:]+:[^@]+@", re.IGNORECASE),
    re.compile(r"api_key\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE),
    re.compile(r"secret\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE)
]

class SiteConfigurationValidator:
    """
    Validates site configuration, enforcing structural integrity and strict secret protection.
    """
    @classmethod
    def validate_secrets(cls, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Recursively scans strings and structures for plaintext secrets.
        Returns (is_clean, failure_reason).
        """
        if isinstance(data, str):
            for pat in SECRET_PATTERNS:
                if pat.search(data):
                    return False, f"Plaintext secret or credential pattern matched: '{pat.pattern}'"
        elif isinstance(data, dict):
            for k, v in data.items():
                if any(sec in str(k).lower() for sec in ["password", "secret", "token", "apikey"]):
                    if v and not str(v).startswith("ENV_") and not str(v).startswith("SEC_REF_"):
                        return False, f"Plaintext secret found in field '{k}'"
                clean, reason = cls.validate_secrets(v)
                if not clean:
                    return False, reason
        elif isinstance(data, list):
            for item in data:
                clean, reason = cls.validate_secrets(item)
                if not clean:
                    return False, reason
        return True, None

    @classmethod
    def validate(cls, site: PilotSite) -> Tuple[str, List[str]]:
        """
        Validates site configuration.
        Returns (STATUS, issues) where STATUS is VALID, VALID_WITH_WARNINGS, or INVALID.
        """
        issues: List[str] = []
        warnings: List[str] = []

        # 1. Secret Protection check
        clean, reason = cls.validate_secrets(site.__dict__)
        if not clean:
            issues.append(f"SECRET_POLICY_VIOLATION: {reason}")
            return "INVALID", issues

        # 2. Camera references
        if not site.camera_ids:
            issues.append("MISSING_CAMERAS: Site configuration has no camera IDs defined.")
        
        # 3. Zone references
        if not site.zone_ids:
            warnings.append("EMPTY_ZONES: No specific zones defined for site.")

        # 4. Operator roles
        for op_id, role in site.operator_roles.items():
            if role not in VALID_ROLES:
                issues.append(f"INVALID_ROLE: Operator '{op_id}' assigned unrecognized role '{role}'.")

        # 5. Operational schedule
        if not site.operational_schedule:
            warnings.append("SCHEDULE_NOT_CONFIGURED: Default 24/7 schedule will be assumed.")

        if issues:
            return "INVALID", issues
        if warnings:
            return "VALID_WITH_WARNINGS", warnings
        return "VALID", []

class PilotReadinessEvaluator:
    """
    Evaluates global readiness before starting a PilotSession.
    """
    @classmethod
    def evaluate_readiness(
        cls,
        site: PilotSite,
        cameras_available: int,
        cameras_expected: int = 15,
        source_security: str = "VALIDATED",
        action_execution_enabled: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        status, issues = SiteConfigurationValidator.validate(site)
        report = {
            "site_id": site.site_id,
            "config_status": status,
            "cameras_available": cameras_available,
            "cameras_expected": cameras_expected,
            "source_security": source_security,
            "action_execution_enabled": action_execution_enabled,
            "issues": issues
        }

        if status == "INVALID" or source_security == "UNTRUSTED" or cameras_available == 0:
            return "NOT_READY", report

        if cameras_available < cameras_expected or status == "VALID_WITH_WARNINGS":
            return "READY_WITH_WARNINGS", report

        return "READY", report
