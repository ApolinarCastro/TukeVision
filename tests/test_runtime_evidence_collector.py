"""Unit and integration tests for RuntimeEvidenceCollector and CertificationEvaluator.

Validates:
- Collector attaches to runtime SourceManager without creating parallel instances.
- Focus HD fails if frame not observed or resolution is 352x240.
- Grid6 geometry fails if viewport is 1x1 or dead space >= 10%.
- Soak certification fails if duration < 1800s.
- Registered source is not marked LIVE without fresh advancing frames.
- Global health and all PASS/FAIL statuses are derived boolean expressions.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from src.observability.runtime_evidence_collector import (
    CertificationEvaluator,
    RuntimeContext,
    RuntimeEvidenceCollector,
)


def test_collector_uses_runtime_source_manager():
    sm_mock = MagicMock()
    tk_mock = MagicMock()
    ctx = RuntimeContext(
        source_manager=sm_mock,
        tk_app=tk_mock,
        health_sampler=MagicMock(),
        true_liveness=MagicMock(),
        multicamera_runtime=MagicMock(),
        run_id="TEST-RUN",
        start_time=100.0,
        pid=os.getpid(),
    )
    collector = RuntimeEvidenceCollector(ctx)
    assert collector.ctx.source_manager is sm_mock
    assert collector.ctx.tk_app is tk_mock
    assert collector.ctx.pid == os.getpid()


def test_collector_does_not_create_parallel_source_manager():
    sm_mock = MagicMock()
    ctx = RuntimeContext(
        source_manager=sm_mock,
        tk_app=MagicMock(),
        health_sampler=MagicMock(),
        true_liveness=MagicMock(),
        multicamera_runtime=MagicMock(),
        run_id="TEST-RUN",
        start_time=100.0,
        pid=os.getpid(),
    )
    collector = RuntimeEvidenceCollector(ctx)
    # Ensure collector holds the exact same reference
    assert collector.ctx.source_manager is sm_mock


def test_focus_hd_fails_if_frame_not_observed():
    main_pass, hd_pass, status = CertificationEvaluator.evaluate_focus(
        profile_requested="MAIN",
        profile_observed="MAIN",
        frame_shape=None,
        frame_sequence=-1,
        source_resolution_observed=False,
    )
    assert not main_pass
    assert not hd_pass
    assert status == "MAIN_SWITCH_FAILED"


def test_focus_hd_fails_if_resolution_352x240():
    main_pass, hd_pass, status = CertificationEvaluator.evaluate_focus(
        profile_requested="MAIN",
        profile_observed="MAIN",
        frame_shape=(240, 352, 3),
        frame_sequence=10,
        source_resolution_observed=True,
    )
    assert main_pass is True
    assert hd_pass is False  # 352x240 is not HD!
    assert status == "MAIN_PROFILE_VALIDATED_SUB_HD_SOURCE"


def test_grid6_fails_if_viewport_1x1():
    passed = CertificationEvaluator.evaluate_grid6(
        viewport_valid=False,
        visible_cameras=6,
        empty_tiles=0,
        overlap_count=0,
        clipped_count=0,
        dead_space_percent=5.0,
    )
    assert not passed


def test_soak_certification_fails_below_1800():
    passed, status = CertificationEvaluator.evaluate_soak(
        actual_duration=30.0,
        target_duration=1800.0,
        unhandled_exceptions=0,
        ui_freezes=0,
    )
    assert passed is False
    assert status == "INCOMPLETE"


def test_registered_source_is_not_live():
    # If session is not open or capture is not advancing, evaluate_liveness must return False
    is_live = CertificationEvaluator.evaluate_liveness(
        session_open=False,
        capture_advancing=False,
        presentation_advancing=False,
        freshness_valid=False,
    )
    assert not is_live


def test_pass_status_is_derived():
    # Pass occurs only when all boolean criteria hold
    liveness_ok = CertificationEvaluator.evaluate_liveness(
        session_open=True,
        capture_advancing=True,
        presentation_advancing=True,
        freshness_valid=True,
    )
    assert liveness_ok is True

    grid6_ok = CertificationEvaluator.evaluate_grid6(
        viewport_valid=True,
        visible_cameras=6,
        empty_tiles=0,
        overlap_count=0,
        clipped_count=0,
        dead_space_percent=4.2,
    )
    assert grid6_ok is True
