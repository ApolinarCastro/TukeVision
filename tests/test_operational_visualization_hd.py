"""Phase 12 Test Suite: Operational Intelligence Visualization & HD Vision.

Validates VideoQualityProfile, 2D Spatial Map, Health Explainability,
Agent Monitor presentation, Evidence Selector, Governed Actions, Experience context,
and Command Center modes.
"""

import unittest
from datetime import datetime, timezone

from src.capture.quality_profile import (
    AdaptiveVideoQualityManager,
    QualityState,
    ResolutionClassification,
    VideoQualityProfile,
)
from src.spatial.contract import (
    CameraCoverage,
    CameraSpatialModel,
    ObservationState,
    SpatialEntityState,
    SpatialTrajectoryPoint,
    StoreCoordinate,
)
from src.ui.tk_operational_panels import (
    OperationalCommandCenterModes,
    OperationalPanelsController,
)
from src.visualization.health_explainer import HealthExplainer
from src.visualization.operational_intelligence import (
    EvidenceBundleViewItem,
    ExperienceContextViewItem,
    GovernedActionViewItem,
    InvestigationViewItem,
    OperationalIntelligenceViewModel,
    OperatorTimelineEvent,
    SituationViewItem,
)
from src.visualization.spatial_map import (
    HandoffVisualVector,
    MapZone,
    SpatialMapModel,
)


class TestHDVideoQuality(unittest.TestCase):
    """Tests for HD video quality profiles, adaptive streams, and resolution decoupling."""

    def test_video_quality_profile_and_adaptive_resolutions(self):
        manager = AdaptiveVideoQualityManager()
        profile = manager.register_camera(
            camera_id="CAM-01",
            native_width=1920,
            native_height=1080,
            codec="H.264",
        )
        self.assertEqual(profile.quality_state, QualityState.ADAPTIVE_HD)
        self.assertEqual(profile.get_resolution_for_mode("GRID"), (352, 240))
        self.assertEqual(profile.get_resolution_for_mode("FOCUS"), (1920, 1080))
        self.assertEqual(profile.get_resolution_for_mode("INFERENCE"), (640, 360))
        self.assertEqual(profile.get_resolution_for_mode("EVIDENCE"), (1920, 1080))

        # Under resource critical pressure, focus resolution adapts safely
        manager.update_resource_state("CRITICAL")
        self.assertEqual(profile.quality_state, QualityState.DEGRADED_RESOURCE)
        self.assertEqual(profile.get_resolution_for_mode("FOCUS"), (640, 360))

        # Recovery to normal
        manager.update_resource_state("NORMAL")
        self.assertEqual(profile.quality_state, QualityState.ADAPTIVE_HD)
        self.assertEqual(profile.get_resolution_for_mode("FOCUS"), (1920, 1080))

    def test_small_object_resolution_and_confidence(self):
        profile_hd = VideoQualityProfile(
            camera_id="CAM-01",
            native_width=1920,
            native_height=1080,
            inference_width=640,
            inference_height=360,
        )
        profile_sd = VideoQualityProfile(
            camera_id="CAM-02",
            native_width=352,
            native_height=240,
            inference_width=352,
            inference_height=240,
        )
        self.assertGreater(profile_hd.inference_width, profile_sd.inference_width)
        self.assertGreater(profile_hd.focus_width, profile_sd.focus_width)


class TestSpatialMapVisualization(unittest.TestCase):
    """Tests for 2D floor plan, viewsheds, trajectories, and handoffs."""

    def test_2d_spatial_map_rendering_and_viewsheds(self):
        model = SpatialMapModel(store_width_m=40.0, store_height_m=25.0)

        # Add zone
        model.add_zone(MapZone("Z1", "Entrance Zone", [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]))

        # Add calibrated camera with coverage
        coverage = CameraCoverage(polygon_points=[
            StoreCoordinate(5.0, 5.0),
            StoreCoordinate(15.0, 5.0),
            StoreCoordinate(15.0, 15.0),
            StoreCoordinate(5.0, 15.0),
        ])
        cam_model = CameraSpatialModel(
            camera_id="CAM-01",
            position_store=StoreCoordinate(10.0, 2.0),
            orientation_yaw_deg=45.0,
            field_of_view_deg=85.0,
            coverage=coverage,
            calibration_version="1.0.0",
        )
        model.add_camera(cam_model)

        # Add entity with trajectory
        entity = SpatialEntityState(
            entity_id="ENT-001",
            current_store_position=StoreCoordinate(12.0, 8.0),
            previous_store_position=StoreCoordinate(11.0, 7.0),
            velocity_vector=(0.5, 0.2),
            direction_deg=45.0,
            current_zone="Z1",
            previous_zone=None,
            active_camera="CAM-01",
            candidate_cameras=["CAM-01", "CAM-02"],
            trajectory=[
                SpatialTrajectoryPoint(10.0, 6.0, "2026-08-29T12:00:00Z", "CAM-01", 0.95, ObservationState.LIVE_OBSERVED),
                SpatialTrajectoryPoint(11.0, 7.0, "2026-08-29T12:00:01Z", "CAM-01", 0.96, ObservationState.LIVE_OBSERVED),
                SpatialTrajectoryPoint(12.0, 8.0, "2026-08-29T12:00:02Z", "CAM-01", 0.98, ObservationState.LIVE_OBSERVED),
            ],
            observation_state=ObservationState.LIVE_OBSERVED,
            confidence=0.98,
            freshness=24.0,
            last_observed_at="2026-08-29T12:00:02Z",
        )
        model.update_entity(entity)

        # Record handoff
        model.record_handoff(HandoffVisualVector(
            from_camera="CAM-01",
            to_camera="CAM-02",
            zone_id="Z1",
            entity_id="ENT-001",
            confidence=0.92,
            status="CONFIRMED_BY_RULE",
            start_point=(12.0, 8.0),
            end_point=(14.0, 9.0),
        ))

        primitives = model.to_render_primitives(canvas_width=800, canvas_height=600)
        self.assertEqual(len(primitives["zones"]), 1)
        self.assertEqual(len(primitives["cameras"]), 1)
        self.assertEqual(len(primitives["entities"]), 1)
        self.assertEqual(len(primitives["handoffs"]), 1)
        self.assertEqual(primitives["entities"][0]["entity_id"], "ENT-001")


class TestHealthExplainability(unittest.TestCase):
    """Tests for granular diagnostics and explainable health degradation."""

    def test_health_explainability_granular_breakdown(self):
        # Degraded cameras
        components = {
            "CAMERAS": {"degraded_cameras": ["CAM-04"], "max_freshness_ms": 120.0},
            "INFERENCE": {"status": "HEALTHY"},
            "STORAGE": {"free_space_gb": 120.0},
        }
        details = HealthExplainer.explain_health("DEGRADED", components, {"cpu_percent": 43.5, "rss_mb": 2520})
        self.assertTrue(any(d.component == "CAMERAS" and d.status == "DEGRADED" for d in details))
        self.assertIn("CAM-04", details[0].affected_channels)

        # Memory constrained
        details_mem = HealthExplainer.explain_health("DEGRADED", {}, {"cpu_percent": 43.5, "rss_mb": 7200})
        self.assertTrue(any(d.component == "RESOURCES_MEMORY" and d.status == "WARNING" for d in details_mem))


class TestOperationalIntelligenceModel(unittest.TestCase):
    """Tests for end-to-end operational intelligence view model and timeline."""

    def test_operational_intelligence_view_model_and_timeline(self):
        vm = OperationalIntelligenceViewModel()

        # Record situation
        vm.record_situation(SituationViewItem(
            situation_id="SIT-01",
            situation_type="PERSISTENT_LOITERING",
            camera_ids=["CAM-01"],
            zone_ids=["Z1"],
            entity_ids=["ENT-001"],
            started_at="2026-08-29T12:00:00Z",
            duration_seconds=45.0,
            status="ACTIVE",
            confidence=0.95,
        ))

        # Record investigation
        vm.record_investigation(InvestigationViewItem(
            investigation_id="INV-01",
            candidate_id="SIT-01",
            situation_type="PERSISTENT_LOITERING",
            priority="HIGH",
            reasoning_level="LOCAL_LLM",
            facts=["Entity present in zone for 45s", "No interaction with cashier"],
            inferences=["Potential assistance required"],
            unknowns=["Customer intent"],
            evidence_bundle_ids=["EVD-001"],
            recommended_action="DISPATCH_ASSISTANCE_ALERT",
            status="COMPLETED",
            updated_at="2026-08-29T12:00:45Z",
        ))

        # Record evidence bundle
        vm.record_evidence_bundle(EvidenceBundleViewItem(
            bundle_id="EVD-001",
            source_camera="CAM-01",
            observed_at="2026-08-29T12:00:45Z",
            entity_id="ENT-001",
            situation_id="SIT-01",
            confidence=0.95,
            detector_runtime="openvino",
            model_id="yolov8n-openvino",
            hashes={"key_frame.jpg": "abcdef123456"},
            key_frame_path="data/evidence/key_frame.jpg",
            roi_crop_path="data/evidence/roi.jpg",
        ))

        # Record governed action
        vm.record_action(GovernedActionViewItem(
            action_id="ACT-01",
            action_type="ALERT_DISPATCH",
            target_channel="CAM-01",
            site_id="SITE-A",
            autonomy_level="AUTONOMY_2",
            autonomy_3_status="DISABLED",
            policy_decision="ALLOW",
            operator_review_required=False,
            execution_status="VERIFIED",
            outcome="SUCCESS",
        ))

        # Record experience
        vm.record_experience(ExperienceContextViewItem(
            experience_id="EXP-01",
            failure_signature="STREAM_STALL_RECONNECT",
            root_cause="Transient RTSP TCP reset",
            proven_resolution="Supervisor reconnect in <2s",
            recurrence_count=3,
        ))

        timeline = vm.build_operator_timeline("INV-01")
        self.assertEqual(len(timeline), 10)
        self.assertEqual(timeline[0].stage, "OBSERVATION")
        self.assertEqual(timeline[5].stage, "REASONING")
        self.assertEqual(timeline[6].stage, "ACTION")
        self.assertEqual(timeline[9].stage, "EXPERIENCE")

    def test_governed_action_autonomy_and_policy_visibility(self):
        action = GovernedActionViewItem(
            action_id="ACT-02",
            action_type="PTZ_PRESET",
            target_channel="CAM-01",
            site_id="SITE-A",
            autonomy_level="AUTONOMY_2",
            autonomy_3_status="DISABLED",
            policy_decision="ALLOW",
        )
        self.assertEqual(action.autonomy_3_status, "DISABLED")

    def test_experience_context_distinct_from_facts(self):
        exp = ExperienceContextViewItem(
            experience_id="EXP-02",
            failure_signature="SIG-01",
            root_cause="RC-01",
            proven_resolution="FIX-01",
            recurrence_count=1,
        )
        self.assertEqual(exp.context_type, "HISTORICAL_EXPERIENCE")
        self.assertNotEqual(exp.context_type, "CURRENT_FACT")

    def test_command_center_modes_and_controller(self):
        controller = OperationalPanelsController()
        modes_observed = []
        controller.on_mode_change_callbacks.append(lambda m: modes_observed.append(m))

        for mode in [
            OperationalCommandCenterModes.FOCUS,
            OperationalCommandCenterModes.OPERATIONAL,
            OperationalCommandCenterModes.MAP,
            OperationalCommandCenterModes.INVESTIGATIONS,
            OperationalCommandCenterModes.EVIDENCE,
            OperationalCommandCenterModes.SYSTEM,
            OperationalCommandCenterModes.GRID,
        ]:
            controller.set_mode(mode)

        self.assertEqual(len(modes_observed), 7)
        self.assertEqual(controller.current_mode, OperationalCommandCenterModes.GRID)


if __name__ == "__main__":
    unittest.main()
