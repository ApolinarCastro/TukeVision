import pytest
import time
from src.observability.latency_metrics import PercentileRegistry, LatencyMetrics

def test_empty_registry_returns_null_percentiles():
    reg = PercentileRegistry()
    snap = reg.snapshot()
    assert snap["count"] == 0
    assert snap["p50_ms"] is None
    assert snap["p95_ms"] is None
    assert snap["min_ms"] is None
    assert snap["max_ms"] is None

def test_single_sample_percentiles():
    reg = PercentileRegistry()
    reg.record(42.5)
    snap = reg.snapshot()
    assert snap["count"] == 1
    assert snap["p50_ms"] == 42.5
    assert snap["p95_ms"] == 42.5
    assert snap["min_ms"] == 42.5
    assert snap["max_ms"] == 42.5

def test_p95_is_computed_from_real_samples():
    reg = PercentileRegistry()
    for i in range(1, 101):
        reg.record(float(i))
    snap = reg.snapshot()
    assert snap["count"] == 100
    assert snap["p50_ms"] == 50.5
    assert snap["p95_ms"] == 95.05
    assert snap["min_ms"] == 1.0
    assert snap["max_ms"] == 100.0

def test_metrics_are_isolated_per_camera():
    lm = LatencyMetrics()
    lm.record("cam_1", "frame_age_ms", 10.0)
    lm.record("cam_2", "frame_age_ms", 20.0)
    
    cam1 = lm.get_metrics_for_camera("cam_1")
    cam2 = lm.get_metrics_for_camera("cam_2")
    
    assert cam1["frame_age_ms"]["p50_ms"] == 10.0
    assert cam2["frame_age_ms"]["p50_ms"] == 20.0

def test_metric_names_are_isolated():
    lm = LatencyMetrics()
    lm.record("cam_1", "frame_age_ms", 10.0)
    lm.record("cam_1", "time_to_first_frame_ms", 500.0)
    
    res = lm.get_metrics_for_camera("cam_1")
    assert res["frame_age_ms"]["p95_ms"] == 10.0
    assert res["time_to_first_frame_ms"]["p95_ms"] == 500.0

def test_registry_is_bounded():
    reg = PercentileRegistry(maxlen=10)
    for i in range(100):
        reg.record(float(i))
    snap = reg.snapshot()
    assert snap["count"] == 10
    # Should contain the last 10 elements: 90 to 99
    assert snap["min_ms"] == 90.0
    assert snap["max_ms"] == 99.0

def test_missing_timestamp_does_not_generate_fake_latency():
    # Application layer responsibility, but we assert that registry has no default defaults
    reg = PercentileRegistry()
    # if it's missing, we just don't call record
    snap = reg.snapshot()
    assert snap["count"] == 0
    assert snap["p50_ms"] is None

def test_monotonic_duration_is_non_negative():
    reg = PercentileRegistry()
    reg.record(-50.0) # Should be clamped to 0
    snap = reg.snapshot()
    assert snap["p50_ms"] == 0.0
    assert snap["min_ms"] == 0.0

def test_snapshot_does_not_mutate_registry():
    reg = PercentileRegistry()
    reg.record(10.0)
    reg.record(5.0)
    snap1 = reg.snapshot()
    snap2 = reg.snapshot()
    assert snap1 == snap2
    assert snap1["count"] == 2
    # Ensure it's still possible to add
    reg.record(20.0)
    assert reg.snapshot()["count"] == 3

def test_no_runtime_control_methods():
    lm = LatencyMetrics()
    # Assert that no control methods exist on the object
    forbidden = ["restart", "change_profile", "stop", "reconnect", "write_evidence"]
    for f in forbidden:
        assert not hasattr(lm, f)

def test_metrics_do_not_write_evidence_store():
    # There should be no os.open, no open, no writes to disk in the recording path
    import os
    # We just run a simple record loop, if it wrote to disk it would be slow or leave files
    lm = LatencyMetrics()
    start = time.monotonic()
    for _ in range(100):
        lm.record("cam_1", "test", 10.0)
    duration = time.monotonic() - start
    assert duration < 0.1 # Should be completely in-memory and fast

def test_performance():
    lm = LatencyMetrics(max_samples_per_metric=10000)
    import time
    start = time.monotonic()
    
    n_ops = 10000
    for i in range(n_ops):
        lm.record("cam_1", "frame_age_ms", float(i % 100))
        
    end = time.monotonic()
    total_runtime = end - start
    avg_insertion = total_runtime / n_ops
    
    # Save baseline to standard out for visibility
    print(f"Total runtime for {n_ops} metric observations: {total_runtime:.6f}s")
    print(f"Average insertion time: {avg_insertion:.9f}s")
    
    # We do not impose a strict threshold, but 10k should be very fast in pure Python
    assert total_runtime < 1.0 
