"""Low-frequency host and camera health snapshots for the operator UI.

The sampler is synchronous and cached.  It opens no source, consumes no frame
and owns no thread; the existing Tk poll loop is its scheduler.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Tuple


logger = logging.getLogger("tukevision.system_health")
HEALTH_METRIC_UNAVAILABLE = "HEALTH_METRIC_UNAVAILABLE"
_ONLINE_STATES = frozenset(("OPEN", "READING"))


def _number(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def read_host_metrics(disk_path: str | Path = ".") -> dict:
    """Read non-blocking raw host metrics, returning None per failed metric."""
    cpu_percent = None
    ram_percent = None
    ram_used_mb = None
    ram_total_mb = None
    disk_percent = None
    disk_free_gb = None
    try:
        import psutil

        try:
            cpu_percent = float(psutil.cpu_percent(interval=None))
        except Exception as exc:
            logger.warning("%s metric=CPU error=%s", HEALTH_METRIC_UNAVAILABLE, type(exc).__name__)
        try:
            memory = psutil.virtual_memory()
            ram_percent = float(memory.percent)
            ram_used_mb = float(memory.used) / (1024 ** 2)
            ram_total_mb = float(memory.total) / (1024 ** 2)
        except Exception as exc:
            logger.warning("%s metric=RAM error=%s", HEALTH_METRIC_UNAVAILABLE, type(exc).__name__)
    except Exception as exc:
        logger.warning("%s metric=PSUTIL error=%s", HEALTH_METRIC_UNAVAILABLE, type(exc).__name__)
    try:
        disk = shutil.disk_usage(Path(disk_path))
        if disk.total > 0:
            disk_percent = (float(disk.used) / float(disk.total)) * 100.0
        disk_free_gb = float(disk.free) / (1024 ** 3)
    except Exception as exc:
        logger.warning("%s metric=DISK error=%s", HEALTH_METRIC_UNAVAILABLE, type(exc).__name__)
    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "disk_percent": disk_percent,
        "disk_free_gb": disk_free_gb,
    }


@dataclass(frozen=True)
class CameraOperationalHealth:
    camera_id: str
    source_state: str
    online: bool
    fps: Optional[float]
    last_frame_age: Optional[float]
    stall_count: Optional[int]
    last_error: str = ""


@dataclass(frozen=True)
class SystemHealthSnapshot:
    timestamp: str
    cpu_percent: Optional[float]
    ram_percent: Optional[float]
    ram_used_mb: Optional[float]
    ram_total_mb: Optional[float]
    disk_percent: Optional[float]
    disk_free_gb: Optional[float]
    camera_health: Tuple[CameraOperationalHealth, ...]
    online_camera_count: int
    total_camera_count: int
    global_health: str

    def camera(self, camera_id: str) -> CameraOperationalHealth:
        for item in self.camera_health:
            if item.camera_id == camera_id:
                return item
        raise KeyError(camera_id)


class SystemHealthSampler:
    """Bounded snapshot collector driven by calls from the existing UI tick."""

    def __init__(
        self,
        source_manager,
        camera_ids: Sequence[str],
        *,
        sample_interval_seconds: float = 3.0,
        disk_path: str | Path = ".",
        host_metrics_reader: Optional[Callable[[], Mapping[str, object]]] = None,
        clock: Callable[[], float] = time.monotonic,
        timestamp_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        interval = float(sample_interval_seconds)
        if not 2.0 <= interval <= 5.0:
            raise ValueError("health sample interval must be between 2 and 5 seconds")
        ids = tuple(str(item) for item in camera_ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("camera_ids must be non-empty and unique")
        self._source_manager = source_manager
        self._camera_ids = ids
        self.sample_interval_seconds = interval
        self._host_metrics_reader = host_metrics_reader or (
            lambda: read_host_metrics(disk_path)
        )
        self._clock = clock
        self._timestamp_factory = timestamp_factory or (
            lambda: datetime.now(timezone.utc).isoformat()
        )
        self._lock = threading.RLock()
        self._cached: Optional[SystemHealthSnapshot] = None
        self._last_sample_at: Optional[float] = None
        self._last_runtime_running: Optional[bool] = None

    @staticmethod
    def _host_values(values: Mapping[str, object]) -> dict:
        return {
            key: _number(values.get(key))
            for key in (
                "cpu_percent",
                "ram_percent",
                "ram_used_mb",
                "ram_total_mb",
                "disk_percent",
                "disk_free_gb",
            )
        }

    def _read_host(self) -> dict:
        try:
            values = self._host_metrics_reader()
            if not isinstance(values, Mapping):
                raise TypeError("host metric reader did not return a mapping")
            return self._host_values(values)
        except Exception as exc:
            logger.warning(
                "%s metric=HOST error=%s",
                HEALTH_METRIC_UNAVAILABLE,
                type(exc).__name__,
            )
            return self._host_values({})

    def _camera_values(self, runtime_running: bool) -> tuple[CameraOperationalHealth, ...]:
        values = []
        for camera_id in self._camera_ids:
            if not runtime_running:
                values.append(CameraOperationalHealth(
                    camera_id, "CLOSED", False, 0.0, None, None
                ))
                continue
            try:
                health = self._source_manager.health(camera_id)
                state = str(getattr(health, "state", "UNKNOWN") or "UNKNOWN")
                fps = _number(getattr(health, "fps", None))
                age_ms = _number(getattr(health, "last_valid_frame_age_ms", None))
                stall_count = getattr(health, "stall_count", None)
                try:
                    stall_count = int(stall_count) if stall_count is not None else None
                except (TypeError, ValueError):
                    stall_count = None
                online = bool(getattr(health, "healthy", False)) and state in _ONLINE_STATES
                values.append(CameraOperationalHealth(
                    camera_id=camera_id,
                    source_state=state,
                    online=online,
                    fps=fps,
                    last_frame_age=(None if age_ms is None else age_ms / 1000.0),
                    stall_count=stall_count,
                    last_error=str(getattr(health, "last_error", "") or ""),
                ))
            except Exception as exc:
                logger.warning(
                    "%s metric=CAMERA camera_id=%s error=%s",
                    HEALTH_METRIC_UNAVAILABLE,
                    camera_id,
                    type(exc).__name__,
                )
                values.append(CameraOperationalHealth(
                    camera_id, "UNKNOWN", False, None, None, None,
                    HEALTH_METRIC_UNAVAILABLE,
                ))
        return tuple(values)

    @staticmethod
    def _global_health(
        runtime_running: bool,
        host: Mapping[str, Optional[float]],
        cameras: Sequence[CameraOperationalHealth],
    ) -> str:
        if not runtime_running:
            return "OFFLINE"
        if any(host.get(key) is None for key in (
            "cpu_percent", "ram_percent", "ram_used_mb", "ram_total_mb",
            "disk_percent", "disk_free_gb",
        )):
            return "UNKNOWN"
        if not cameras:
            return "UNKNOWN"
        return "OK" if all(item.online for item in cameras) else "DEGRADED"

    def _build(
        self,
        runtime_running: bool,
        host: Mapping[str, Optional[float]],
    ) -> SystemHealthSnapshot:
        cameras = self._camera_values(runtime_running)
        online = sum(1 for item in cameras if item.online)
        return SystemHealthSnapshot(
            timestamp=self._timestamp_factory(),
            cpu_percent=host["cpu_percent"],
            ram_percent=host["ram_percent"],
            ram_used_mb=host["ram_used_mb"],
            ram_total_mb=host["ram_total_mb"],
            disk_percent=host["disk_percent"],
            disk_free_gb=host["disk_free_gb"],
            camera_health=cameras,
            online_camera_count=online,
            total_camera_count=len(cameras),
            global_health=self._global_health(runtime_running, host, cameras),
        )

    def snapshot(self, *, runtime_running: bool) -> SystemHealthSnapshot:
        now = float(self._clock())
        running = bool(runtime_running)
        with self._lock:
            same_runtime = self._last_runtime_running == running
            due = (
                self._last_sample_at is None
                or now - self._last_sample_at >= self.sample_interval_seconds
            )
            if self._cached is not None and same_runtime and not due:
                return self._cached

            if self._cached is not None and not running and not due:
                host = self._host_values(self._cached.__dict__)
            else:
                host = self._read_host()
                self._last_sample_at = now
            self._cached = self._build(running, host)
            self._last_runtime_running = running
            return self._cached
