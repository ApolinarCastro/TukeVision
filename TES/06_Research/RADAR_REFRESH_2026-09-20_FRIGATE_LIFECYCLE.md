# Radar Refresh — 2026-09-20 — Frigate lifecycle / tracking / observability

## Material finding

- SOURCE_ID: `FRIGATE-OSS`
- SOURCE_VERIFIED: YES
- CANONICAL_UPSTREAM: `blakeblackshear/frigate`
- VERSION_OR_REF_VERIFIED: YES — commit `52f50a7396ebdef7a22aa9682b275ca4828f6399`, 2026-09-20
- LICENSE_VERIFIED: YES — MIT (code/config/docs; Frigate marks/logo excluded)
- CAPABILITIES_EXTRACTED: YES
- TUKEVISION_MAPPING: YES
- ADOPTION_BOUNDARY: YES
- REVISIT_CONDITION: YES
- EXPERIENCE_RECORD: `EXP-FRIGATE-2026-09-20-LIFECYCLE-TRACKING`
- CLASSIFICATION: `ADAPTAR | BENCHMARK`

## What changed materially

Upstream commit `52f50a7` fixes several failure modes directly relevant to TukeVision's active engineering gaps:

1. **Runtime camera-add race / process lifecycle**: the audio process could reach a newly-added camera before shared camera metrics existed, causing a `KeyError` and taking down the whole audio manager. Upstream now waits for required state and registers the audio process with the watchdog.
2. **Tracking state isolation**: expiration of one stationary object could incorrectly drop other healthy tracked objects of the same label. The fix removes only the intended target.
3. **Motion recovery after scene/config transitions**: `skip_motion_threshold` could permanently suppress motion because skipped frames never updated the background model. Upstream now blends the frame before early return so the background converges and motion resumes.
4. **FFmpeg restart observability**: restart paths now dump the relevant FFmpeg log tail consistently, including stale-record and crash paths, without duplicate empty dumps.

These are not cosmetic changes. They expose reusable engineering patterns for race-free dynamic source lifecycle, per-entity state isolation, recovery after scene transitions, watchdog coverage and failure-context capture.

## TukeVision mapping

- Gate 0C / live multicamera freshness and recovery.
- lifecycle/reconnect supervision and dynamic source add/remove.
- tracking continuity / prevention of collateral ID-state loss.
- observability around FFmpeg restart and stale-stream recovery.
- resource/process health separation from presentation health.

## Adoption boundary

`FRIGATE-OSS` remains an engineering reference, not a product dependency. TukeVision MUST NOT become a second NVR. DVR/NVR remains the primary recorder. No Frigate storage/recording architecture is imported. Patterns may be reimplemented only where TukeVision evidence demonstrates the same class of failure.

## Risk

- Frigate's process topology differs from TukeVision; a fix is evidence of a failure pattern, not proof that TukeVision has the identical defect.
- Audio-specific behavior remains outside current priority and privacy scope; only the lifecycle/watchdog pattern is relevant.
- Tracking implementation differs; benchmark behavior, not code transplantation.

## Minimum benchmark

Use the certified/local baseline and induce four bounded cases independently:

1. add/remove/re-add a source while worker state is initializing;
2. expire one stationary tracked object while peer objects of the same class remain active;
3. force a large scene/background transition and verify motion detection recovers without restart;
4. force an FFmpeg/source restart and verify exactly one bounded diagnostic context is retained with source identity and timestamp.

Measure: stale-frame duration, recovery time, worker/process survival, collateral track loss/ID switches, motion recovery time, CPU/RAM delta and provenance of restart diagnostics.

PASS requires no regression to existing certified behavior and no mutation/invention of Evidence.

## Next gate

`BENCHMARK` only when the corresponding TukeVision defect/gate is active. Promote a pattern to implementation only if a reproducible TukeVision FAIL demonstrates the same class and the minimal adaptation turns it PASS.

## Permanent constraints preserved

`LOCAL_FIRST`; DVR/NVR primary recorder; Evidence First; vendor neutrality; AI result = lead, not fact; no biometrics; no customer CCTV upload to external services; license/provenance verified.
