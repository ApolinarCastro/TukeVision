"""Edge vs Central Deployment Architecture (AG-07 / OC-18).

STORE EDGE: capture + inference + evidence (local)
CENTRAL: health + events + review + search (aggregated)

Avoids permanent 16xN full-res streaming.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.domain.models import OrganizationConfig, StoreConfig
from src.observability.system_health import SystemHealthSnapshot


class DeploymentRole(Enum):
    """Deployment role for a component."""
    EDGE = "EDGE"          # Runs at store
    CENTRAL = "CENTRAL"    # Runs at central
    BOTH = "BOTH"          # Runs both places


@dataclass(frozen=True)
class EdgeCapability:
    """Capabilities available at store edge."""
    capture: bool = True
    inference: bool = True
    evidence_storage: bool = True
    local_tracking: bool = True
    temporal_activity: bool = True
    behavior_engine: bool = True
    cross_camera_correlation: bool = False  # Limited to store topology
    evidence_clips: bool = True  # QW-04
    max_cameras: int = 16
    max_concurrent_streams: int = 4  # Sub-streams for grid


@dataclass(frozen=True)
class CentralCapability:
    """Capabilities available at central."""
    health_aggregation: bool = True
    event_aggregation: bool = True
    review_console: bool = True
    search_index: bool = True
    case_memory: bool = True
    learning_dataset: bool = True
    policy_management: bool = True
    multi_store_correlation: bool = True
    operator_insight_generation: bool = True


@dataclass(frozen=True)
class EdgeCentralSplit:
    """Defines which components run where (OC-18).

    Immutable configuration validated at deployment.
    """
    store_id: str
    edge: EdgeCapability = field(default_factory=EdgeCapability)
    central: CentralCapability = field(default_factory=CentralCapability)

    # What data flows edge -> central (never full-res video)
    upstream_data: Tuple[str, ...] = (
        "health_snapshots",      # SystemHealthSnapshot (per-camera, per-store)
        "behavior_events",       # BehaviorSignal, RiskEvent (metadata only)
        "scene_events",          # SceneEvent (metadata + evidence refs)
        "evidence_refs",         # JPEG/MP4 paths (not blobs)
        "review_records",        # Human review labels
        "policy_updates",        # CandidatePolicy diffs
    )

    # What data flows central -> edge
    downstream_data: Tuple[str, ...] = (
        "policy_updates",        # Promoted CurrentPolicy
        "zone_configs",          # ZoneConfig updates
        "model_updates",         # Model weights (if applicable)
        "camera_config_updates", # CameraConfig changes
    )

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate split configuration."""
        errors = []
        if self.edge.max_cameras < 1:
            errors.append("edge.max_cameras must be >= 1")
        if self.edge.max_concurrent_streams > self.edge.max_cameras:
            errors.append("edge.max_concurrent_streams cannot exceed max_cameras")
        return len(errors) == 0, errors


@dataclass(frozen=True)
class StoreDeployment:
    """Deployment spec for a single store."""
    store: StoreConfig
    split: EdgeCentralSplit
    edge_config: dict = field(default_factory=dict)  # Edge-specific config
    central_config: dict = field(default_factory=dict)  # Central-specific config


class CentralQueryService:
    """Central query interface (OC-18).

    Provides: health, events, review, search across stores.
    """

    def __init__(self) -> None:
        self._store_health: Dict[str, SystemHealthSnapshot] = {}
        self._store_events: Dict[str, List[dict]] = defaultdict(list)
        self._review_queue: List[dict] = []

    def ingest_store_health(self, store_id: str, health: SystemHealthSnapshot) -> None:
        """Receive health snapshot from edge."""
        self._store_health[store_id] = health

    def ingest_store_events(self, store_id: str, events: Sequence[dict]) -> None:
        """Receive behavior/scene events from edge."""
        self._store_events[store_id].extend(events)
        # Keep last 1000 events per store
        if len(self._store_events[store_id]) > 1000:
            self._store_events[store_id] = self._store_events[store_id][-1000:]

    def ingest_review_record(self, record: dict) -> None:
        """Receive human review record from edge."""
        self._review_queue.append(record)

    def get_global_health(self) -> Dict[str, Any]:
        """Aggregate health across all stores."""
        total_cameras = 0
        online_cameras = 0
        stores_online = 0
        stores_degraded = 0
        stores_offline = 0

        for store_id, health in self._store_health.items():
            total_cameras += health.total_camera_count
            online_cameras += health.online_camera_count
            if health.global_health == "OK":
                stores_online += 1
            elif health.global_health == "DEGRADED":
                stores_degraded += 1
            else:
                stores_offline += 1

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_stores": len(self._store_health),
            "stores_online": stores_online,
            "stores_degraded": stores_degraded,
            "stores_offline": stores_offline,
            "total_cameras": total_cameras,
            "online_cameras": online_cameras,
            "global_status": "OK" if stores_offline == 0 and stores_degraded == 0 else
                           "DEGRADED" if stores_offline == 0 else "OFFLINE",
        }

    def get_store_health(self, store_id: str) -> Optional[SystemHealthSnapshot]:
        """Get health for specific store."""
        return self._store_health.get(store_id)

    def search_events(
        self,
        store_ids: Optional[Sequence[str]] = None,
        event_types: Optional[Sequence[str]] = None,
        time_range: Optional[Tuple[str, str]] = None,
        min_risk: Optional[float] = None,
    ) -> List[dict]:
        """Search aggregated events across stores."""
        results = []
        for sid, events in self._store_events.items():
            if store_ids and sid not in store_ids:
                continue
            for ev in events:
                if event_types and ev.get("type") not in event_types:
                    continue
                if min_risk and ev.get("risk_score", 0) < min_risk:
                    continue
                if time_range:
                    ts = ev.get("timestamp_utc", "")
                    if not (time_range[0] <= ts <= time_range[1]):
                        continue
                results.append({**ev, "store_id": sid})
        return results

    def get_review_queue(self, limit: int = 50) -> List[dict]:
        """Get pending review cases."""
        return self._review_queue[-limit:]


class EdgeCaptureService:
    """Edge capture and inference service (OC-18).

    Runs at store: SourceManager -> Pipeline -> Evidence.
    """

    def __init__(
        self,
        store: StoreConfig,
        split: EdgeCentralSplit,
        central_callback: Optional[Callable[[str, Any], None]] = None,
        runtime: Optional[Any] = None,
    ) -> None:
        self._store = store
        self._split = split
        self._central_callback = central_callback
        self._runtime = runtime
        self._running = False

    def start(self) -> None:
        """Start edge services.

        When a real StoreEdgeRuntime is attached, edge processing is
        delegated to it (MACRO-OC-02-D).  A service without that runtime fails
        closed instead of reporting a boolean-only false start.
        """
        if self._runtime is None:
            raise RuntimeError("edge runtime is not configured")
        self._runtime.start()
        self._running = True

    def stop(self) -> None:
        """Stop edge services."""
        if self._runtime is not None:
            self._runtime.stop()
        self._running = False

    @property
    def runtime(self) -> Optional[Any]:
        return self._runtime

    def _send_upstream(self, data_type: str, payload: Any) -> None:
        """Send data to central (if callback configured)."""
        if self._central_callback and data_type in self._split.upstream_data:
            self._central_callback(data_type, {"store_id": self._store.store_id, **payload})


class DeploymentTopology:
    """Full deployment topology for organization (OC-18)."""

    def __init__(
        self,
        organization: OrganizationConfig,
        *,
        edge_runtime_provider: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._organization = organization
        self._stores: Dict[str, StoreDeployment] = {}
        self._central = CentralQueryService()
        self._edge_runtime_provider = edge_runtime_provider

    def add_store(self, store: StoreConfig, split: EdgeCentralSplit) -> None:
        """Add store to topology."""
        self._stores[store.store_id] = StoreDeployment(
            store=store,
            split=split,
        )

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate entire topology."""
        errors = []
        for store_id, deployment in self._stores.items():
            valid, split_errors = deployment.split.validate()
            if not valid:
                errors.extend([f"{store_id}: {e}" for e in split_errors])
        return len(errors) == 0, errors

    def get_central_service(self) -> CentralQueryService:
        return self._central

    def get_store_deployment(self, store_id: str) -> Optional[StoreDeployment]:
        return self._stores.get(store_id)

    def create_edge_service(self, store_id: str) -> Optional[EdgeCaptureService]:
        """Factory for edge service at store."""
        deployment = self._stores.get(store_id)
        if not deployment:
            return None
        runtime = (
            self._edge_runtime_provider(store_id)
            if self._edge_runtime_provider is not None
            else None
        )
        return EdgeCaptureService(
            store=deployment.store,
            split=deployment.split,
            central_callback=self._central_ingest,
            runtime=runtime,
        )

    def _central_ingest(self, data_type: str, payload: Any) -> None:
        """Internal callback for edge -> central data flow."""
        store_id = payload.get("store_id")
        if not store_id:
            return

        if data_type == "health_snapshots":
            self._central.ingest_store_health(store_id, payload.get("health"))
        elif data_type in ("behavior_events", "scene_events"):
            events = payload.get("events", [])
            self._central.ingest_store_events(store_id, events)
        elif data_type == "review_records":
            self._central.ingest_review_record(payload.get("record", {}))
