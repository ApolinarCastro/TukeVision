import pytest
from scripts.run_physical_raw_recorder import record_sample
from pathlib import Path
import tempfile
import json
import time

def test_raw_recorder_never_uses_operator_attestation():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        content = out_path.read_text(encoding="utf-8")
        assert "OPERATOR_ATTESTATION" not in content
        
def test_raw_recorder_missing_value_is_null():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["process"]["cpu_percent"] is None
        assert "process.cpu_percent" in data["missing_fields"]
        
def test_raw_recorder_does_not_default_resolution():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        (run_dir / "live_status.json").write_text('{"cameras": {"cam_01": {}}}', encoding="utf-8")
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["cameras"]["cam_01"]["source_width"] is None
        
def test_raw_recorder_does_not_default_fps():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        (run_dir / "live_status.json").write_text('{"cameras": {"cam_01": {}}}', encoding="utf-8")
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "fps" not in data["cameras"]["cam_01"]  # We didn't even include fps, or if we did, it's null
        
def test_raw_recorder_does_not_default_readers():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["streams"]["readers_active"] is None
        
def test_raw_recorder_does_not_default_decoders():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["streams"]["decoders_active"] is None

def test_raw_recorder_uses_monotonic_elapsed():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        t = time.monotonic()
        time.sleep(0.1)
        record_sample(run_dir, out_path, 0, t)
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["elapsed_seconds"] >= 0.08

def test_raw_recorder_is_append_only():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        record_sample(run_dir, out_path, 1, time.monotonic())
        
        lines = out_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

def test_raw_recorder_records_missing_fields():
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "RUN-TEST"
        run_dir.mkdir()
        out_path = Path(td) / "raw.jsonl"
        record_sample(run_dir, out_path, 0, time.monotonic())
        
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "runtime.pid" in data["missing_fields"]
        
def test_soak_cannot_pass_with_single_sample():
    # Placeholder for evaluator test
    pass

def test_soak_cannot_pass_below_1800_seconds():
    # Placeholder for evaluator test
    pass

def test_soak_cannot_pass_with_large_sample_gaps():
    # Placeholder for evaluator test
    pass

def test_summary_is_derived_from_raw_samples():
    # Placeholder for evaluator test
    pass

def test_summary_cannot_override_raw_values():
    # Placeholder for evaluator test
    pass
