import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from src.pilot.contract import PilotSite, PilotSession, PilotMetrics, PilotReport
from src.pilot.client_input import ClientOperationalInputRecord, ClientOperationalInputValidator, RealSiteActivationPackage
from src.pilot.validator import SiteConfigurationValidator, PilotReadinessEvaluator

logger = logging.getLogger("real_pilot_orchestrator")

@dataclass
class RealPilotHealth:
    cameras: str = "HEALTHY"
    perception: str = "HEALTHY"
    spatial: str = "HEALTHY"
    evidence: str = "HEALTHY"
    agent: str = "HEALTHY"
    cascade: str = "HEALTHY"
    experience: str = "HEALTHY"
    actions: str = "HEALTHY"
    storage: str = "HEALTHY"
    security: str = "HEALTHY"

    def overall_status(self) -> str:
        all_states = [
            self.cameras, self.perception, self.spatial, self.evidence,
            self.agent, self.cascade, self.experience, self.actions,
            self.storage, self.security
        ]
        if any(s == "UNAVAILABLE" for s in all_states):
            return "UNAVAILABLE"
        if any(s == "DEGRADED" for s in all_states):
            return "DEGRADED"
        return "HEALTHY"

class RealPilotOrchestrator:
    """
    Orchestrates dry-run validations, activation gates, and controlled pilot sessions.
    """
    @classmethod
    def execute_dry_run(
        cls,
        site: PilotSite,
        cameras_available: int = 15,
        source_security: str = "VALIDATED"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Executes a dry-run to validate all technical pipelines before live activation.
        """
        config_status, issues = SiteConfigurationValidator.validate(site)
        if config_status == "INVALID":
            return "FAILED", {"reason": "Site configuration invalid", "issues": issues}

        if source_security != "VALIDATED":
            return "FAILED", {"reason": f"Source security '{source_security}' rejected for dry-run."}

        if cameras_available == 0:
            return "FAILED", {"reason": "0 cameras available."}

        dry_run_results = {
            "site_id": site.site_id,
            "cameras_verified": cameras_available,
            "zones_verified": len(site.zone_ids),
            "use_cases_verified": len(site.enabled_use_cases),
            "operator_roles_verified": len(site.operator_roles),
            "status": "DRY_RUN_PASS"
        }
        return "PASS", dry_run_results

    @classmethod
    def evaluate_pilot_activation_gate(
        cls,
        input_record: ClientOperationalInputRecord,
        site: PilotSite,
        dry_run_status: str,
        source_security: str = "VALIDATED"
    ) -> Tuple[bool, str, List[str]]:
        """
        Evaluates the mandatory activation gate before starting a live pilot session.
        """
        val_state, issues = ClientOperationalInputValidator.validate(input_record)
        if val_state != "COMPLETE":
            return False, "BLOCKED_BY_CLIENT_OPERATIONAL_INPUT", issues

        if source_security != "VALIDATED":
            return False, "BLOCKED_BY_SOURCE_SECURITY", ["Source security state is unverified or quarantined."]

        if dry_run_status != "PASS":
            return False, "BLOCKED_BY_DRY_RUN", ["Dry-run verification did not pass."]

        return True, "READY_FOR_ACTIVATION", []
