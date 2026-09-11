"""Runtime wiring vertical tests (MACRO-OC-02, Bloques E/F/G).

Validates that one pipeline result flows into the existing Scene ->
OperatorInsight -> Learning foundations connected to the same runtime:
  - SCENE_RUNTIME: observations/tracks/activities -> scene events (only
    ACTIVITY_REQUIRES_REVIEW) -> sequences -> evidence timelines
  - OPERATOR_INSIGHT_RUNTIME: sequence+timeline+signals -> OperatorInsight
  - LEARNING_CASE_RUNTIME: signal -> RawCase -> human review -> ReviewedCase
    -> training eligible
  - CANDIDATE_PROMOTION_GATE: never auto-promote; inferior candidate blocked
"""

import tempfile
import unittest
from pathlib import Path

from src.app.runtime_wiring import RuntimeWiring, _classification_to_label
from src.behavior import BehaviorEngine
from src.correlation.contracts import CrossCameraLink, TrackReference, Trajectory
from src.learning.memory import PolicyRejectionError, SignalLabel
from src.review.contracts import SignalReviewRecord
from src.temporal.contract import LocalTrack, TemporalActivity


def track(camera="CAM-001", tid="T-1", seconds=45, events=4, evidence=True):
    return LocalTrack(
        track_id=tid, camera_id=camera, object_type="person",
        started_at="2026-08-17T10:00:00Z",
        last_seen_at=f"2026-08-17T10:00:{seconds:02d}Z",
        event_count=events,
        evidence_refs={"first": "e/1.jpg" if evidence else None,
                       "latest": "e/2.jpg" if evidence else None,
                       "best": "e/2.jpg" if evidence else None},
    )


def activity(t, seconds=45):
    return TemporalActivity(
        activity_id="A-1", track_id=t.track_id, source_id=t.camera_id,
        activity_type="PERSON_PRESENCE", started_at=t.started_at,
        last_seen_at=t.last_seen_at, duration_ms=seconds * 1000,
        event_count=t.event_count, evidence_refs=t.evidence_refs,
    )


def trajectory():
    nodes = tuple(TrackReference(
        camera_id=f"CAM-00{i}", track_id=f"T-{i}", object_type="person",
        start_time=f"2026-08-17T10:00:{i * 10:02d}Z",
        end_time=f"2026-08-17T10:00:{i * 10 + 5:02d}Z",
        evidence_refs=(f"e/{i}.jpg",),
    ) for i in range(1, 5))
    edges = tuple(CrossCameraLink(
        link_id=f"L-{i}", candidate_id=f"C-{i}",
        source_track_ref=nodes[i].track_id, target_track_ref=nodes[i + 1].track_id,
        source_camera_id=nodes[i].camera_id, target_camera_id=nodes[i + 1].camera_id,
        time_delta_seconds=5, score_components=(("temporal", 0.7),),
        correlation_score=0.9, evidence_refs=(f"e/{i}.jpg",),
    ) for i in range(3))
    return Trajectory("TR-1", nodes, edges, nodes[0].start_time,
                      nodes[-1].end_time, tuple(f"e/{i}.jpg" for i in range(1, 5)),
                      (("method", "temporal_topological"),))


def behavior_result():
    t = track()
    return BehaviorEngine().evaluate(
        track=t, activity=activity(t), trajectory=trajectory()
    )


def make_record(signal, classification="USEFUL_SIGNAL", review_id="SRR-1"):
    return SignalReviewRecord(
        review_id=review_id,
        signal_id=signal.signal_id,
        signal_type=signal.signal_type,
        camera_id="CAM-001",
        track_id="T-1",
        trajectory_id=None,
        rule_id=signal.rule_id,
        timestamp_start=signal.window_start,
        timestamp_end=signal.window_end,
        rule_score=signal.rule_score,
        source_refs=(),
        evidence_refs=("cam_a/1.jpg",),
        structured_explanation={},
        human_classification=classification,
    )


class TestSceneRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.wiring = RuntimeWiring(
            organization_id="ORG-1",
            store_id="store_a",
            dataset_root=str(root / "datasets"),
            policy_root=str(root / "policies"),
        )
        self.result = behavior_result()

    def tearDown(self):
        self.tmp.cleanup()

    def test_pipeline_result_produces_scene_events_and_sequences(self):
        t = track()
        created = self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": activity(t),
                "behavior": self.result,
                "evidence": None,
            },
        )
        self.assertGreaterEqual(created["scene_events"], 1)
        self.assertGreaterEqual(created["sequences"], 1)
        events = self.wiring.scene_events()
        self.assertTrue(events)
        self.assertTrue(
            all(event.event_type == "ACTIVITY_REQUIRES_REVIEW" for event in events)
        )
        self.assertEqual(
            {event.priority for event in events},
            {self.wiring._scene._map_priority(self.result.risk_event.risk_score)},
        )

    def test_scene_event_traceability(self):
        t = track()
        self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": activity(t),
                "behavior": self.result,
                "evidence": None,
            },
        )
        event = self.wiring.scene_events()[0]
        self.assertEqual(event.store_id, "store_a")
        self.assertIn("CAM-001", event.camera_ids)
        self.assertIn("T-1", event.track_ids)
        self.assertTrue(event.explanation)

    def test_evidence_timeline_links_pipeline_evidence(self):
        t = track()
        self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": None,
                "behavior": self.result,
                "evidence": {"relative_path": "store_a/cam/evd.jpg", "timestamp": "2026-08-19T00:00:00Z"},
            },
        )
        timeline = self.wiring._scene.get_evidence_timeline("T-1")
        self.assertTrue(timeline.evidence_items)
        self.assertIn("store_a/cam/evd.jpg", {item["path"] for item in timeline.evidence_items})


class TestOperatorInsightRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.wiring = RuntimeWiring(
            organization_id="ORG-1",
            store_id="store_a",
            dataset_root=str(root / "datasets"),
            policy_root=str(root / "policies"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_insight_generated_from_scene_sequence(self):
        t = track()
        result = behavior_result()
        self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": activity(t),
                "behavior": result,
                "evidence": {"relative_path": "store_a/cam/evd.jpg", "timestamp": "2026-08-19T00:00:00Z"},
            },
        )
        insights = self.wiring.insights()
        self.assertEqual(len(insights), 1)
        insight = insights[0]
        self.assertEqual(insight.store_id, "store_a")
        self.assertEqual(insight.organization_id, "ORG-1")
        self.assertIn("ACTIVITY_REQUIRES_REVIEW", insight.reason_for_review)
        self.assertTrue(insight.evidence_refs)
        self.assertIn("T-1", insight.tracks)
        self.assertIn("CAM-001", insight.cameras)

    def test_query_engine_retrieves_insight_by_store(self):
        from src.operator.engine import OperatorQuery
        t = track()
        self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": activity(t),
                "behavior": behavior_result(),
                "evidence": None,
            },
        )
        query = OperatorQuery(what="señal", store_id="store_a")
        result = self.wiring.query(query)
        self.assertEqual(result.total_matches, 1)
        self.assertEqual(result.insights[0].store_id, "store_a")


class TestLearningCaseRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.wiring = RuntimeWiring(
            organization_id="ORG-1",
            store_id="store_a",
            dataset_root=str(root / "datasets"),
            policy_root=str(root / "policies"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _ingest(self):
        t = track()
        result = behavior_result()
        self.wiring.ingest_result(
            "CAM-001",
            {},
            {
                "observation": None,
                "track": t,
                "temporal_activity": activity(t),
                "behavior": result,
                "evidence": None,
            },
        )
        return result

    def test_signal_becomes_raw_case(self):
        result = self._ingest()
        self.assertEqual(self.wiring.summary()["raw_cases"], len(result.signals))
        memory = self.wiring.case_memory()
        self.assertEqual(len(memory.raw_cases), len(result.signals))

    def test_review_maps_useful_signal_to_training_eligible(self):
        result = self._ingest()
        signal = result.signals[0]
        reviewed = self.wiring.review_and_learn(make_record(signal, "USEFUL_SIGNAL"))
        self.assertEqual(reviewed.label, SignalLabel.USEFUL_SIGNAL)
        summary = self.wiring.summary()
        self.assertEqual(summary["reviewed_cases"], 1)
        self.assertEqual(summary["training_eligible"], 1)
        dataset = self.wiring.build_dataset()
        self.assertEqual(len(dataset.records), 1)
        self.assertEqual(dataset.records[0]["label"], "USEFUL_SIGNAL")

    def test_benign_activity_maps_to_false_positive_not_eligible(self):
        result = self._ingest()
        signal = result.signals[0]
        reviewed = self.wiring.review_and_learn(
            make_record(signal, "BENIGN_ACTIVITY", review_id="SRR-FP")
        )
        self.assertEqual(reviewed.label, SignalLabel.FALSE_POSITIVE)
        self.assertEqual(self.wiring.summary()["training_eligible"], 0)

    def test_inferior_candidate_blocked_by_promotion_gate(self):
        result = self._ingest()
        self.wiring.review_and_learn(
            make_record(result.signals[0], "USEFUL_SIGNAL", review_id="SRR-A")
        )
        dataset = self.wiring.build_dataset()
        self.assertEqual(dataset.manifest.total_cases, 1)
        self.assertGreater(dataset.records[0]["risk_score"], 0)
        # Baseline policy with a superior f1_score that no candidate can beat.
        from src.learning.memory import CurrentPolicy
        baseline = CurrentPolicy(
            policy_id="POL-BASE", version="v1",
            validation_metrics={"f1_score": 0.99, "precision": 0.99, "recall": 0.99},
        )
        self.wiring.policy_manager().set_current(baseline)
        # Threshold above the useful record's risk score yields fn -> f1=0.
        candidate = self.wiring.policy_manager().create_candidate(
            "v1", {"risk_weights": {"risk_threshold": 90.0}}
        )
        validated = self.wiring.policy_manager().validate_candidate(
            candidate.candidate_id, dataset
        )
        self.assertEqual(validated.validation_metrics["f1_score"], 0.0)
        with self.assertRaises(PolicyRejectionError):
            self.wiring.policy_manager().promote_candidate(candidate.candidate_id)
        # No auto-promotion: nothing was promoted.
        self.assertIs(self.wiring.current_policy(), baseline)

    def test_no_auto_promotion_of_policy(self):
        self._ingest()
        self.assertIsNone(self.wiring.current_policy())


class TestClassificationMapping(unittest.TestCase):
    def test_classification_map(self):
        self.assertEqual(
            _classification_to_label("USEFUL_SIGNAL"), SignalLabel.USEFUL_SIGNAL
        )
        self.assertEqual(
            _classification_to_label("BENIGN_ACTIVITY"), SignalLabel.FALSE_POSITIVE
        )
        for value in ("AMBIGUOUS", "INSUFFICIENT_EVIDENCE", "SYSTEM_ERROR"):
            self.assertEqual(
                _classification_to_label(value), SignalLabel.INSUFFICIENT_EVIDENCE
            )
        self.assertEqual(
            _classification_to_label("NOT_REVIEWED"), SignalLabel.INSUFFICIENT_EVIDENCE
        )


if __name__ == "__main__":
    unittest.main()
