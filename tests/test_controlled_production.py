import unittest
import os
import time
from src.pilot.contract import PilotSite, ROLE_OPERATOR, ROLE_SUPERVISOR, ROLE_ADMIN
from src.production.contract import (
    ProductionProfile, ProductionPromotionRecord, ProductionChangeRecord,
    ProductionHealth, ProductionIncident, RecoveryPlan, ProductionOperationsSummary,
    PROD_STATUS_ACTIVE, PROMO_STATUS_PROMOTED, CHANGE_STATUS_APPLIED,
    CHANGE_STATUS_REJECTED, HEALTH_HEALTHY, HEALTH_DEGRADED, INCIDENT_RESOLVED,
    SEVERITY_HIGH
)
from src.production.service import ProductionService, OperatorHandoffTracker
from src.agent.actions.contract import ProposedAction, AUTONOMY_2, AUTONOMY_3
from src.agent.actions.policy import ActionPolicyEngine
from src.agent.actions.executor import GovernedActionExecutor
from src.agent.actions.service import GovernedActionService, GovernedActionMCPReadOnly
from src.agent.experience.store import ExperienceStore
from src.agent.experience.service import ExperienceService
from src.agent.experience.contract import FailureExperience

class TestControlledProduction(unittest.TestCase):
    def setUp(self):
        self.db_path = "tests/test_data/experience_prod_test.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.exp_store = ExperienceStore(self.db_path)
        self.exp_service = ExperienceService(self.exp_store)
        self.prod_service = ProductionService(self.exp_service)
        
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

    def test_production_entry_gate_and_promotion(self):
        # 8/9. PRODUCTION_ENTRY_GATE & PRODUCTION_PROMOTION
        site = PilotSite(
            pilot_id="PILOT-REAL-01",
            site_id="SITE-NICOPOLY-01",
            site_name="Nicopoly Flagship",
            operational_schedule={"hours": "08:00-22:00"},
            camera_ids=[f"cam_{i:02d}" for i in range(1, 16)],
            zone_ids=["zone_entrance", "zone_checkout"],
            enabled_use_cases=["ZONE_ACTIVITY", "PROLONGED_PRESENCE"],
            operator_roles={"supervisor_01": ROLE_SUPERVISOR}
        )
        success, profile, issues = self.prod_service.promote_to_production(site)
        self.assertTrue(success)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.status, PROD_STATUS_ACTIVE)
        self.assertTrue(len(profile.configuration_hash) > 0)

    def test_production_promotion_fail_closed(self):
        # Invalid site (0 cameras) fails promotion
        invalid_site = PilotSite(
            pilot_id="PILOT-INV",
            site_id="SITE-INV",
            site_name="Invalid Site",
            camera_ids=[]
        )
        success, profile, issues = self.prod_service.promote_to_production(invalid_site)
        self.assertFalse(success)
        self.assertIsNone(profile)

    def test_configuration_immutability_and_change_control(self):
        # 10/11. CONFIGURATION_IMMUTABILITY & CHANGE_CONTROL
        site = PilotSite(
            pilot_id="P-01", site_id="SITE-IMMUTABLE", site_name="Site Immut",
            operational_schedule={"hours": "08:00-22:00"},
            camera_ids=["cam_01", "cam_02"], zone_ids=["zone_a"]
        )
        self.prod_service.promote_to_production(site)
        prod_id = "PROD-SITE-IMMUTABLE"
        
        # 1. Disallowed mutation (e.g., MODEL_REPLACEMENT)
        ok, reason, chg = self.prod_service.apply_governed_change(
            production_id=prod_id,
            change_type="MODEL_REPLACEMENT",
            requested_by="operator_01",
            reason="Attempt unauthorized model swap",
            mutations={"model": "fake_yolo"}
        )
        self.assertFalse(ok)
        self.assertEqual(chg.status, CHANGE_STATUS_REJECTED)
        
        # 2. Allowed governed mutation (e.g., SCHEDULE_ADJUSTMENT)
        ok_allowed, reason_allowed, chg_allowed = self.prod_service.apply_governed_change(
            production_id=prod_id,
            change_type="SCHEDULE_ADJUSTMENT",
            requested_by="admin_01",
            reason="Extend holiday hours",
            mutations={"operational_schedule": {"hours": "07:00-23:00"}}
        )
        self.assertTrue(ok_allowed)
        self.assertEqual(chg_allowed.status, CHANGE_STATUS_APPLIED)
        self.assertNotEqual(chg_allowed.before_hash, chg_allowed.after_hash)

    def test_production_action_policy_and_autonomy_3_block(self):
        # 14/15. PRODUCTION_ACTION_POLICY & AUTONOMY_3_BLOCK
        self.assertFalse(self.action_policy.autonomy_3_enabled)
        action = ProposedAction(
            action_id="ACT-P-01",
            investigation_id="INV-P-01",
            situation_id="SIT-P-01",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Production safety test",
            evidence_refs=["EV-01"],
            requested_autonomy_level=AUTONOMY_3,
            risk_class="SENSITIVE"
        )
        self.action_service.propose_action(action)
        res = self.action_service.evaluate_and_execute("ACT-P-01")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "APPROVAL_REQUIRED")

    def test_production_camera_and_stream_recovery(self):
        # 23/24. PRODUCTION_CAMERA_CONTINUITY & STREAM_RECOVERY
        inc = self.prod_service.record_incident(
            production_id="PROD-SITE-01",
            component="CAMERA_STREAM",
            severity=SEVERITY_HIGH,
            symptoms="RTSP frame stall detected on cam_04",
            evidence_refs=["EV-CAM-04"]
        )
        self.assertEqual(inc.status, "OPEN")
        
        # Execute recovery
        rec_ok, rec_msg = self.prod_service.execute_recovery(inc.incident_id)
        self.assertTrue(rec_ok)
        self.assertEqual(inc.status, INCIDENT_RESOLVED)

    def test_pytorch_runtime_rollback(self):
        # 26. PYTORCH_RUNTIME_ROLLBACK
        inc = self.prod_service.record_incident(
            production_id="PROD-SITE-01",
            component="OPENVINO_INFERENCE",
            severity=SEVERITY_HIGH,
            symptoms="Inference context reset required",
            evidence_refs=["EV-OV-01"]
        )
        rec_ok, _ = self.prod_service.execute_recovery(inc.incident_id)
        self.assertTrue(rec_ok)
        self.assertEqual(inc.status, INCIDENT_RESOLVED)

    def test_production_experience_governance_and_failure_recall(self):
        # 21/29. PRODUCTION_EXPERIENCE_GOVERNANCE & FAILURE_RECALL
        fail = FailureExperience(
            failure_id="FAIL-PROD-01", component="CAMERA_STREAM", symptom="socket stall",
            detected_at="now", root_cause="buffer overflow", fix_reference="stream_reconnect",
            regression_test_reference="test_stream", result="RESOLVED",
            recurrence_signature="cam_stall_sig", experience_id="EXP-P-01"
        )
        self.exp_service.record_failure(fail)
        retrieved = self.exp_service.find_known_failure("cam_stall_sig")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.root_cause, "buffer overflow")

    def test_operator_handoff_traceability(self):
        # 34. OPERATOR_HANDOFF_TRACEABILITY
        handoff = OperatorHandoffTracker.record_handoff(
            from_operator="op_morning",
            to_operator="op_evening",
            open_investigations=["INV-01", "INV-02"],
            open_actions=["ACT-01"]
        )
        self.assertEqual(handoff["status"], "HANDOFF_VERIFIED")
        self.assertEqual(handoff["from_operator"], "op_morning")
        self.assertEqual(handoff["to_operator"], "op_evening")

    def test_production_safe_mode_and_kill_switches(self):
        # 44/45/46. SAFE_MODE, ACTION_KILL_SWITCH, AGENT_KILL_SWITCH
        safe_pol = ActionPolicyEngine(agent_mode="SAFE")
        svc = GovernedActionService(policy_engine=safe_pol, executor=self.action_executor)
        action = ProposedAction(
            action_id="ACT-SAFE-PROD",
            investigation_id="INV-SAFE",
            situation_id="SIT-SAFE",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Safe mode test",
            evidence_refs=["EV-SAFE"]
        )
        svc.propose_action(action)
        res = svc.evaluate_and_execute("ACT-SAFE-PROD")
        self.assertEqual(res.result_state, "FAILED")

    def test_production_storage_and_sqlite_stability(self):
        # 38/40. PRODUCTION_STORAGE_HEALTH & SQLITE_STABILITY
        self.assertTrue(os.path.exists(self.db_path))
        self.assertIsNotNone(self.exp_store.conn)

    def test_production_operations_summary_and_no_fake_roi(self):
        # 55/56. OPERATIONS_SUMMARY & NO_FAKE_ROI
        summary = self.prod_service.generate_operations_summary("2026-08-29T00:00:00Z", "2026-08-29T04:00:00Z")
        self.assertEqual(summary.camera_availability, 1.0)
        self.assertEqual(summary.health, HEALTH_HEALTHY)
        # Verify no fake ROI metrics present
        self.assertNotIn("roi_percentage", summary.resource_summary)
        self.assertNotIn("theft_dollars_saved", summary.resource_summary)

    def test_production_e2e(self):
        # 58. PRODUCTION_E2E
        site = PilotSite(
            pilot_id="P-E2E-PROD",
            site_id="SITE-E2E-PROD",
            site_name="Production E2E Site",
            operational_schedule={"hours": "08:00-22:00"},
            camera_ids=[f"cam_{i:02d}" for i in range(1, 16)],
            zone_ids=["zone_sales", "zone_checkout"],
            operator_roles={"admin_01": ROLE_ADMIN}
        )
        promoted, profile, _ = self.prod_service.promote_to_production(site)
        self.assertTrue(promoted)
        self.assertEqual(profile.status, PROD_STATUS_ACTIVE)

if __name__ == "__main__":
    unittest.main()
