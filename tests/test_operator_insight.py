"""OPERATOR vertical tests (MACRO-OC-01-R, Block 9).

Covers OPERATOR_IMPORT (import src.operator) and OPERATOR_VERTICAL:
OperatorInsight generation with full traceability
(store/cameras/tracks/scene events/evidence/timeline) and the structured
OperatorQueryEngine (store/camera/when/why/what filters). Asserts the
no-accusation reason (ACTIVITY_REQUIRES_REVIEW).
"""

import unittest

from src.behavior.contracts import BehaviorSignal, RiskEvent
from src.operator import (
    OperatorInsightGenerator,
    OperatorQuery,
    OperatorQueryEngine,
)
from src.scene.models import EvidenceTimeline, SceneEvent, SceneSequence


def make_sequence(store_id="store_principal"):
    event1 = SceneEvent(
        store_id=store_id,
        camera_ids=("CAM-001",),
        track_ids=("TRK-1",),
        event_type="ACTIVITY_REQUIRES_REVIEW",
        explanation="Track TRK-1 en cámara CAM-001 señal: PROLONGED_DWELL.",
        priority="HIGH",
        risk_score=70.0,
        evidence_refs=("evidence/cam-001/frame.jpg",),
        timestamp_utc="2026-08-19T12:00:00.000000Z",
    )
    event2 = SceneEvent(
        store_id=store_id,
        camera_ids=("CAM-002",),
        track_ids=("TRK-1",),
        event_type="ACTIVITY_REQUIRES_REVIEW",
        explanation="Track TRK-1 en cámara CAM-002 señal: MULTI_CAMERA_SEQUENCE.",
        priority="HIGH",
        risk_score=65.0,
        evidence_refs=(),
        timestamp_utc="2026-08-19T12:01:00.000000Z",
    )
    return SceneSequence(
        track_id="TRK-1",
        store_id=store_id,
        events=(event1, event2),
        start_time="2026-08-19T12:00:00.000000Z",
        end_time="2026-08-19T12:01:00.000000Z",
        camera_path=("CAM-001", "CAM-002"),
        zones_traversed=("Cajas",),
    )


def make_evidence_timeline(store_id="store_principal"):
    timeline = EvidenceTimeline(
        track_id="TRK-1",
        store_id=store_id,
        sequence_id="SEQ-1",
    )
    return timeline.add_evidence({
        "type": "jpg",
        "path": "evidence/cam-001/frame.jpg",
        "timestamp": "2026-08-19T12:00:00Z",
        "camera_id": "CAM-001",
        "event_id": "EV-1",
    })


def make_signal():
    return BehaviorSignal(
        signal_id="SIG-1",
        signal_type="PROLONGED_DWELL",
        rule_id="R1",
        rule_score=25.0,
        subject_ref="TRK-1",
        feature_refs=(),
        camera_ids=("CAM-001",),
        window_start="2026-08-19T12:00:00.000000Z",
        window_end="2026-08-19T12:01:00.000000Z",
    )


def make_risk():
    return RiskEvent(
        risk_event_id="RISK-1",
        risk_event_type="BEHAVIORAL_RISK",
        risk_score=70.0,
        status="CONFIRMED",
        subject_ref="TRK-1",
        signal_refs=("SIG-1",),
        rules_triggered=("R1",),
        camera_ids=("CAM-001",),
        window_start="2026-08-19T12:00:00.000000Z",
        window_end="2026-08-19T12:01:00.000000Z",
        evidence_refs=("evidence/cam-001/frame.jpg",),
        explanation=(("signal", "PROLONGED_DWELL"),),
    )


class TestOperatorImport(unittest.TestCase):
    def test_operator_module_imports_and_exports_core_contracts(self):
        import src.operator as operator
        for name in (
            "OperatorInsightGenerator",
            "OperatorQuery",
            "OperatorQueryEngine",
            "QueryResult",
        ):
            self.assertTrue(hasattr(operator, name), name)


class TestOperatorInsightGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = OperatorInsightGenerator(
            organization_id="org_nicopoly",
            store_id="store_principal",
        )

    def test_insight_traces_store_cameras_tracks_events_evidence(self):
        sequence = make_sequence()
        timeline = make_evidence_timeline()
        insight = self.generator.generate_from_scene_sequence(
            sequence,
            timeline,
            behavior_signals=(make_signal(),),
            risk_events=(make_risk(),),
        )
        self.assertEqual(insight.organization_id, "org_nicopoly")
        self.assertEqual(insight.store_id, "store_principal")
        self.assertEqual(tuple(insight.cameras), ("CAM-001", "CAM-002"))
        self.assertEqual(tuple(insight.tracks), ("TRK-1",))
        self.assertEqual(len(insight.scene_events), 2)
        self.assertEqual(
            insight.timeline_span,
            ("2026-08-19T12:00:00.000000Z", "2026-08-19T12:01:00.000000Z"),
        )
        self.assertIn("evidence/cam-001/frame.jpg", insight.evidence_refs)
        self.assertIn("ACTIVITY_REQUIRES_REVIEW", insight.reason_for_review)
        self.assertNotIn("guilt", insight.reason_for_review.lower())
        self.assertEqual(insight.priority, "HIGH")

    def test_insight_never_accuses(self):
        sequence = make_sequence()
        insight = self.generator.generate_from_scene_sequence(
            sequence, make_evidence_timeline()
        )
        self.assertEqual(insight.reason_for_review, "ACTIVITY_REQUIRES_REVIEW")
        self.assertTrue(insight.recommended_action)


class TestOperatorQueryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = OperatorQueryEngine()
        self.generator = OperatorInsightGenerator(
            organization_id="org_nicopoly",
            store_id="store_principal",
        )
        self.sequence = make_sequence()
        self.timeline = make_evidence_timeline()
        self.insight = self.generator.generate_from_scene_sequence(
            self.sequence,
            self.timeline,
            behavior_signals=(make_signal(),),
            risk_events=(make_risk(),),
        )
        from dataclasses import replace
        self.insight = replace(
            self.insight, timestamp_utc="2026-08-19T12:30:00.000000Z"
        )
        self.engine.index_insight(self.insight)
        self.engine.index_sequence(self.sequence)

    def test_query_by_store(self):
        result = self.engine.query(OperatorQuery(store_id="store_principal"))
        self.assertEqual(result.total_matches, 1)
        self.assertEqual(result.insights[0].store_id, "store_principal")

    def test_query_by_camera(self):
        result = self.engine.query(OperatorQuery(which_cameras=("CAM-002",)))
        self.assertEqual(result.total_matches, 1)

    def test_query_by_time_range(self):
        result = self.engine.query(OperatorQuery(
            store_id="store_principal",
            when=("2026-08-19T11:00:00Z", "2026-08-19T13:00:00Z"),
        ))
        self.assertEqual(result.total_matches, 1)
        outside = self.engine.query(OperatorQuery(
            store_id="store_principal",
            when=("2026-08-19T15:00:00Z", "2026-08-19T16:00:00Z"),
        ))
        self.assertEqual(outside.total_matches, 0)

    def test_query_by_why_and_evidence_collection(self):
        result = self.engine.query(OperatorQuery(
            store_id="store_principal", why="PROLONGED_DWELL",
        ))
        self.assertEqual(result.total_matches, 1)
        self.assertIn("evidence/cam-001/frame.jpg", result.evidence_refs)

    def test_queries_are_isolated_by_store(self):
        other = self.generator.generate_from_scene_sequence(
            make_sequence(store_id="store_norte"),
            make_evidence_timeline(store_id="store_norte"),
        )
        self.engine.index_insight(other)
        result = self.engine.query(OperatorQuery(store_id="store_principal"))
        for insight in result.insights:
            self.assertEqual(insight.store_id, "store_principal")


if __name__ == "__main__":
    unittest.main()