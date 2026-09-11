"""Periodic resource telemetry for long physical runs (MACRO-OC-02, BLOCK D).

Records UPTIME / CPU / PROCESS_RSS / SYSTEM_RAM / THREAD_COUNT /
QUEUE_DEPTHS / ACTIVE_SOURCES / ONLINE_COUNT / RECONNECTING_COUNT at
configurable intervals, aligned to the 0m / 5m / 10m / 20m / 30m markers
the operator uses to compare.  Output is one row per sample (never a log
per frame).  Values come from psutil (host) and the existing SourceManager
health API (no capture changes).
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

import psutil

MARKERS_MINUTES = (0, 5, 10, 15, 20, 25, 30)
MARKERS_SECONDS = tuple(m * 60 for m in MARKERS_MINUTES)


def _process_cpu(proc: psutil.Process) -> Optional[float]:
    try:
        return float(proc.cpu_percent(interval=None) or 0.0)
    except Exception:
        return None


def _process_rss(proc: psutil.Process) -> Optional[int]:
    try:
        return int(proc.memory_info().rss)
    except Exception:
        return None


def _system_ram() -> dict:
    try:
        vm = psutil.virtual_memory()
        return {
            "ram_percent": float(vm.percent),
            "ram_used_mb": round(float(vm.used) / (1024 ** 2), 1),
            "ram_total_mb": round(float(vm.total) / (1024 ** 2), 1),
        }
    except Exception:
        return {}


class ResourceTelemetry:
    """Background sampler writing bounded, JSON-serialisable rows."""

    def __init__(
        self,
        camera_ids: Sequence[str],
        source_manager: object,
        health_snapshot=None,
        *,
        interval_s: float = 30.0,
        markers_seconds: Sequence[int] = MARKERS_SECONDS,
        clock: Optional[Callable[[], float]] = None,
        psutil_proc: Optional[psutil.Process] = None,
    ) -> None:
        self._camera_ids = tuple(str(item) for item in camera_ids)
        self._manager = source_manager
        self._health_snapshot = health_snapshot
        self._interval_s = max(1.0, float(interval_s))
        self._markers = tuple(int(m) for m in markers_seconds)
        self._clock = clock or time.monotonic
        self._proc = psutil_proc or psutil.Process(os.getpid())
        self._samples: list = []
        self._marker_hits: dict = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started: Optional[float] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ state
    def _counts(self) -> dict:
        if self._health_snapshot is not None:
            try:
                health = self._health_snapshot()
                counts = {"ONLINE": 0, "RECONNECTING": 0, "DEGRADED": 0, "OFFLINE": 0}
                for item in health.camera_health:
                    key = getattr(item, "health_state", "OFFLINE") or "OFFLINE"
                    counts[key] = counts.get(key, 0) + 1
                return counts
            except Exception:
                pass
        online = 0
        reconnecting = 0
        offline = 0
        for camera_id in self._camera_ids:
            try:
                item = self._manager.health(camera_id)
            except Exception:
                offline += 1
                continue
            state = str(getattr(item, "state", "") or "")
            if state in ("OPEN", "READING"):
                online += 1
            elif state in ("CONNECTING", "RECONNECTING", "REGISTERED"):
                reconnecting += 1
            else:
                offline += 1
        return {"ONLINE": online, "RECONNECTING": reconnecting,
                "DEGRADED": 0, "OFFLINE": offline}

    def _sample(self) -> dict:
        uptime = 0.0
        if self._started is not None:
            uptime = round(max(0.0, self._clock() - self._started), 1)
        sources = []
        try:
            sources = list(self._manager.list_sources() or [])
        except Exception:
            pass
        queue_depths = {}
        for item in sources:
            camera_id = item.get("camera_id")
            try:
                queue_depths[camera_id] = int(self._manager.health(camera_id).queue_depth)
            except Exception:
                queue_depths[camera_id] = 0
        counts = self._counts()
        row = {
            "uptime_s": uptime,
            "cpu_percent": _process_cpu(self._proc),
            "process_rss_mb": (
                round(_process_rss(self._proc) / (1024 ** 2), 1)
                if _process_rss(self._proc) is not None else None
            ),
            "thread_count": threading.active_count(),
            "active_sources": sum(1 for item in sources if item.get("running")),
            "total_sources": len(sources),
            "queue_depths": queue_depths,
            "online": counts["ONLINE"],
            "reconnecting": counts["RECONNECTING"],
            "offline": counts["OFFLINE"],
        }
        row.update(_system_ram())
        row["wall_clock"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return row

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._started = self._clock()
        baseline = self._sample()  # t0 baseline (0m)
        with self._lock:
            self._samples.append(baseline)
            if 0 in self._markers:
                self._marker_hits[0] = baseline
                baseline["marker_min"] = 0.0
        self._thread = threading.Thread(
            target=self._loop, name="tukevision-resource-telemetry", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(self._interval_s)
            if self._stop.is_set():
                return
            try:
                self._record()
            except Exception:
                continue

    def _record(self) -> None:
        with self._lock:
            uptime = 0.0 if self._started is None else self._clock() - self._started
            row = self._sample()
            self._samples.append(row)
            for marker in self._markers:
                if marker not in self._marker_hits and uptime >= marker:
                    self._marker_hits[marker] = row
                    row["marker_min"] = marker / 60.0

    def snapshot(self) -> list:
        with self._lock:
            return [dict(item) for item in self._samples]

    def marker_rows(self) -> dict:
        with self._lock:
            return {str(k): dict(v) for k, v in self._marker_hits.items()}

    def rss_deltas(self) -> dict:
        rows = self.snapshot()
        if not rows:
            return {}
        baseline = rows[0].get("process_rss_mb")
        result = {}
        for marker in self._markers:
            row = self._marker_hits.get(marker) or self._closest_row(rows, marker)
            rss = row.get("process_rss_mb") if row else None
            if baseline is not None and rss is not None:
                result[f"rss_delta_{marker // 60}m_mb"] = round(rss - baseline, 1)
        return result

    def _closest_row(self, rows: list, marker_s: int) -> Optional[dict]:
        best = None
        for row in rows:
            if best is None or abs(row["uptime_s"] - marker_s) < abs(
                best["uptime_s"] - marker_s
            ):
                best = row
        return best

    def export(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "interval_s": self._interval_s,
            "markers_minutes": list(self._markers),
            "rss_deltas_mb": self.rss_deltas(),
            "samples": self.snapshot(),
            "marker_rows": self.marker_rows(),
        }
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(target)
        return target

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5)


__all__ = ["ResourceTelemetry", "MARKERS_MINUTES", "MARKERS_SECONDS"]