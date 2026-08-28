"""SCENE vertical tests (MACRO-OC-01-R, Block 9).

Covers SCENE_IMPORT (import src.scene) and SCENE_VERTICAL
(ActivityObservation -> SceneObservation -> SceneTrack -> SceneActivity ->
 SceneEvent -> SceneSequence -> EvidenceTimeline), zone adaptation and
interaction events. Asserts the no-accusation taxonomy
(ACTIVITY_REQUIRES_REVIEW only) and full store traceability.
"""

import unittest

from src.behavior.contracts import BehaviorResult, BehaviorSignal, RiskEvent
from src.observations.activity import ActivityObservation
from src.scene import (
    SceneEngine,
    ZoneAdapter,
    ZoneConfig,
)
from src.temporal.contract import LocalTrack, TemporalActivity


def make_observation(
    camera_id="CAM-001",
    observation_id="OBS-1",
    timestamp="2026-08-19T12:00:00.000000Z",
):
    return ActivityObservation(
        observation_id=observation_id,
        camera_id=camera_id,
        timestamp=timestamp,
        observation_type="SIGNAL",
        state="ACTIVE",
        payload={"bbox": [10, 20, 110, 220], "class_name": "person"},
        confidence=0.92,
    )


def make_track(
    track_id="TRK-1",
    camera_id="CAM-001",
    timestamp="2026-08-19T12:00:00.000000Z",
):
    return LocalTrack(
        track_id=track_id,
        camera_id=camera_id,
        object_type="person",
        started_at=timestamp,
        last_seen_at=timestamp,
        status="ACTIVE",
        last_bbox=(10, 20, 110, 220),
        confidence=0.9,
    )


def make_temporal(
    track_id="TRK-1",
    camera_id="CAM-001",
    timestamp="2026-08-19T12:00:00.000000Z",
):
    return TemporalActivity(
        activity_id="ACT-1",
        track_id=track_id,
        source_id=camera_id,
        activity_type="PERSON_PRESENCE",
        started_at=timestamp,
        last_seen_at=timestamp,
        status="ACTIVE",
        duration_ms=1500,
        confidence=0.9,
    )


def make_behavior(track_id="TRK-1", camera_id="CAM-001", risk=65.0):
    signal = BehaviorSignal(
        signal_id="SIG-1",
        signal_type="PROLONGED_DWELL",
        rule_id="R1",
        rule_score=25.0,
        subject_ref=track_id,
        feature_refs=(),
        camera_ids=(camera_id,),
        window_start="2026-08-19T12:00:00.000000Z",
        window_end="2026-08-19T12:01:00.000000Z",
        evidence_refs=("CAM-001/EVD/frame.jpg",),
        status="CANDIDATE",
    )
    risk = RiskEvent(
        risk_event_id="RISK-1",
        risk_event_type="BEHAVIORAL_RISK",
        risk_score=risk,
        status="CONFIRMED",
        subject_ref=track_id,
        signal_refs=("SIG-1",),
        rules_triggered=("R1",),
        camera_ids=(camera_id,),
        window_start="2026-08-19T12:00:00.000000Z",
        window_end="2026-08-19T12:01:00.000000Z",
        evidence_refs=("CAM-001/EVD/frame.jpg",),
        explanation=(("signal", "PROLONGED_DWELL"),),
    )
    return BehaviorResult(
        subject_ref=track_id,
        camera_ids=(camera_id,),
        signals=(signal,),
        risk_event=risk,
        evidence_refs=("CAM-001/EVD/frame.jpg",),
    )


class TestSceneImport(unittest.TestCase):
    def test_scene_module_imports_and_exports_core_contracts(self):
        import src.scene as scene
        for name in (
            "SceneObservation",
            "SceneTrack",
            "SceneActivity",
            "SceneEvent",
            "SceneSequence",
            "EvidenceTimeline",
            "ZoneConfig",
            "InteractionEvent",
            "OperatorInsight",
            "SceneEngine",
            "InteractionIntelligence",
            "ZoneAdapter",
        ):
            self.assertTrue(hasattr(scene, name), name)

    def test_scene_engine_imports_without_broken_dependencies(self):
        engine = SceneEngine(store_id="store_principal")
        self.assertEqual(engine._store_id, "store_principal")


class TestSceneVertical(unittest.TestCase):
    def setUp(self):
        self.engine = SceneEngine(store_id="store_principal")

    def test_observation_adapts_to_scene_observation_with_str_track_id(self):
        obs = make_observation()
        track = make_track()
        scene_obs = self.engine.process_activity_observation(obs, track)[0]
        self.assertIsInstance(scene_obs.track_id, str)
        self.assertEqual(scene_obs.track_id, "TRK-1")
        self.assertEqual(scene_obs.bbox, (10, 20, 110, 220))
        self.assertEqual(scene_obs.camera_id, "CAM-001")
        self.assertEqual(scene_obs.observation_ref, "OBS-1")

    def test_observation_track_activity_vertical_with_store_traceability(self):
        obs = make_observation()
        track = make_track()
        temporal = TemporalActivity(
            activity_id="ACT-1",
            track_id="TRK-1",
            source_id="CAM-001",
            activity_type="PERSON_PRESENCE",
            started_at="2026-08-19T12:00:00.000000Z",
            last_seen_at="2026-08-19T12:00:01.500000Z",
            status="ACTIVE",
            duration_ms=1500,
            confidence=0.9,
        )
        result = self.engine.observe(obs, track, temporal)
        scene_obs = result["observations"][0]
        scene_track = result["track"]
        scene_activity = result["activity"]

        self.assertEqual(scene_obs.store_id, "store_principal")
        self.assertEqual(scene_track.store_id, "store_principal")
        self.assertEqual(scene_track.track_id, "TRK-1")
        self.assertEqual(scene_activity.store_id, "store_principal")
        self.assertEqual(scene_activity.activity_type, "PRESENCE")
        self.assertAlmostEqual(scene_activity.duration_seconds, 1.5, places=1)
        self.assertIsInstance(scene_track.track_id, str)

    def test_behavior_result_produces_review_only_events(self):
        behavior = make_behavior(risk=72.0)
        events = self.engine.process_behavior_result(
            behavior, camera_id="CAM-001", track_id="TRK-1"
        )
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.event_type, "ACTIVITY_REQUIRES_REVIEW")
        self.assertNotIn("guilt", event.explanation.lower())
        self.assertEqual(event.risk_score, 72.0)
        self.assertEqual(event.priority, "HIGH")
        self.assertEqual(event.evidence_refs, ("CAM-001/EVD/frame.jpg",))
        self.assertIn("PROLONGED_DWELL", event.explanation)

    def test_event_taxonomy_is_never_accusation(self):
        behavior = make_behavior(risk=95.0)
        events = self.engine.process_behavior_result(
            behavior, camera_id="CAM-001", track_id="TRK-1"
        )
        for event in events:
            self.assertEqual(event.event_type, "ACTIVITY_REQUIRES_REVIEW")

    def test_sequence_builder_traces_camera_path_and_zones(self):
        behavior1 = make_behavior(track_id="TRK-1", camera_id="CAM-001", risk=70.0)
        self.engine.process_temporal_activity(
            make_temporal(track_id="TRK-1", camera_id="CAM-001")
        )
        self.engine.process_behavior_result(
            behavior1, camera_id="CAM-001", track_id="TRK-1"
        )
        behavior2 = BehaviorResult(
            subject_ref="TRK-1",
            camera_ids=("CAM-002",),
            signals=behavior1.signals,
            risk_event=behavior1.risk_event,
            evidence_refs=(),
        )
        self.engine.process_behavior_result(
            behavior2, camera_id="CAM-002", track_id="TRK-1"
        )
        sequences = self.engine.build_scene_sequences()
        self.assertEqual(len(sequences), 1)
        sequence = sequences[0]
        self.assertEqual(sequence.track_id, "TRK-1")
        self.assertEqual(sequence.store_id, "store_principal")
        self.assertEqual(tuple(sequence.camera_path), ("CAM-001", "CAM-002"))
        self.assertEqual(len(sequence.events), 2)

    def test_evidence_timeline_accumulates_items(self):
        self.engine.add_evidence_to_timeline("TRK-1", {
            "type": "jpg", "path": "evidence/store/cam-001/frame.jpg",
            "timestamp": "2026-08-19T12:00:00Z", "camera_id": "CAM-001",
        })
        timeline = self.engine.get_evidence_timeline("TRK-1")
        self.assertEqual(len(timeline.evidence_items), 1)
        self.assertEqual(timeline.store_id, "store_principal")
        self.assertEqual(timeline.track_id, "TRK-1")
        self.assertEqual(timeline.evidence_items[0]["type"], "jpg")


class TestZoneAdapter(unittest.TestCase):
    def test_rectangle_and_polygon_containment(self):
        adapter = ZoneAdapter([
            ZoneConfig(
                zone_id="ZONE-CAJA", zone_name="Caja", zone_type="RECTANGLE",
                rectangle=(0, 0, 100, 100), camera_id="CAM-001",
            ),
            ZoneConfig(
                zone_id="ZONE-PASILLO", zone_name="Pasillo", zone_type="POLYGON",
                polygon=((0, 0), (100, 0), (50, 100)), camera_id="CAM-001",
            ),
        ])
        self.assertTrue(adapter.contains_point("ZONE-CAJA", 50, 50))
        self.assertFalse(adapter.contains_point("ZONE-CAJA", 200, 200))
        self.assertTrue(adapter.contains_point("ZONE-PASILLO", 50, 30))
        self.assertFalse(adapter.contains_point("ZONE-PASILLO", 20, 80))
        self.assertIsNone(adapter.get_zone_for_point("CAM-001", 500, 500))

    def test_unknown_zone_never_matches(self):
        adapter = ZoneAdapter([])
        self.assertFalse(adapter.contains_point("ZONE-X", 0, 0))


class TestInteractionIntelligence(unittest.TestCase):
    def test_zone_entry_exit_and_poi_approach(self):
        from src.scene import InteractionIntelligence
        adapter = ZoneAdapter([
            ZoneConfig(
                zone_id="ZONE-CAJA", zone_name="Caja", zone_type="RECTANGLE",
                rectangle=(0, 0, 200, 200), camera_id="CAM-001",
            ),
        ])
        ii = InteractionIntelligence(adapter, store_id="store_principal")
        ii.register_poi("POI-RACK", x=100, y=100, radius=50)
        track = make_track(timestamp="2026-08-19T12:00:00.000000Z")
        events = ii.process_track(track, "CAM-001")
        types = {event.interaction_type for event in events}
        self.assertIn("ZONE_ENTRY", types)
        self.assertIn("POI_APPROACH", types)
        for event in events:
            self.assertEqual(event.store_id, "store_principal")


if __name__ == "__main__":
    unittest.main()