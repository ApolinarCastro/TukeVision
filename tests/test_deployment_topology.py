"""DEPLOYMENT vertical tests (MACRO-OC-01-R, Block 9).

Covers DEPLOYMENT_TESTS: import src.deployment, edge/central split
validation, full topology validation and central aggregation
(health, events, review, search). Asserts the edge->central upstream data
never carries full-resolution video streams.
"""

import unittest

from src.deployment.topology import (
    CentralQueryService,
    DeploymentTopology,
    EdgeCaptureService,
    EdgeCentralSplit,
)
from src.deployment import (
    CentralCapability,
    EdgeCapability,
    StoreDeployment,
)
from src.domain.models import (
    CameraConfig,
    OrganizationConfig,
    SourceType,
    StoreConfig,
)
from src.observability.system_health import SystemHealthSnapshot


def make_camera(camera_id="CAM-001"):
    return CameraConfig(
        camera_id=camera_id,
        store_id="store_a",
        recorder_id=None,
        channel_number=1,
        camera_name=camera_id,
        source_type=SourceType.VIDEO_FILE,
        stream_main=f"videos/{camera_id}.mp4",
        stream_sub=f"videos/{camera_id}_sub.mp4",
        zone="Zona",
        role="HYBRID",
        enabled=True,
        host="",
    )


def make_store(store_id="store_a", camera_ids=("CAM-001",)):
    return StoreConfig(
        store_id=store_id,
        organization_id="org_1",
        store_name=f"Tienda {store_id}",
        location_address=f"Av. {store_id} 100",
        timezone="America/Santiago",
        evidence_namespace=f"data/evidence/{store_id}/",
        direct_cameras=[make_camera(c) for c in camera_ids],
    )


def make_organization():
    return OrganizationConfig(
        organization_id="org_1",
        organization_name="Org Demo",
        created_at="2026-08-19T00:00:00Z",
        stores=[make_store("store_a"), make_store("store_b", ("CAM-101",))],
    )


def make_health(store_id, online=2, total=2, status="OK"):
    return SystemHealthSnapshot(
        timestamp="2026-08-19T12:00:00Z",
        cpu_percent=10.0,
        ram_percent=40.0,
        ram_used_mb=2048.0,
        ram_total_mb=8192.0,
        disk_percent=30.0,
        disk_free_gb=120.0,
        camera_health=(),
        store_health=(),
        online_camera_count=online,
        total_camera_count=total,
        global_health=status,
    )


class FakeEdgeRuntime:
    def __init__(self):
        self.start_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1


class TestDeploymentImport(unittest.TestCase):
    def test_deployment_module_imports(self):
        import src.deployment as deployment
        for name in (
            "CentralCapability",
            "CentralQueryService",
            "DeploymentTopology",
            "EdgeCapability",
            "EdgeCaptureService",
            "EdgeCentralSplit",
            "StoreDeployment",
        ):
            self.assertTrue(hasattr(deployment, name), name)


class TestEdgeCentralSplit(unittest.TestCase):
    def test_default_split_is_valid(self):
        split = EdgeCentralSplit(store_id="store_a")
        valid, errors = split.validate()
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_invalid_stream_budget_is_rejected(self):
        split = EdgeCentralSplit(
            store_id="store_a",
            edge=EdgeCapability(max_cameras=4, max_concurrent_streams=8),
        )
        valid, errors = split.validate()
        self.assertFalse(valid)
        self.assertTrue(any("max_concurrent_streams" in e for e in errors))

    def test_upstream_never_carries_full_resolution_video(self):
        split = EdgeCentralSplit(store_id="store_a")
        self.assertNotIn("video_streams", split.upstream_data)
        self.assertNotIn("frames", split.upstream_data)
        self.assertIn("health_snapshots", split.upstream_data)


class TestTopologyAndCentral(unittest.TestCase):
    def setUp(self):
        self.topology = DeploymentTopology(make_organization())
        self.topology.add_store(
            make_store("store_a"),
            EdgeCentralSplit(store_id="store_a"),
        )
        self.topology.add_store(
            make_store("store_b", ("CAM-101",)),
            EdgeCentralSplit(store_id="store_b"),
        )

    def test_topology_validates(self):
        valid, errors = self.topology.validate()
        self.assertTrue(valid, errors)

    def test_central_aggregates_health_across_stores(self):
        central = self.topology.get_central_service()
        central.ingest_store_health("store_a", make_health("store_a", online=2, status="OK"))
        central.ingest_store_health("store_b", make_health("store_b", online=0, status="OFFLINE"))
        global_health = central.get_global_health()
        self.assertEqual(global_health["total_stores"], 2)
        self.assertEqual(global_health["total_cameras"], 4)
        self.assertEqual(global_health["online_cameras"], 2)
        self.assertEqual(global_health["global_status"], "OFFLINE")

    def test_central_searches_events_by_store_type_and_risk(self):
        central = self.topology.get_central_service()
        central.ingest_store_events("store_a", [
            {"type": "ACTIVITY_REQUIRES_REVIEW", "risk_score": 70.0,
             "timestamp_utc": "2026-08-19T12:00:00Z"},
            {"type": "OTHER", "risk_score": 20.0,
             "timestamp_utc": "2026-08-19T12:05:00Z"},
        ])
        central.ingest_store_events("store_b", [
            {"type": "ACTIVITY_REQUIRES_REVIEW", "risk_score": 90.0,
             "timestamp_utc": "2026-08-19T12:10:00Z"},
        ])
        results = central.search_events(store_ids=("store_a",))
        self.assertEqual(len(results), 2)
        flagged = central.search_events(
            event_types=("ACTIVITY_REQUIRES_REVIEW",), min_risk=80.0,
        )
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["store_id"], "store_b")

    def test_edge_service_factory_and_review_queue(self):
        service = self.topology.create_edge_service("store_a")
        self.assertIsInstance(service, EdgeCaptureService)
        central = self.topology.get_central_service()
        central.ingest_review_record({"case_id": "C1", "label": "USEFUL_SIGNAL"})
        self.assertEqual(len(central.get_review_queue()), 1)

    def test_edge_service_without_runtime_fails_closed(self):
        service = self.topology.create_edge_service("store_a")
        with self.assertRaises(RuntimeError):
            service.start()

    def test_topology_injects_and_delegates_the_real_edge_runtime(self):
        runtime = FakeEdgeRuntime()
        topology = DeploymentTopology(
            make_organization(),
            edge_runtime_provider=lambda store_id: runtime,
        )
        topology.add_store(
            make_store("store_a"),
            EdgeCentralSplit(store_id="store_a"),
        )

        service = topology.create_edge_service("store_a")
        self.assertIs(service.runtime, runtime)
        service.start()
        service.stop()

        self.assertEqual(runtime.start_calls, 1)
        self.assertEqual(runtime.stop_calls, 1)


if __name__ == "__main__":
    unittest.main()
