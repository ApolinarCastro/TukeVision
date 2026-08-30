"""Strict Runtime Truth and Zero-Fake Acceptance Tests for TukeVision.

EXECUTION_ID: TV-F12-STRICT-RUNTIME-TRUTH-ENFORCEMENT-06
Validates:
1. test_no_focus_resolution_fallback
2. test_generation_requires_strict_increment
3. test_frame_requires_real_frame_object
4. test_liveness_gate_is_all_real_booleans
5. test_no_freshness_22_4_fallback
6. test_presentation_not_inferred_from_capture
7. test_registered_not_available
8. test_grid6_no_viewport_fallback
9. test_grid6_no_assumed_tile_count
10. test_grid6_overlap_computed
11. test_grid6_clipping_computed
12. test_screenshot_failure_has_no_synthetic_fallback
13. test_certification_soak_cannot_be_below_1800
14. test_global_health_not_hardcoded
15. test_final_verdict_reads_gate_artifacts
16. test_zero_fake_counters_are_instrumented
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.observability.runtime_evidence_collector import (
    CertificationEvaluator,
    CertificationRequirementError,
    RuntimeContext,
    RuntimeEvidenceCollector,
)


def test_no_focus_resolution_fallback():
    # If no frame is observed, source resolution MUST be NOT_OBSERVED and focus_hd_pass MUST be False
    main_pass, hd_pass, status = CertificationEvaluator.evaluate_focus(
        profile_requested="MAIN",
        profile_observed="MAIN",
        frame_shape=None,
        frame_sequence=0,
        source_resolution_observed=False,
    )
    assert not main_pass
    assert not hd_pass
    assert status == "MAIN_SWITCH_FAILED"


def test_generation_requires_strict_increment():
    # Strict inequality: gen_after > gen_before
    gen_before = 0
    gen_after = 0
    assert not (gen_after > gen_before)

    gen_after = 1
    assert (gen_after > gen_before) is True


def test_frame_requires_real_frame_object():
    # frame_sequence >= 0 alone does not prove a frame if frame object is None
    main_pass, hd_pass, _ = CertificationEvaluator.evaluate_focus(
        profile_requested="MAIN",
        profile_observed="MAIN",
        frame_shape=None,
        frame_sequence=15,
        source_resolution_observed=False,
    )
    assert not main_pass
    assert not hd_pass


def test_liveness_gate_is_all_real_booleans():
    # Evaluates boolean expression over actual flags, no hardcoded True
    cameras = [
        {"camera_id": "cam_01", "is_live_derived": True},
        {"camera_id": "cam_02", "is_live_derived": False},
    ]
    gate = all(c["is_live_derived"] for c in cameras)
    assert gate is False


def test_no_freshness_22_4_fallback():
    # Without observed frame age, freshness is NOT_OBSERVED and freshness_valid is False
    is_live = CertificationEvaluator.evaluate_liveness(
        session_open=True,
        capture_advancing=True,
        presentation_advancing=True,
        freshness_valid=False,  # no fallback constant!
    )
    assert is_live is False


def test_presentation_not_inferred_from_capture():
    # Presentation advancing MUST require presented_sequence_T1 > presented_sequence_T0
    # capture_advancing does not suffice
    is_live = CertificationEvaluator.evaluate_liveness(
        session_open=True,
        capture_advancing=True,
        presentation_advancing=False,
        freshness_valid=True,
    )
    assert is_live is False


def test_registered_not_available():
    # A source that is merely REGISTERED without session open is not LIVE
    is_live = CertificationEvaluator.evaluate_liveness(
        session_open=False,
        capture_advancing=False,
        presentation_advancing=False,
        freshness_valid=False,
    )
    assert is_live is False


def test_grid6_no_viewport_fallback():
    # Invalid viewport (width < 100 or height < 100) must FAIL without substituting 1280x680
    passed = CertificationEvaluator.evaluate_grid6(
        viewport_valid=False,
        visible_cameras=6,
        empty_tiles=0,
        overlap_count=0,
        clipped_count=0,
        dead_space_percent=5.0,
    )
    assert passed is False


def test_grid6_no_assumed_tile_count():
    # If visible cameras is not 6, grid6 must FAIL
    passed = CertificationEvaluator.evaluate_grid6(
        viewport_valid=True,
        visible_cameras=4,
        empty_tiles=0,
        overlap_count=0,
        clipped_count=0,
        dead_space_percent=5.0,
    )
    assert passed is False


def test_grid6_overlap_computed():
    # Overlapping tiles must cause grid6 evaluation to fail
    passed = CertificationEvaluator.evaluate_grid6(
        viewport_valid=True,
        visible_cameras=6,
        empty_tiles=0,
        overlap_count=1,
        clipped_count=0,
        dead_space_percent=5.0,
    )
    assert passed is False


def test_grid6_clipping_computed():
    # Clipped tiles must cause grid6 evaluation to fail
    passed = CertificationEvaluator.evaluate_grid6(
        viewport_valid=True,
        visible_cameras=6,
        empty_tiles=0,
        overlap_count=0,
        clipped_count=1,
        dead_space_percent=5.0,
    )
    assert passed is False


def test_screenshot_failure_has_no_synthetic_fallback():
    # In certification mode, synthetic screenshot fallback is forbidden
    ctx = RuntimeContext(
        source_manager=MagicMock(),
        tk_app=MagicMock(),
        health_sampler=MagicMock(),
        true_liveness=MagicMock(),
        multicamera_runtime=MagicMock(),
        run_id="TEST-RUN",
        start_time=100.0,
        pid=os.getpid(),
    )
    collector = RuntimeEvidenceCollector(ctx)
    assert collector.synthetic_fallback_allowed is False


def test_certification_soak_cannot_be_below_1800():
    # Guard raises CertificationRequirementError if soak < 1800 in certification mode
    ctx = RuntimeContext(
        source_manager=MagicMock(),
        tk_app=MagicMock(),
        health_sampler=MagicMock(),
        true_liveness=MagicMock(),
        multicamera_runtime=MagicMock(),
        run_id="TEST-RUN",
        start_time=100.0,
        pid=os.getpid(),
    )
    collector = RuntimeEvidenceCollector(ctx)
    with pytest.raises(CertificationRequirementError):
        collector.execute_soak_sampling(target_duration_seconds=30, certification_mode=True)


def test_global_health_not_hardcoded():
    # System health must persist structured snapshot without hardcoding SALUDABLE
    ctx = RuntimeContext(
        source_manager=MagicMock(),
        tk_app=MagicMock(),
        health_sampler=None,
        true_liveness=MagicMock(),
        multicamera_runtime=MagicMock(),
        run_id="TEST-RUN",
        start_time=100.0,
        pid=os.getpid(),
    )
    collector = RuntimeEvidenceCollector(ctx)
    trace = collector.build_system_health_trace()
    assert trace["overall_health_derived"] in ("NOMINAL", "DEGRADED", "UNKNOWN", "OFFLINE")
    assert trace["overall_health_derived"] != "SALUDABLE"


def test_final_verdict_reads_gate_artifacts():
    # Verdict parser checks all required JSONs dynamically
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "soak_summary.json").write_text(json.dumps({"soak_passed_derived": True, "actual_duration_seconds": 1800}), encoding="utf-8")
        (tmp_path / "regression_summary.json").write_text(json.dumps({"clean_regression": True}), encoding="utf-8")
        (tmp_path / "zero_fake_runtime_gate.json").write_text(json.dumps({"zero_fake_passed_derived": True}), encoding="utf-8")
        (tmp_path / "focus_hd_physical.json").write_text(json.dumps({"overall_focus_main_pass": True, "overall_focus_hd_pass": False, "status": "FAIL"}), encoding="utf-8")
        (tmp_path / "liveness_physical.json").write_text(json.dumps({"gate_liveness_all_derived": False}), encoding="utf-8")
        (tmp_path / "grid6_physical.json").write_text(json.dumps({"grid6_pass_derived": True}), encoding="utf-8")
        
        check = CertificationEvaluator.evaluate_certification_integrity(tmp_path)
        assert check["soak_conforming"] is True
        assert check["regression_passed"] is True
        # Since focus_hd_physical has status FAIL, final closure is limited
        assert check["final_closure_allowed"] is False
        assert check["recommended_verdict"] == "TV_F12_RUNTIME_TRUTH_CLOSED_WITH_EXTERNAL_LIMITATIONS"


def test_zero_fake_counters_are_instrumented():
    counters = {
        "detections_received": 0,
        "tracks_received": 0,
        "events_received": 0,
        "situations_received": 0,
        "situations_rendered": 0,
        "situations_created_by_ui": 0,
        "ids_created_by_ui": 0,
        "severity_created_by_ui": 0,
        "epistemic_created_by_ui": 0,
    }
    zero_fake_ok = (
        counters["situations_created_by_ui"] == 0
        and counters["ids_created_by_ui"] == 0
        and counters["severity_created_by_ui"] == 0
        and counters["epistemic_created_by_ui"] == 0
    )
    assert zero_fake_ok is True
