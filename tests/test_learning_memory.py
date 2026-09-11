"""LEARNING vertical tests (MACRO-OC-01-R, Block 9).

Covers LEARNING_CURRENT_POLICY, LEARNING_CANDIDATE_CREATION,
LEARNING_VALIDATION and INFERIOR_CANDIDATE_GATE
(INFERIOR_CANDIDATE -> MUST_NOT_REPLACE_CURRENT). Also asserts the
no auto-promotion governance guarantee.
"""

import tempfile
import unittest

from src.learning.memory import (
    CandidatePolicy,
    CurrentPolicy,
    DatasetManifest,
    FeedbackDataset,
    PolicyManager,
    PolicyRejectionError,
    PolicyValidationError,
    SignalLabel,
)


def _temp_policy_manager():
    """PolicyManager with an isolated temp policy root (test hygiene)."""
    root = tempfile.TemporaryDirectory()
    manager = PolicyManager(policy_root=root.name)
    manager._test_root = root
    return manager


def make_policy(f1=0.70, version="v1", policy_id="POL-1"):
    return CurrentPolicy(
        policy_id=policy_id,
        version=version,
        behavior_thresholds={"prolonged_dwell_min_seconds": 30.0},
        risk_weights={"risk_threshold": 60.0},
        zone_configs={},
        validation_metrics={"f1_score": f1, "precision": f1, "recall": f1},
    )


def make_dataset(threshold=60.0):
    records = (
        {"label": SignalLabel.USEFUL_SIGNAL.value, "risk_score": 80.0},
        {"label": SignalLabel.FALSE_POSITIVE.value, "risk_score": 70.0},
        {"label": SignalLabel.USEFUL_SIGNAL.value, "risk_score": 40.0},
        {"label": SignalLabel.FALSE_POSITIVE.value, "risk_score": 30.0},
    )
    return FeedbackDataset(
        manifest=DatasetManifest(
            version="d1", created_at_utc="2026-08-19T00:00:00Z",
            total_cases=len(records),
        ),
        records=records,
    )


class TestCurrentPolicy(unittest.TestCase):
    def test_current_policy_is_a_usable_dataclass(self):
        policy = make_policy()
        self.assertEqual(policy.version, "v1")
        self.assertEqual(policy.validation_metrics["f1_score"], 0.70)
        self.assertTrue(policy.effective_since_utc)
        self.assertTrue(policy.created_at_utc)

    def test_current_policy_dict_round_trip(self):
        policy = make_policy()
        restored = CurrentPolicy.from_dict(policy.to_dict())
        self.assertEqual(restored.policy_id, policy.policy_id)
        self.assertEqual(restored.version, policy.version)
        self.assertEqual(restored.validation_metrics, policy.validation_metrics)
        self.assertEqual(restored.risk_weights, policy.risk_weights)


class TestCandidateCreation(unittest.TestCase):
    def setUp(self):
        self.manager = _temp_policy_manager()
        self.addCleanup(self.manager._test_root.cleanup)
        self.manager.set_current(make_policy())

    def test_create_candidate_from_current_base(self):
        candidate = self.manager.create_candidate(
            "v1", {"risk_weights": {"risk_threshold": 70.0}}
        )
        self.assertIsInstance(candidate, CandidatePolicy)
        self.assertEqual(candidate.status, "DRAFT")
        self.assertEqual(candidate.base_policy_version, "v1")
        self.assertEqual(
            candidate.proposed_changes["risk_weights"]["risk_threshold"], 70.0
        )

    def test_create_candidate_unknown_base_raises(self):
        with self.assertRaises(PolicyValidationError):
            self.manager.create_candidate(
                "v99", {"risk_weights": {"risk_threshold": 70.0}}
            )


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.manager = _temp_policy_manager()
        self.addCleanup(self.manager._test_root.cleanup)
        self.manager.set_current(make_policy())
        self.candidate = self.manager.create_candidate(
            "v1", {"risk_weights": {"risk_threshold": 60.0}}
        )

    def test_validation_metrics_are_deterministic(self):
        metrics = self.candidate.validate(make_dataset())
        self.assertAlmostEqual(metrics["precision"], 0.5)
        self.assertAlmostEqual(metrics["recall"], 0.5)
        self.assertAlmostEqual(metrics["f1_score"], 0.5)
        self.assertAlmostEqual(metrics["false_positive_rate"], 0.5)
        self.assertEqual(metrics["total_records"], 4)

    def test_validate_candidate_marks_validated(self):
        validated = self.manager.validate_candidate(
            self.candidate.candidate_id, make_dataset()
        )
        self.assertEqual(validated.status, "VALIDATED")
        self.assertTrue(validated.validated_at_utc)
        self.assertAlmostEqual(validated.validation_metrics["f1_score"], 0.5)

    def test_empty_dataset_cannot_be_validated(self):
        empty = FeedbackDataset(
            manifest=DatasetManifest(
                version="d0", created_at_utc="2026-08-19T00:00:00Z", total_cases=0
            ),
            records=(),
        )
        with self.assertRaises(PolicyValidationError):
            self.manager.validate_candidate(self.candidate.candidate_id, empty)


class TestPromotionGate(unittest.TestCase):
    def setUp(self):
        self.manager = _temp_policy_manager()
        self.addCleanup(self.manager._test_root.cleanup)
        self.manager.set_current(make_policy(f1=0.50))

    def _validated_candidate(self, threshold=60.0):
        candidate = self.manager.create_candidate(
            "v1", {"risk_weights": {"risk_threshold": threshold}}
        )
        return self.manager.validate_candidate(
            candidate.candidate_id, make_dataset()
        )

    def test_superior_candidate_is_promoted(self):
        # Dataset with threshold 60 yields f1=0.5 == current 0.5 (not inferior).
        candidate = self._validated_candidate(threshold=60.0)
        new_policy = self.manager.promote_candidate(candidate.candidate_id)
        self.assertEqual(new_policy.version, "v2")
        self.assertEqual(self.manager.current().policy_id, new_policy.policy_id)
        self.assertEqual(
            self.manager.get_candidate(candidate.candidate_id).status, "PROMOTED"
        )

    def test_inferior_candidate_is_rejected(self):
        current = make_policy(f1=0.90)
        self.manager.set_current(current)
        candidate = self._validated_candidate(threshold=60.0)  # f1 = 0.5
        with self.assertRaises(PolicyRejectionError) as ctx:
            self.manager.promote_candidate(candidate.candidate_id)
        self.assertIn("INFERIOR_CANDIDATE", str(ctx.exception))
        self.assertIn("MUST_NOT_REPLACE_CURRENT", str(ctx.exception))

    def test_unvalidated_candidate_cannot_promote(self):
        candidate = self.manager.create_candidate(
            "v1", {"risk_weights": {"risk_threshold": 70.0}}
        )
        with self.assertRaises(PolicyValidationError):
            self.manager.promote_candidate(candidate.candidate_id)

    def test_no_automatic_promotion(self):
        candidate = self._validated_candidate(threshold=60.0)
        self.assertEqual(candidate.status, "VALIDATED")
        self.assertEqual(self.manager.current().version, "v1")


if __name__ == "__main__":
    unittest.main()
