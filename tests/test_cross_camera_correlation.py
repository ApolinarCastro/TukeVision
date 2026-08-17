"""LOOP-0018W deterministic temporal/topological correlation contracts."""

import json
import unittest

import numpy as np

from src.app.advance_chain import AdvanceChain
from src.correlation.contracts import AMBIGUOUS, CANDIDATE
from src.correlation.correlator import CrossCameraCorrelator
from src.correlation.topology import (
    TRANSITION_ALLOWED,
    TRANSITION_DISABLED,
    TRANSITION_NOT_CONFIGURED,
    CameraTopology,
)
from src.temporal.contract import ENDED, LocalTrack


def ts(seconds):
    return f"2026-08-17T12:00:{seconds:02d}Z"


def track(camera, number, start, end, evidence=None, object_type="object"):
    return LocalTrack(
        track_id=f"TRK-{camera}-{number:03d}", camera_id=camera,
        object_type=object_type, started_at=ts(start), last_seen_at=ts(end),
        status=ENDED, event_count=1,
        evidence_refs={"first": evidence, "latest": evidence, "best": evidence},
    )


def correlation_config(transitions=None, **overrides):
    block = {
        "enabled": True,
        "transitions": transitions or [
            {"source_camera": "CAM-01", "target_camera": "CAM-02",
             "min_transition_seconds": 1, "max_transition_seconds": 10,
             "enabled": True, "weight": 1.0},
            {"source_camera": "CAM-02", "target_camera": "CAM-03",
             "min_transition_seconds": 1, "max_transition_seconds": 10,
             "enabled": True, "weight": 0.9},
        ],
        "score_weights": {"temporal": 0.7, "topology": 0.3, "direction": 0.0},
        "max_active_trajectories": 8,
        "max_candidates_per_camera_pair": 3,
        "candidate_ttl_seconds": 60,
        "trajectory_ttl_seconds": 120,
    }
    block.update(overrides)
    return {"correlation": block}


class TestTopologyContract(unittest.TestCase):
    def test_allowed_disabled_and_not_configured(self):
        cfg = correlation_config(transitions=[
            {"source_camera": "CAM-01", "target_camera": "CAM-02",
             "min_transition_seconds": 1, "max_transition_seconds": 5,
             "enabled": True},
            {"source_camera": "CAM-02", "target_camera": "CAM-04",
             "min_transition_seconds": 1, "max_transition_seconds": 5,
             "enabled": False},
        ])
        topology = CameraTopology.from_config(cfg)
        self.assertEqual(topology.transition_state("CAM-01", "CAM-02"), TRANSITION_ALLOWED)
        self.assertEqual(topology.transition_state("CAM-02", "CAM-04"), TRANSITION_DISABLED)
        self.assertEqual(topology.transition_state("CAM-01", "CAM-04"), TRANSITION_NOT_CONFIGURED)

    def test_topology_rejects_invalid_window(self):
        with self.assertRaises(ValueError):
            CameraTopology.from_config(correlation_config(transitions=[
                {"source_camera": "A", "target_camera": "B",
                 "min_transition_seconds": 9, "max_transition_seconds": 2}
            ]))


class TestCorrelationFiltering(unittest.TestCase):
    def setUp(self):
        self.correlator = CrossCameraCorrelator.from_config(correlation_config())

    def test_valid_cam01_to_cam02(self):
        self.correlator.ingest(track("CAM-01", 1, 0, 5, "CAM-01/E1/frame.jpg"))
        result = self.correlator.ingest(track("CAM-02", 14, 8, 9, "CAM-02/E2/frame.jpg"))
        self.assertIsNotNone(result.link)
        self.assertEqual(result.link.status, CANDIDATE)
        self.assertEqual(dict(result.link.score_components).keys(), {"temporal_score", "topology_score", "direction_score"})

    def test_outside_window_rejected(self):
        self.correlator.ingest(track("CAM-01", 1, 0, 5))
        self.assertIsNone(self.correlator.ingest(track("CAM-02", 2, 20, 21)).link)

    def test_not_configured_and_same_camera_rejected(self):
        self.correlator.ingest(track("CAM-01", 1, 0, 5))
        self.assertIsNone(self.correlator.ingest(track("CAM-04", 2, 8, 9)).link)
        self.assertIsNone(self.correlator.ingest(track("CAM-01", 3, 8, 9)).link)

    def test_target_before_source_rejected(self):
        self.correlator.ingest(track("CAM-01", 1, 10, 15))
        self.assertIsNone(self.correlator.ingest(track("CAM-02", 2, 8, 9)).link)

    def test_incompatible_object_type_rejected(self):
        self.correlator.ingest(track("CAM-01", 1, 0, 5, object_type="person"))
        self.assertIsNone(self.correlator.ingest(track("CAM-02", 2, 8, 9, object_type="vehicle")).link)


class TestTrajectoryGraph(unittest.TestCase):
    def test_three_camera_trajectory_and_evidence(self):
        correlator = CrossCameraCorrelator.from_config(correlation_config())
        correlator.ingest(track("CAM-01", 1, 0, 5, "CAM-01/E1/frame.jpg"))
        first = correlator.ingest(track("CAM-02", 14, 8, 10, "CAM-02/E2/frame.jpg"))
        final = correlator.ingest(track("CAM-03", 8, 13, 15, "CAM-03/E3/frame.jpg"))
        trajectory = final.trajectory
        self.assertIsNotNone(first.trajectory)
        self.assertEqual(trajectory.camera_sequence, ("CAM-01", "CAM-02", "CAM-03"))
        self.assertEqual(len(trajectory.edges), 2)
        self.assertEqual(len(trajectory.evidence_refs), 3)
        self.assertEqual(len(set(trajectory.evidence_refs)), 3)
        payload = trajectory.to_dict()
        self.assertEqual(payload["track_sequence"][1], "TRK-CAM-02-014")
        self.assertNotIn("image", json.dumps(payload).lower())

    def test_ambiguity_is_preserved_without_forced_link(self):
        correlator = CrossCameraCorrelator.from_config(correlation_config())
        correlator.ingest(track("CAM-01", 1, 0, 5))
        correlator.ingest(track("CAM-01", 2, 1, 6))
        result = correlator.ingest(track("CAM-02", 3, 8, 9))
        self.assertIsNone(result.link)
        self.assertEqual(len(result.candidates), 2)
        self.assertTrue(all(candidate.status == AMBIGUOUS for candidate in result.candidates))

    def test_four_camera_isolation_and_configurable_edges(self):
        transitions = correlation_config()["correlation"]["transitions"] + [
            {"source_camera": "CAM-03", "target_camera": "CAM-04",
             "min_transition_seconds": 1, "max_transition_seconds": 10,
             "enabled": True}
        ]
        correlator = CrossCameraCorrelator.from_config(correlation_config(transitions))
        results = []
        for camera, number, start, end in (
            ("CAM-01", 1, 0, 5), ("CAM-02", 2, 8, 10),
            ("CAM-03", 3, 13, 15), ("CAM-04", 4, 18, 20),
        ):
            results.append(correlator.ingest(track(camera, number, start, end, f"{camera}/E/frame.jpg")))
        self.assertEqual(results[-1].trajectory.camera_sequence, ("CAM-01", "CAM-02", "CAM-03", "CAM-04"))
        self.assertEqual({node.camera_id for node in results[-1].trajectory.nodes}, {"CAM-01", "CAM-02", "CAM-03", "CAM-04"})


class TestBoundedState(unittest.TestCase):
    def test_candidate_retention_bounded_per_pair(self):
        cfg = correlation_config(max_candidates_per_camera_pair=2)
        correlator = CrossCameraCorrelator.from_config(cfg)
        correlator.ingest(track("CAM-01", 1, 0, 5))
        correlator.ingest(track("CAM-01", 2, 0, 5))
        for number in range(10, 14):
            correlator.ingest(track("CAM-02", number, 8, 9))
        self.assertLessEqual(correlator.metrics()["candidate_count"], 2)

    def test_trajectory_count_and_ttl_bounded(self):
        cfg = correlation_config(max_active_trajectories=1, trajectory_ttl_seconds=15)
        correlator = CrossCameraCorrelator.from_config(cfg)
        correlator.ingest(track("CAM-01", 1, 0, 5))
        correlator.ingest(track("CAM-02", 2, 8, 9))
        correlator.ingest(track("CAM-01", 3, 20, 25))
        correlator.ingest(track("CAM-02", 4, 28, 29))
        self.assertLessEqual(len(correlator.trajectories()), 1)

    def test_reset_and_close_clean(self):
        correlator = CrossCameraCorrelator.from_config(correlation_config())
        correlator.ingest(track("CAM-01", 1, 0, 5))
        correlator.reset()
        self.assertEqual(correlator.metrics()["track_count"], 0)
        correlator.close()
        with self.assertRaises(RuntimeError):
            correlator.ingest(track("CAM-01", 2, 0, 5))

    def test_evicted_track_linkage_state_is_bounded(self):
        transitions = [
            {"source_camera": "CAM-01", "target_camera": "CAM-02",
             "min_transition_seconds": 0, "max_transition_seconds": 5, "enabled": True},
            {"source_camera": "CAM-02", "target_camera": "CAM-01",
             "min_transition_seconds": 0, "max_transition_seconds": 5, "enabled": True},
        ]
        cfg = correlation_config(transitions, max_tracks=2)
        correlator = CrossCameraCorrelator.from_config(cfg)
        for number in range(1, 9):
            camera = "CAM-01" if number % 2 else "CAM-02"
            correlator.ingest(track(camera, number, number * 3, number * 3 + 1))
        metrics = correlator.metrics()
        self.assertLessEqual(metrics["track_count"], 2)
        self.assertLessEqual(metrics["association_count"], 4)

    def test_serialized_contract_has_no_identity_or_biometrics(self):
        correlator = CrossCameraCorrelator.from_config(correlation_config())
        correlator.ingest(track("CAM-01", 1, 0, 5))
        result = correlator.ingest(track("CAM-02", 2, 8, 9))
        serialized = json.dumps(result.trajectory.to_dict()).lower()
        for forbidden in ("same_person", "identified_person", "embedding", "biometric", "reid"):
            self.assertNotIn(forbidden, serialized)


class TestAdvanceChainComposition(unittest.TestCase):
    def test_operational_result_exposes_three_camera_trajectory(self):
        class Manager:
            def list_sources(self):
                return [{"camera_id": camera, "running": False} for camera in ("CAM-01", "CAM-02", "CAM-03")]
            def health(self, camera_id):
                return type("Health", (), {"fps": 15.0})()

        cfg = correlation_config()
        cfg.update({
            "observation": {"default_profile": "BALANCED", "profiles": {
                "QUALITY": {"max_analysis_fps": 5.0}, "BALANCED": {"max_analysis_fps": 2.0},
                "ECONOMY": {"max_analysis_fps": 1.0}}},
            "inference": {"backend": "deterministic", "confidence_threshold": 0.5,
                "event_queue_maxlen": 4, "event_queue_overflow": "drop_oldest",
                "events": [{"type": "OBJECT_DETECTED", "min_confidence": 0.5}]},
            "temporal": {"association_window_ms": 2000, "track_timeout_ms": 5000,
                "iou_threshold": 0.05, "max_active_tracks": 8, "max_completed_history": 8,
                "max_event_refs": 4, "max_evidence_refs": 3},
        })
        cfg["correlation"]["transitions"][0]["min_transition_seconds"] = 0
        cfg["correlation"]["transitions"][1]["min_transition_seconds"] = 0
        frame = np.zeros((80, 120, 3), dtype="uint8")
        frame[10:60, 30:90] = 255
        chain = AdvanceChain.build(cfg, Manager())
        chain.register_from_source_manager()
        chain.feed("CAM-01", 0, 15.0, frame)
        chain.feed("CAM-02", 0, 15.0, frame)
        result = chain.feed("CAM-03", 0, 15.0, frame)
        self.assertIsNotNone(result["correlation"].trajectory)
        self.assertEqual(result["correlation"].trajectory.camera_sequence, ("CAM-01", "CAM-02", "CAM-03"))
        self.assertIn("correlation", chain.summary())
        chain.close()


if __name__ == "__main__":
    unittest.main()
