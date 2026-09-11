import time
import math
import collections
from typing import Dict, Any, Optional

class PercentileRegistry:
    def __init__(self, maxlen: int = 1000):
        self._samples = collections.deque(maxlen=maxlen)

    def record(self, value_ms: float):
        if value_ms < 0:
            value_ms = 0.0
        self._samples.append(value_ms)

    def _percentile(self, sorted_data, percent: float) -> Optional[float]:
        n = len(sorted_data)
        if n == 0:
            return None
        if n == 1:
            return float(sorted_data[0])
        k = (n - 1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_data[int(k)])
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return float(d0 + d1)

    def snapshot(self) -> Dict[str, Any]:
        data = list(self._samples)
        if not data:
            return {
                "count": 0,
                "min_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "max_ms": None
            }
        
        data.sort()
        return {
            "count": len(data),
            "min_ms": float(data[0]),
            "p50_ms": self._percentile(data, 0.50),
            "p95_ms": self._percentile(data, 0.95),
            "max_ms": float(data[-1])
        }

class LatencyMetrics:
    def __init__(self, max_samples_per_metric: int = 1000):
        # schema: dict[camera_id, dict[metric_name, PercentileRegistry]]
        self._metrics: Dict[str, Dict[str, PercentileRegistry]] = {}
        self._maxlen = max_samples_per_metric

    def record(self, camera_id: str, metric_name: str, value_ms: float):
        if camera_id not in self._metrics:
            self._metrics[camera_id] = {}
        if metric_name not in self._metrics[camera_id]:
            self._metrics[camera_id][metric_name] = PercentileRegistry(maxlen=self._maxlen)
        self._metrics[camera_id][metric_name].record(value_ms)

    def get_metrics_for_camera(self, camera_id: str) -> Dict[str, Any]:
        result = {}
        if camera_id in self._metrics:
            for metric_name, registry in self._metrics[camera_id].items():
                result[metric_name] = registry.snapshot()
        return result

    def get_all_metrics(self) -> Dict[str, Any]:
        result = {}
        for cam_id, metrics in self._metrics.items():
            result[cam_id] = self.get_metrics_for_camera(cam_id)
        return result

# Global instance for observational integration
_global_latency_metrics = LatencyMetrics()

def record_latency(camera_id: str, metric_name: str, value_ms: float):
    _global_latency_metrics.record(camera_id, metric_name, value_ms)

def get_latency_metrics(camera_id: Optional[str] = None) -> Dict[str, Any]:
    if camera_id:
        return _global_latency_metrics.get_metrics_for_camera(camera_id)
    return _global_latency_metrics.get_all_metrics()
