import json
import unittest
from types import SimpleNamespace

from src.behavior import BehaviorEngine, BehaviorFeature, BehaviorSignal, RiskEvent
from src.correlation.contracts import CrossCameraLink, TrackReference, Trajectory
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


def trajectory(status="CANDIDATE"):
    nodes = tuple(TrackReference(
        camera_id=f"CAM-00{i}", track_id=f"T-{i}", object_type="person",
        start_time=f"2026-08-17T10:00:{i*10:02d}Z",
        end_time=f"2026-08-17T10:00:{i*10+5:02d}Z",
        evidence_refs=(f"e/{i}.jpg",),
    ) for i in range(1, 5))
    edges = tuple(CrossCameraLink(
        link_id=f"L-{i}", candidate_id=f"C-{i}",
        source_track_ref=nodes[i].track_id, target_track_ref=nodes[i+1].track_id,
        source_camera_id=nodes[i].camera_id, target_camera_id=nodes[i+1].camera_id,
        time_delta_seconds=5, score_components=(("temporal", .7),),
        correlation_score=.9, evidence_refs=(f"e/{i}.jpg",),
    ) for i in range(3))
    return Trajectory("TR-1", nodes, edges, nodes[0].start_time,
                      nodes[-1].end_time, tuple(f"e/{i}.jpg" for i in range(1, 5)),
                      (("method", "temporal_topological"),), status=status)


class TestBehaviorContracts(unittest.TestCase):
    def test_contracts_are_json_serializable_and_non_accusatory(self):
        result = BehaviorEngine().evaluate(track=track(), activity=activity(track()), trajectory=trajectory())
        text = json.dumps(result.to_dict())
        self.assertTrue(result.features)
        self.assertIsInstance(result.features[0], BehaviorFeature)
        self.assertIsInstance(result.signals[0], BehaviorSignal)
        self.assertIsInstance(result.risk_event, RiskEvent)
        for forbidden in ("shoplift", "guilt", "identity", "biometric"):
            self.assertNotIn(forbidden, text.lower())

    def test_observation_and_event_references_are_traceable(self):
        observation = SimpleNamespace(observation_id="OBS-1", camera_id="CAM-001", evidence_ref="e/obs.jpg")
        event = SimpleNamespace(event_id="EVT-1", camera_id="CAM-001", timestamp="2026-08-17T10:00:45Z", evidence_ref="e/event.jpg")
        result = BehaviorEngine().evaluate(observation=observation, event=event, track=track())
        self.assertIn("OBS-1", result.features[0].source_refs)
        self.assertIn("EVT-1", result.features[0].source_refs)

    def test_missing_evidence_is_preserved_not_fabricated(self):
        result = BehaviorEngine().evaluate(track=track(evidence=False))
        self.assertEqual(result.evidence_refs, ())


class TestFeatureExtraction(unittest.TestCase):
    def test_extracts_dwell_repetition_and_trajectory_facts(self):
        t = track()
        result = BehaviorEngine().evaluate(track=t, activity=activity(t), trajectory=trajectory())
        values = {f.feature_type: f.value for f in result.features}
        self.assertEqual(values["dwell_seconds"], 45.0)
        self.assertEqual(values["event_count"], 4)
        self.assertEqual(values["camera_count"], 4)
        self.assertEqual(values["transition_count"], 3)

    def test_zone_visits_only_uses_explicit_metadata(self):
        a = BehaviorEngine().evaluate(track=track(), metadata={"zone_visits": 3})
        b = BehaviorEngine().evaluate(track=track(), metadata={})
        self.assertIn("zone_visits", {f.feature_type for f in a.features})
        self.assertNotIn("zone_visits", {f.feature_type for f in b.features})


class TestSignalsAndRisk(unittest.TestCase):
    def test_rules_generate_explainable_review_candidate(self):
        t = track()
        result = BehaviorEngine().evaluate(track=t, activity=activity(t), trajectory=trajectory())
        self.assertEqual({s.rule_id for s in result.signals},
                         {"prolonged_dwell", "repeated_activity", "multi_camera_sequence"})
        self.assertEqual(result.risk_event.status, "REVIEW_REQUIRED")
        self.assertGreaterEqual(result.risk_event.risk_score, 60)
        self.assertEqual(len(result.risk_event.rules_triggered), 3)

    def test_thresholds_are_config_driven(self):
        engine = BehaviorEngine({"behavior": {"rules": {
            "prolonged_dwell": {"enabled": True, "min_seconds": 90, "score": 20},
            "repeated_activity": {"enabled": False},
            "multi_camera_sequence": {"enabled": False}}}})
        self.assertEqual(engine.evaluate(track=track()).signals, ())

    def test_single_signal_does_not_become_risk(self):
        result = BehaviorEngine().evaluate(track=track(events=1))
        self.assertEqual(len(result.signals), 1)
        self.assertIsNone(result.risk_event)

    def test_ambiguous_trajectory_is_preserved_and_suppressed(self):
        t = track()
        result = BehaviorEngine().evaluate(track=t, activity=activity(t), trajectory=trajectory("AMBIGUOUS"))
        self.assertTrue(result.ambiguous)
        self.assertIsNone(result.risk_event)

    def test_disabled_engine_is_fail_safe(self):
        result = BehaviorEngine({"behavior": {"enabled": False}}).evaluate(track=track())
        self.assertEqual(result.features, ())

    def test_invalid_config_is_rejected(self):
        with self.assertRaises(ValueError):
            BehaviorEngine({"behavior": {"retention": {"max_results": 0}}})


class TestIsolationAndRetention(unittest.TestCase):
    def test_retention_is_bounded(self):
        engine = BehaviorEngine({"behavior": {"retention": {"max_results": 2}}})
        for i in range(5):
            engine.evaluate(track=track(tid=f"T-{i}"))
        self.assertEqual(engine.metrics()["retained_results"], 2)

    def test_track_results_are_isolated(self):
        engine = BehaviorEngine()
        first = engine.evaluate(track=track(tid="T-A"))
        second = engine.evaluate(track=track(tid="T-B", seconds=5, events=1))
        self.assertNotEqual(first.subject_ref, second.subject_ref)
        self.assertEqual(second.signals, ())

    def test_four_camera_sequence_is_supported(self):
        result = BehaviorEngine().evaluate(track=track(), trajectory=trajectory())
        self.assertEqual(result.camera_ids, ("CAM-001", "CAM-002", "CAM-003", "CAM-004"))


if __name__ == "__main__":
    unittest.main()
