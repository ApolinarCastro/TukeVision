# LOOP-0019A-QW04-R3 — TDD evidence

Date: 2026-08-18
Base commit: `0f214ca169358a0980e1324650d046e53f625557`

## User-visible guarantees

| Guarantee | Automated proof |
|---|---|
| The operational multicamera runtime creates QW-04 clips from the exact frame and timestamp already processed by the pipeline. | `test_runtime_passes_the_exact_existing_frame_and_timestamp_to_qw04` |
| The integration is instantiated once and does not open a second capture path. | `test_runtime_instantiates_qw04_once_without_second_capture` |
| Each camera has isolated bounded buffering and produces linked clip/QW-00 records. | `test_four_camera_frames_generate_isolated_clips_and_qw00_records` |
| Stop joins the pipeline and then flushes QW-04 deterministically. | `test_clean_close_joins_pipeline_then_flushes_qw04` |
| Backend failures retain a static evidence fallback without taking down the runtime. | `test_backend_failure_exports_static_fallback_and_does_not_raise` |
| A repeated pending signal does not duplicate the review dataset. | `test_repeated_pending_signal_does_not_duplicate_review_record` |
| Pending-bound overflow cannot crowd reproducible clips out of QW-00. | `test_pending_bound_skips_extra_signal_without_crowding_qw00` |

## RED checkpoints

- `4be9793` — the operational linkage tests failed because `src.app.runtime_qw04` did not exist.
- `31c1123` — the pending-bound protection failed because the second, rejected signal was exported as an unavailable QW-00 candidate.

## GREEN checkpoints

- `aebec61` — integrated the existing `EvidenceClipAdapter`, `TemporalClipCoordinator`, bounded exporter and QW-00 contract into `scripts/run_multicamera.py`.
- `516c554` — retained accepted clip candidates while excluding pending-bound overflow from QW-00.

## Verification

- Focused integration/regression: `66/66 PASS`.
- Full regression: `454/454 PASS + 4 optional skips`.
- New regressions: `0`.
- Compileall (`src`, `scripts`, `tests`): `PASS`.
- Secret scan: `22/22 PASS`.
- `git diff --check` from the declared base: `PASS`.
- Coverage command: not available because the local environment does not include the `coverage` package; no dependency was installed or configuration changed.

Physical CCTV and operator validation are intentionally not claimed by this document.
