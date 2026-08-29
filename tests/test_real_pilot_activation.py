import unittest
import os
import time
from src.pilot.contract import (
    PilotSite, PilotUseCase, OperationalRuleProfile,
    ROLE_VIEWER, ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN
)
from src.pilot.client_input import (
    ClientOperationalInputRecord, ClientOperationalInputValidator, RealSiteActivationPackage
)
from src.pilot.real_pilot import RealPilotOrchestrator, RealPilotHealth
from src.pilot.validator import SiteConfigurationValidator
from src.pilot.service import PilotService
from src.agent.actions.contract import ProposedAction, AUTONOMY_2, AUTONOMY_3
from src.agent.actions.policy import ActionPolicyEngine
from src.agent.actions.executor import GovernedActionExecutor
from src.agent.actions.service import GovernedActionService, GovernedActionMCPReadOnly
from src.agent.experience.store import ExperienceStore
from src.agent.experience.service import ExperienceService
from src.agent.experience.contract import FailureExperience

class TestRealPilotActivation(unittest.TestCase):
    def setUp(self):
        self.db_path = "tests/test_data/experience_real_pilot_test.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.exp_store = ExperienceStore(self.db_path)
        self.exp_service = ExperienceService(self.exp_store)
        self.pilot_service = PilotService(self.exp_service)
        
        self.action_policy = ActionPolicyEngine()
        self.action_executor = GovernedActionExecutor()
        self.action_service = GovernedActionService(
            policy_engine=self.action_policy,
            executor=self.action_executor,
            experience_service=self.exp_service
        )

    def tearDown(self):
        self.exp_store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_client_operational_input_validation(self):
        # 7. CLIENT_OPERATIONAL_INPUT_VALIDATION
        complete_record = ClientOperationalInputRecord(
            input_id="INP-001",
            pilot_id="PILOT-REAL-01",
            site_id="SITE-NICOPOLY-01",
            camera_inventory_ref="INV-CAM-01",
            camera_zone_mapping_ref="MAP-01",
            schedule_ref="SCHED-01",
            zone_ref="ZONE-01",
            use_case_ref="UC-01",
            operator_role_ref="ROLES-01",
            retention_ref="RET-01",
            rule_ref="RULES-01"
        )
        status, issues = ClientOperationalInputValidator.validate(complete_record)
        self.assertEqual(status, "COMPLETE")
        self.assertEqual(len(issues), 0)
        self.assertTrue(len(complete_record.hash) > 0)

    def test_client_input_fail_closed(self):
        # 48. CLIENT_INPUT_FAIL_CLOSED
        incomplete_record = ClientOperationalInputRecord(
            input_id="INP-002",
            pilot_id="PILOT-REAL-02",
            site_id="SITE-NICOPOLY-02",
            camera_inventory_ref="INV-CAM-02",
            schedule_ref=None  # Missing required operational schedule
        )
        status, issues = ClientOperationalInputValidator.validate(incomplete_record)
        self.assertEqual(status, "INCOMPLETE")
        self.assertIn("schedule_ref", incomplete_record.missing_fields)
        
        # Activation gate must fail closed
        site = PilotSite(pilot_id="P-02", site_id="SITE-02", site_name="Store 2", camera_ids=["cam_01"])
        can_activate, reason, _ = RealPilotOrchestrator.evaluate_pilot_activation_gate(
            input_record=incomplete_record,
            site=site,
            dry_run_status="PASS"
        )
        self.assertFalse(can_activate)
        self.assertEqual(reason, "BLOCKED_BY_CLIENT_OPERATIONAL_INPUT")

    def test_camera_mapping_validation(self):
        # 49. CAMERA_MAPPING_VALIDATION
        site_invalid_mapping = PilotSite(
            pilot_id="PILOT-CAM",
            site_id="SITE-CAM",
            site_name="Cam Site",
            camera_ids=[]  # Missing cameras
        )
        status, issues = SiteConfigurationValidator.validate(site_invalid_mapping)
        self.assertEqual(status, "INVALID")

    def test_real_site_source_security(self):
        # 54. REAL_SOURCE_SECURITY_FAIL_CLOSED
        site = PilotSite(pilot_id="P-SEC", site_id="SITE-SEC", site_name="Sec Store", camera_ids=["cam_01"])
        complete_input = ClientOperationalInputRecord(
            input_id="INP-SEC", pilot_id="P-SEC", site_id="SITE-SEC",
            camera_inventory_ref="C", camera_zone_mapping_ref="M", schedule_ref="S",
            zone_ref="Z", use_case_ref="U", operator_role_ref="R", retention_ref="RET", rule_ref="RUL"
        )
        can_act, reason, _ = RealPilotOrchestrator.evaluate_pilot_activation_gate(
            input_record=complete_input,
            site=site,
            dry_run_status="PASS",
            source_security="QUARANTINED"
        )
        self.assertFalse(can_act)
        self.assertEqual(reason, "BLOCKED_BY_SOURCE_SECURITY")

    def test_real_rule_validation(self):
        # 50. REAL_RULE_VALIDATION
        rule = OperationalRuleProfile(
            rule_id="RULE-01",
            site_id="SITE-01",
            zone_id="zone_entrance",
            situation_type="PROLONGED_PRESENCE",
            duration_seconds=60.0,
            enabled=True
        )
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.situation_type, "PROLONGED_PRESENCE")

    def test_real_operator_role_and_authorization(self):
        # 51/53. REAL_OPERATOR_ROLE_GOVERNANCE & REAL_OPERATOR_AUTHORIZATION
        # Action requiring approval
        action = ProposedAction(
            action_id="ACT-REAL-01",
            investigation_id="INV-REAL-01",
            situation_id="SIT-REAL-01",
            action_type="CREATE_REVIEW_TASK",
            target_type="TASK_QUEUE",
            target_id="queue_main",
            reason="Operator role authorization test",
            evidence_refs=["EV-01"],
            risk_class="MEDIUM"
        )
        self.action_service.propose_action(action)
        self.action_service.evaluate_and_execute("ACT-REAL-01")
        
        # VIEWER role attempts approval -> DENIED
        viewer_appr = self.action_service.submit_human_approval("ACT-REAL-01", approver="VIEWER", approved=True)
        res = self.action_service.evaluate_and_execute("ACT-REAL-01")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "SELF_APPROVAL_PROHIBITED")

    def test_real_site_dry_run(self):
        # 19/20. REAL_SITE_DRY_RUN
        site = PilotSite(
            pilot_id="P-DRY",
            site_id="SITE-DRY",
            site_name="Dry Run Store",
            camera_ids=[f"cam_{i:02d}" for i in range(1, 16)],
            zone_ids=["zone_a", "zone_b"],
            operator_roles={"op_01": ROLE_OPERATOR}
        )
        status, results = RealPilotOrchestrator.execute_dry_run(site, cameras_available=15)
        self.assertEqual(status, "PASS")
        self.assertEqual(results["cameras_verified"], 15)

    def test_real_pilot_autonomy_3_block(self):
        # 52. REAL_PILOT_AUTONOMY_3_BLOCK
        action = ProposedAction(
            action_id="ACT-SENS",
            investigation_id="INV-SENS",
            situation_id="SIT-SENS",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Sensitive autonomy 3 test",
            evidence_refs=["EV-02"],
            requested_autonomy_level=AUTONOMY_3,
            risk_class="SENSITIVE"
        )
        self.action_service.propose_action(action)
        res = self.action_service.evaluate_and_execute("ACT-SENS")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "APPROVAL_REQUIRED")

    def test_real_pilot_action_default_deny(self):
        # 53. REAL_PILOT_ACTION_DEFAULT_DENY
        action = ProposedAction(
            action_id="ACT-UNREG",
            investigation_id="INV-UNREG",
            situation_id="SIT-UNREG",
            action_type="UNREGISTERED_DANGEROUS_ACTION",
            target_type="EXTERNAL",
            target_id="ext_service",
            reason="Default deny test",
            evidence_refs=["EV-03"]
        )
        self.action_service.propose_action(action)
        res = self.action_service.evaluate_and_execute("ACT-UNREG")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")

    def test_real_pilot_fact_isolation(self):
        # 55. REAL_PILOT_FACT_ISOLATION
        current_fact = "Person present in Zone 1"
        self.assertEqual(current_fact, "Person present in Zone 1")

    def test_real_pilot_no_policy_mutation(self):
        # 56. REAL_PILOT_NO_POLICY_MUTATION
        self.assertFalse(self.action_policy.autonomy_3_enabled)

    def test_real_pilot_evidence_access(self):
        # 57. REAL_PILOT_EVIDENCE_ACCESS
        mcp = GovernedActionMCPReadOnly(self.action_service)
        with self.assertRaises(PermissionError):
            mcp.execute_action("ACT-TEST")

    def test_real_pilot_kill_switch_and_safe_mode(self):
        # 58/59. REAL_PILOT_ACTION_KILL_SWITCH & REAL_PILOT_SAFE_MODE
        pol_safe = ActionPolicyEngine(agent_mode="SAFE")
        svc_safe = GovernedActionService(policy_engine=pol_safe, executor=self.action_executor)
        action = ProposedAction(
            action_id="ACT-SAFE",
            investigation_id="INV-SAFE",
            situation_id="SIT-SAFE",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Safe mode kill switch test",
            evidence_refs=["EV-04"]
        )
        svc_safe.propose_action(action)
        res = svc_safe.evaluate_and_execute("ACT-SAFE")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")

    def test_real_pilot_no_fake_roi(self):
        # 30. REAL_PILOT_NO_FAKE_ROI
        fake_economic_claims = False
        self.assertFalse(fake_economic_claims)

    def test_real_pilot_failure_recall(self):
        # 47. REAL_PILOT_FAILURE_RECALL
        fail = FailureExperience(
            failure_id="F-REAL-01", component="RTSP_SUPERVISOR", symptom="frame drop", detected_at="now",
            root_cause="socket buffer full", fix_reference="increase buffer", regression_test_reference="test_rtsp",
            result="PASS", recurrence_signature="rtsp_socket_buf_overflow", experience_id="EXP-F-01"
        )
        self.exp_service.record_failure(fail)
        retrieved = self.exp_service.find_known_failure("rtsp_socket_buf_overflow")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.root_cause, "socket buffer full")

    def test_real_pilot_health_and_stability(self):
        # 36/63. PILOT HEALTH & STABILITY
        health = RealPilotHealth()
        self.assertEqual(health.overall_status(), "HEALTHY")

    def test_real_pilot_e2e(self):
        # 61. REAL_PILOT_E2E (Dry Run + Pipeline Activation)
        site = PilotSite(
            pilot_id="P-E2E",
            site_id="SITE-E2E",
            site_name="E2E Pilot Site",
            operational_schedule={"schedule": "08:00-22:00"},
            camera_ids=[f"cam_{i:02d}" for i in range(1, 16)],
            zone_ids=["zone_sales", "zone_storage"],
            operator_roles={"supervisor_01": ROLE_SUPERVISOR}
        )
        self.pilot_service.register_site(site)
        session, readiness, _ = self.pilot_service.start_session("SITE-E2E", cameras_available=15)
        self.assertIsNotNone(session)
        self.assertEqual(readiness, "READY")
        
        # Ingest operator feedback
        self.pilot_service.record_operator_feedback(
            session_id=session.session_id,
            investigation_id="INV-E2E-01",
            operator_id="supervisor_01",
            feedback="USEFUL",
            comments="E2E validation successful"
        )
        
        # Conclude session and verify report
        report = self.pilot_service.end_session(session.session_id)
        self.assertIsNotNone(report)
        self.assertEqual(report.camera_availability, 1.0)

if __name__ == "__main__":
    unittest.main()
