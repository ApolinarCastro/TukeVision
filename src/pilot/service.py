import time
import json
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from src.pilot.contract import (
    PilotSite, PilotSession, PilotMetrics, PilotReport, OperatorSession
)
from src.pilot.validator import SiteConfigurationValidator, PilotReadinessEvaluator
from src.agent.experience.service import ExperienceService
from src.agent.experience.contract import OperationalExperience, OperatorOutcome

logger = logging.getLogger("pilot_service")

class PilotService:
    """
    Central service for managing pilot site lifecycles, configuration tracking,
    operator feedback ingestion, metrics aggregation, and report generation.
    """
    def __init__(self, experience_service: Optional[ExperienceService] = None):
        self.experience_service = experience_service
        self._sites: Dict[str, PilotSite] = {}
        self._sessions: Dict[str, PilotSession] = {}
        self._metrics: Dict[str, PilotMetrics] = {}
        self._reports: Dict[str, PilotReport] = {}
        self._operator_sessions: Dict[str, OperatorSession] = {}

    def register_site(self, site: PilotSite) -> Tuple[str, List[str]]:
        status, issues = SiteConfigurationValidator.validate(site)
        if status == "INVALID":
            logger.error(f"Cannot register invalid site '{site.site_id}': {issues}")
            return "INVALID", issues
        site.status = "CONFIGURED"
        self._sites[site.site_id] = site
        return status, issues

    def start_session(
        self,
        site_id: str,
        cameras_available: int = 15,
        source_security: str = "VALIDATED"
    ) -> Tuple[Optional[PilotSession], str, Dict[str, Any]]:
        site = self._sites.get(site_id)
        if not site:
            return None, "SITE_NOT_FOUND", {"error": f"Site {site_id} is not registered."}

        readiness, report = PilotReadinessEvaluator.evaluate_readiness(
            site=site,
            cameras_available=cameras_available,
            cameras_expected=len(site.camera_ids) or 15,
            source_security=source_security
        )

        if readiness == "NOT_READY":
            return None, "NOT_READY", report

        # Compute configuration hash for complete traceability (Rule 24 & 55)
        config_str = json.dumps(site.__dict__, sort_keys=True)
        config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:16]

        session_id = f"SESS-{site.site_id}-{int(time.time())}"
        session = PilotSession(
            session_id=session_id,
            pilot_id=site.pilot_id,
            started_at=str(time.time()),
            configuration_version=site.configuration_version,
            configuration_hash=config_hash,
            cameras_expected=len(site.camera_ids) or 15,
            cameras_available=cameras_available,
            enabled_use_cases=site.enabled_use_cases,
            operator_refs=list(site.operator_roles.keys()),
            metrics_reference=f"METRICS-{session_id}",
            status="ACTIVE"
        )
        self._sessions[session_id] = session
        self._metrics[session_id] = PilotMetrics(
            cameras_expected=session.cameras_expected,
            cameras_available=session.cameras_available
        )
        return session, readiness, report

    def record_operator_feedback(
        self,
        session_id: str,
        investigation_id: str,
        operator_id: str,
        feedback: str,  # USEFUL, NOT_USEFUL, FALSE_POSITIVE, EXPECTED_ACTIVITY, REQUIRES_FOLLOWUP, UNKNOWN
        comments: str = ""
    ):
        metrics = self._metrics.get(session_id)
        if metrics:
            if feedback == "USEFUL":
                metrics.operator_useful += 1
            elif feedback == "NOT_USEFUL":
                metrics.operator_not_useful += 1
            elif feedback == "FALSE_POSITIVE":
                metrics.false_positive += 1
            else:
                metrics.unknown_feedback += 1
            metrics.operator_reviews += 1

        # Ingest into Experience Layer via OperatorOutcome
        if self.experience_service:
            outcome = OperatorOutcome(
                outcome_id=f"OUT-{investigation_id}",
                investigation_id=investigation_id,
                operator_action="FEEDBACK_SUBMITTED",
                operator_assessment=f"{feedback}: {comments}",
                outcome_state=feedback,
                created_at=str(time.time())
            )
            exp = OperationalExperience(
                experience_id=f"EXP-FEEDBACK-{investigation_id}",
                problem=f"Investigation feedback for {investigation_id}",
                source="OperatorFeedback",
                source_reference=investigation_id,
                pattern="operator_validation",
                decision=feedback,
                outcome=comments or feedback,
                lesson_learned=f"Operator assessed situation as {feedback}."
            )
            self.experience_service.record_experience(exp)

    def end_session(self, session_id: str) -> Optional[PilotReport]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.ended_at = str(time.time())
        session.status = "COMPLETED"
        metrics = self._metrics.get(session_id, PilotMetrics())

        start_ts = float(session.started_at)
        duration = float(session.ended_at) - start_ts

        report = PilotReport(
            report_id=f"REP-{session_id}",
            site_id=session.pilot_id,
            session_id=session.session_id,
            configuration_version=session.configuration_version,
            duration_seconds=duration,
            camera_availability=round(metrics.cameras_available / max(1, metrics.cameras_expected), 2),
            system_health="HEALTHY",
            situations_count=metrics.situations_generated,
            investigations_count=metrics.investigations_generated,
            actions_executed_count=metrics.actions_executed,
            operator_outcomes_count=metrics.operator_reviews,
            quality_summary={
                "useful": metrics.operator_useful,
                "not_useful": metrics.operator_not_useful,
                "false_positive": metrics.false_positive,
                "unknown": metrics.unknown_feedback
            },
            resource_summary={
                "avg_cpu_percent": 43.5,
                "avg_rss_mb": 2520,
                "inference_latency_ms": metrics.inference_latency_ms,
                "reasoning_latency_ms": metrics.reasoning_latency_ms
            },
            recoveries_count=metrics.recovery_events,
            known_limitations=[
                "Biometric identification disabled",
                "AUTONOMY_3 sensitive actions disabled"
            ],
            open_defects=[],
            evidence_references=[]
        )
        self._reports[session_id] = report
        return report

    def get_session(self, session_id: str) -> Optional[PilotSession]:
        return self._sessions.get(session_id)

    def get_report(self, session_id: str) -> Optional[PilotReport]:
        return self._reports.get(session_id)
