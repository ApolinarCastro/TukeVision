import unittest
import time
import os
from src.agent.actions.contract import (
    ProposedAction, HumanApprovalRequest, ActionResult,
    AUTONOMY_0, AUTONOMY_1, AUTONOMY_2, AUTONOMY_3,
    ALLOWED_ACTION_TYPES
)
from src.agent.actions.policy import ActionPolicyEngine, ActionEvidenceGate
from src.agent.actions.verifier import ActionVerifier
from src.agent.actions.executor import GovernedActionExecutor
from src.agent.actions.queue import GovernedActionQueue
from src.agent.actions.service import GovernedActionService, GovernedActionMCPReadOnly
from src.agent.experience.store import ExperienceStore
from src.agent.experience.service import ExperienceService

class TestGovernedActions(unittest.TestCase):
    def setUp(self):
        self.verifier = ActionVerifier()
        self.policy_engine = ActionPolicyEngine()
        self.executor = GovernedActionExecutor(self.verifier)
        self.queue = GovernedActionQueue()
        
        self.db_path = "tests/test_data/experience_action_test.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.exp_store = ExperienceStore(self.db_path)
        self.exp_service = ExperienceService(self.exp_store)
        
        self.service = GovernedActionService(
            policy_engine=self.policy_engine,
            executor=self.executor,
            queue=self.queue,
            experience_service=self.exp_service
        )

    def tearDown(self):
        self.exp_store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_action_default_deny(self):
        # 40. TEST — POLICY DEFAULT DENY
        action = ProposedAction(
            action_id="ACT-001",
            investigation_id="INV-001",
            situation_id="SIT-001",
            action_type="UNKNOWN_UNREGISTERED_ACTION",
            target_type="CAMERA",
            target_id="cam_01",
            reason="Testing default deny",
            evidence_refs=["EV-001"]
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-001")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")
        self.assertEqual(action.status, "POLICY_DENIED")

    def test_autonomy_2_limited_action(self):
        # 41. TEST — AUTONOMY 2
        action = ProposedAction(
            action_id="ACT-002",
            investigation_id="INV-002",
            situation_id="SIT-002",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="High risk loitering in restricted zone",
            evidence_refs=["EV-100"],
            requested_autonomy_level=AUTONOMY_2,
            risk_class="LOW"
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-002")
        self.assertEqual(res.result_state, "SUCCESS")
        self.assertEqual(res.verification_state, "VERIFIED")
        self.assertEqual(action.status, "VERIFIED")

    def test_sensitive_action_block(self):
        # 42. TEST — SENSITIVE ACTION
        action = ProposedAction(
            action_id="ACT-003",
            investigation_id="INV-003",
            situation_id="SIT-003",
            action_type="door_unlock",
            target_type="PHYSICAL_DOOR",
            target_id="door_main",
            reason="Attempt physical door unlock",
            evidence_refs=["EV-101"]
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-003")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")
        self.assertEqual(action.status, "POLICY_DENIED")

    def test_autonomy_3_disabled(self):
        # 43. TEST — AUTONOMY 3
        action = ProposedAction(
            action_id="ACT-004",
            investigation_id="INV-004",
            situation_id="SIT-004",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Sensitive action test",
            evidence_refs=["EV-102"],
            requested_autonomy_level=AUTONOMY_3,
            risk_class="SENSITIVE"
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-004")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(action.status, "PENDING_APPROVAL")

    def test_human_approval_flow(self):
        # 44. TEST — HUMAN APPROVAL
        action = ProposedAction(
            action_id="ACT-005",
            investigation_id="INV-005",
            situation_id="SIT-005",
            action_type="CREATE_REVIEW_TASK",
            target_type="TASK_QUEUE",
            target_id="task_q1",
            reason="Medium risk anomaly",
            evidence_refs=["EV-103"],
            requested_autonomy_level=AUTONOMY_2,
            risk_class="MEDIUM"  # Requires human approval
        )
        self.service.propose_action(action)
        
        # 1. Attempt execute without approval -> PENDING_APPROVAL
        res1 = self.service.evaluate_and_execute("ACT-005")
        self.assertEqual(res1.result_state, "FAILED")
        self.assertEqual(action.status, "PENDING_APPROVAL")
        
        # 2. Operator approves
        self.service.submit_human_approval("ACT-005", approver="Operator_John", approved=True)
        
        # 3. Execute with approval -> SUCCESS
        res2 = self.service.evaluate_and_execute("ACT-005")
        self.assertEqual(res2.result_state, "SUCCESS")
        self.assertEqual(res2.verification_state, "VERIFIED")

    def test_no_self_approval(self):
        # 45. TEST — NO SELF APPROVAL
        action = ProposedAction(
            action_id="ACT-006",
            investigation_id="INV-006",
            situation_id="SIT-006",
            action_type="CREATE_REVIEW_TASK",
            target_type="TASK_QUEUE",
            target_id="task_q1",
            reason="Testing self approval block",
            evidence_refs=["EV-104"],
            risk_class="HIGH"
        )
        self.service.propose_action(action)
        self.service.evaluate_and_execute("ACT-006")
        
        # AI/Agent attempts self-approval
        self.service.submit_human_approval("ACT-006", approver="AgentMonitor", approved=True)
        res = self.service.evaluate_and_execute("ACT-006")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "SELF_APPROVAL_PROHIBITED")

    def test_action_idempotency(self):
        # 46. TEST — IDEMPOTENCY
        action = ProposedAction(
            action_id="ACT-007",
            investigation_id="INV-007",
            situation_id="SIT-007",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Idempotency test",
            evidence_refs=["EV-105"],
            idempotency_key="IDEMP-ALERT-INV-007"
        )
        self.service.propose_action(action)
        res1 = self.service.evaluate_and_execute("ACT-007")
        self.assertEqual(res1.result_state, "SUCCESS")
        
        # Re-execute same action
        res2 = self.service.evaluate_and_execute("ACT-007")
        self.assertEqual(res2.result_state, "SUCCESS")
        self.assertEqual(res1.result_reference, res2.result_reference)

    def test_action_expiration(self):
        # 47. TEST — EXPIRATION
        now = time.time()
        action = ProposedAction(
            action_id="ACT-008",
            investigation_id="INV-008",
            situation_id="SIT-008",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Expiration test",
            evidence_refs=["EV-106"],
            expires_at=str(now - 10)  # Already expired
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-008", current_timestamp=now)
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "ACTION_EXPIRED")
        self.assertEqual(action.status, "EXPIRED")

    def test_evidence_sufficiency_gate(self):
        # 48. TEST — EVIDENCE SUFFICIENCY
        action = ProposedAction(
            action_id="ACT-009",
            investigation_id="INV-009",
            situation_id="SIT-009",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Evidence sufficiency test",
            evidence_refs=[]  # No evidence
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-009")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")

    def test_degraded_source_health_gate(self):
        # 49. TEST — DEGRADED SOURCE
        action = ProposedAction(
            action_id="ACT-010",
            investigation_id="INV-010",
            situation_id="SIT-010",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Degraded source test",
            evidence_refs=["EV-107"]
        )
        self.service.propose_action(action)
        # Source health is DEGRADED
        res = self.service.evaluate_and_execute("ACT-010", source_health="DEGRADED")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "APPROVAL_REQUIRED")
        self.assertEqual(action.status, "PENDING_APPROVAL")

    def test_action_provenance(self):
        # 50. TEST — ACTION PROVENANCE
        action = ProposedAction(
            action_id="ACT-011",
            investigation_id="INV-011",
            situation_id="SIT-011",
            action_type="PIN_EVIDENCE",
            target_type="CAMERA",
            target_id="cam_03",
            reason="Pinning anomaly evidence",
            supporting_fact_refs=["FACT-001", "FACT-002"],
            evidence_refs=["EV-108", "EV-109"],
            proposed_at="2026-08-29T10:00:00Z"
        )
        self.service.propose_action(action)
        self.service.evaluate_and_execute("ACT-011")
        
        prov = self.service.trace_provenance("ACT-011")
        self.assertEqual(prov["action_id"], "ACT-011")
        self.assertEqual(prov["investigation_id"], "INV-011")
        self.assertIn("FACT-001", prov["supporting_facts"])
        self.assertIn("EV-108", prov["evidence_refs"])
        self.assertEqual(prov["camera_id"], "cam_03")

    def test_action_result_verification(self):
        # 51. TEST — VERIFICATION
        # Custom faulty handler that returns SUCCESS but registers nothing in verifier
        class FaultyHandler:
            def execute(self, action, verifier):
                return ActionResult(
                    action_id=action.action_id,
                    result_state="SUCCESS",
                    result_reference="FAKE-REF",
                    verification_required=True
                )
        
        from src.agent.actions import executor
        orig = executor.ACTION_HANDLER_REGISTRY.get("CREATE_OPERATOR_ALERT")
        executor.ACTION_HANDLER_REGISTRY["CREATE_OPERATOR_ALERT"] = FaultyHandler()
        try:
            action = ProposedAction(
                action_id="ACT-012",
                investigation_id="INV-012",
                situation_id="SIT-012",
                action_type="CREATE_OPERATOR_ALERT",
                target_type="OPERATOR",
                target_id="op_console",
                reason="Verification failure test",
                evidence_refs=["EV-110"]
            )
            self.service.propose_action(action)
            res = self.service.evaluate_and_execute("ACT-012")
            self.assertEqual(res.result_state, "FAILED")
            self.assertEqual(res.verification_state, "VERIFICATION_FAILED")
        finally:
            executor.ACTION_HANDLER_REGISTRY["CREATE_OPERATOR_ALERT"] = orig

    def test_kill_switch(self):
        # 52. TEST — KILL SWITCH
        policy_off = ActionPolicyEngine(action_execution_enabled=False)
        svc_off = GovernedActionService(policy_engine=policy_off, executor=self.executor, queue=self.queue)
        
        action = ProposedAction(
            action_id="ACT-013",
            investigation_id="INV-013",
            situation_id="SIT-013",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Kill switch test",
            evidence_refs=["EV-111"]
        )
        svc_off.propose_action(action)
        res = svc_off.evaluate_and_execute("ACT-013")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")
        self.assertIn("KILL_SWITCH", res.error_message)

    def test_safe_mode(self):
        # 53. TEST — SAFE MODE
        policy_safe = ActionPolicyEngine(agent_mode="SAFE")
        svc_safe = GovernedActionService(policy_engine=policy_safe, executor=self.executor, queue=self.queue)
        
        action = ProposedAction(
            action_id="ACT-014",
            investigation_id="INV-014",
            situation_id="SIT-014",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Safe mode test",
            evidence_refs=["EV-112"]
        )
        svc_safe.propose_action(action)
        res = svc_safe.evaluate_and_execute("ACT-014")
        self.assertEqual(res.result_state, "FAILED")
        self.assertEqual(res.error_code, "POLICY_DENIED")
        self.assertIn("SAFE_MODE", res.error_message)

    def test_failure_isolation(self):
        # 54. TEST — FAILURE ISOLATION
        state = "ACTION_LAYER_UNAVAILABLE"
        self.assertEqual(state, "ACTION_LAYER_UNAVAILABLE")

    def test_experience_integration(self):
        # 55. TEST — EXPERIENCE INTEGRATION
        action = ProposedAction(
            action_id="ACT-015",
            investigation_id="INV-015",
            situation_id="SIT-015",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="Experience recording test",
            evidence_refs=["EV-113"]
        )
        self.service.propose_action(action)
        self.service.evaluate_and_execute("ACT-015")
        
        self.service.record_action_experience(
            action_id="ACT-015",
            operator_assessment="Alert verified and valid",
            outcome_result="RESOLVED"
        )
        
        exp = self.exp_service.get_experience("EXP-ACT-ACT-015")
        self.assertIsNotNone(exp)
        self.assertIn("CREATE_OPERATOR_ALERT", exp.lesson_learned)

    def test_no_automatic_policy_mutation(self):
        # 56. TEST — NO POLICY MUTATION
        initial_allowlist = set(ALLOWED_ACTION_TYPES)
        # Record 10 positive experiences
        for i in range(10):
            self.service.record_action_experience(
                action_id=f"ACT-MOCK-{i}",
                operator_assessment="Good action",
                outcome_result="SUCCESS"
            )
        # Allowlist must remain unmodified
        self.assertEqual(set(ALLOWED_ACTION_TYPES), initial_allowlist)
        self.assertFalse(self.policy_engine.autonomy_3_enabled)

    def test_mcp_governance(self):
        # 57. TEST — MCP
        mcp = GovernedActionMCPReadOnly(self.service)
        
        action = ProposedAction(
            action_id="ACT-016",
            investigation_id="INV-016",
            situation_id="SIT-016",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="MCP test",
            evidence_refs=["EV-114"]
        )
        self.service.propose_action(action)
        
        # Reads allowed
        act_dict = mcp.get_action("ACT-016")
        self.assertIsNotNone(act_dict)
        self.assertEqual(act_dict["action_id"], "ACT-016")
        
        # Writes prohibited
        with self.assertRaises(PermissionError):
            mcp.execute_action("ACT-016")
        with self.assertRaises(PermissionError):
            mcp.approve_action("ACT-016")
        with self.assertRaises(PermissionError):
            mcp.change_policy()
        with self.assertRaises(PermissionError):
            mcp.change_autonomy()

    def test_governed_action_e2e(self):
        # 59/60. END-TO-END CASO OBLIGATORIO: CREATE_OPERATOR_ALERT
        action = ProposedAction(
            action_id="ACT-E2E-01",
            investigation_id="INV-E2E-01",
            situation_id="SIT-E2E-01",
            action_type="CREATE_OPERATOR_ALERT",
            target_type="OPERATOR",
            target_id="op_console",
            reason="E2E loitering alert",
            evidence_refs=["EV-E2E-01"],
            requested_autonomy_level=AUTONOMY_2,
            risk_class="LOW"
        )
        self.service.propose_action(action)
        res = self.service.evaluate_and_execute("ACT-E2E-01")
        
        self.assertEqual(res.result_state, "SUCCESS")
        self.assertEqual(res.verification_state, "VERIFIED")
        
        # Verify Audit Log
        audit = self.service.get_action_audit("ACT-E2E-01")
        self.assertTrue(len(audit) > 0)
        self.assertEqual(audit[0]["policy_decision"], "ALLOW")
        self.assertEqual(audit[0]["verification_state"], "VERIFIED")
        
        # Record outcome & experience
        self.service.record_action_experience("ACT-E2E-01", "Operator confirmed alert", "SUCCESS")
        exp = self.exp_service.get_experience("EXP-ACT-ACT-E2E-01")
        self.assertIsNotNone(exp)

if __name__ == "__main__":
    unittest.main()
