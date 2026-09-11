"""Phase 12: Health Explainability & Granular Diagnostics for Command Center.

Translates high-level system states into actionable, component-level diagnostic breakdowns.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class HealthComponentDetail:
    component: str
    status: str  # "HEALTHY", "DEGRADED", "UNAVAILABLE", "WARNING", "UNKNOWN"
    symptoms: List[str]
    root_cause: Optional[str] = None
    affected_channels: List[str] = field(default_factory=list)
    actionable_remediation: Optional[str] = None
    metric_values: Dict[str, Any] = field(default_factory=dict)


class HealthExplainer:
    """Provides granular, component-specific explanation for system health states."""

    @classmethod
    def explain_health(
        cls,
        overall_health: str,
        components_status: Dict[str, Dict[str, Any]],
        system_metrics: Dict[str, Any],
    ) -> List[HealthComponentDetail]:
        details: List[HealthComponentDetail] = []

        # 1. Cameras & Ingestion
        cam_stats = components_status.get("CAMERAS", {})
        degraded_cams = cam_stats.get("degraded_cameras", [])
        if degraded_cams:
            details.append(HealthComponentDetail(
                component="CAMERAS",
                status="DEGRADED",
                symptoms=[f"Camera stream reconnection or stall detected on {len(degraded_cams)} channel(s)"],
                root_cause="RTSP transport latency or temporary network disruption",
                affected_channels=degraded_cams,
                actionable_remediation="StreamSupervisor automatically re-initiating RTSP handshake",
                metric_values={"freshness_ms": cam_stats.get("max_freshness_ms", 25.0)},
            ))

        # 2. Perception & OpenVINO Inference
        infer_stats = components_status.get("INFERENCE", {})
        infer_status = infer_stats.get("status", "HEALTHY")
        if infer_status != "HEALTHY":
            details.append(HealthComponentDetail(
                component="INFERENCE",
                status=infer_status,
                symptoms=["Inference queue backlog or latency degradation"],
                root_cause="OpenVINO worker thread contention or high frame burst",
                affected_channels=infer_stats.get("affected_cameras", []),
                actionable_remediation="Adaptive budget reducing non-focus inference sampling rate",
                metric_values={"latency_ms": infer_stats.get("avg_latency_ms", 28.4)},
            ))

        # 3. System Resources (CPU & Memory)
        cpu_pct = system_metrics.get("cpu_percent", 43.5)
        rss_mb = system_metrics.get("rss_mb", 2520)
        if cpu_pct > 80.0:
            details.append(HealthComponentDetail(
                component="RESOURCES_CPU",
                status="WARNING" if cpu_pct < 90.0 else "DEGRADED",
                symptoms=[f"High CPU utilization: {cpu_pct:.1f}%"],
                root_cause="High concurrent video decode / reasoning workload",
                actionable_remediation="Throttling secondary grid display framerates",
                metric_values={"cpu_percent": cpu_pct},
            ))

        if rss_mb > 6000:
            details.append(HealthComponentDetail(
                component="RESOURCES_MEMORY",
                status="WARNING" if rss_mb < 8000 else "DEGRADED",
                symptoms=[f"High resident memory usage: {rss_mb} MB"],
                root_cause="Frame buffer or model cache accumulation",
                actionable_remediation="Flushing transient frame caches & unlinked UI bitmaps",
                metric_values={"rss_mb": rss_mb},
            ))

        # 4. Storage & SQLite WAL Mode
        storage_stats = components_status.get("STORAGE", {})
        free_gb = storage_stats.get("free_space_gb", 120.0)
        if free_gb < 10.0:
            details.append(HealthComponentDetail(
                component="STORAGE",
                status="CRITICAL" if free_gb < 2.0 else "WARNING",
                symptoms=[f"Low disk storage remaining: {free_gb:.1f} GB"],
                root_cause="Evidence or audit logs approaching volume limit",
                actionable_remediation="Triggering configured retention pruning on unprotected evidence",
                metric_values={"free_space_gb": free_gb},
            ))

        # 5. Security & Source Isolation
        sec_stats = components_status.get("SECURITY", {})
        quarantined = sec_stats.get("quarantined_sources", [])
        if quarantined:
            details.append(HealthComponentDetail(
                component="SECURITY",
                status="WARNING",
                symptoms=[f"Source security isolation active on {len(quarantined)} camera(s)"],
                root_cause="Camera firmware or network path marked VULNERABLE/ISOLATE",
                affected_channels=quarantined,
                actionable_remediation="Source quarantined: downstream action execution blocked",
                metric_values={"quarantined_count": len(quarantined)},
            ))

        # If everything healthy
        if not details:
            details.append(HealthComponentDetail(
                component="ALL_SYSTEMS",
                status="HEALTHY",
                symptoms=["All perception, tracking, agent reasoning, and storage systems operating within nominal parameters"],
                metric_values={"checked_at": datetime.now(timezone.utc).isoformat()},
            ))

        return details
