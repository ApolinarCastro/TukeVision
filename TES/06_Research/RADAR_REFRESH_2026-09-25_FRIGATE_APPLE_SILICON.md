# Radar Refresh — 2026-09-25 — Frigate Apple Silicon / ONNX

## Materiality verdict

**MATERIAL CHANGE = YES** — compatibility/maturity boundary expanded for a currently active benchmark source. This does **not** change the current Intel/OpenVINO production profile and does not authorize a runtime/dependency/configuration change.

## Source validation

- **SOURCE_VERIFIED:** `blakeblackshear/frigate` (canonical GitHub upstream).
- **VERSION_OR_REF_VERIFIED:** commit `c959df32c9b5a56fe6e49ae2b90082a0ba9475a7`, 2026-09-24.
- **LICENSE_VERIFIED:** MIT at the verified ref (`LICENSE`).
- **CAPABILITIES_EXTRACTED:** Frigate added Apple Silicon support through the `lighter` container runtime: ONNX Runtime plugin execution provider for Apple Neural Engine, hardware H.264/H.265 decode through the media engine, hardware probe/reporting, codec-specific presets, and fallback to default ONNX providers if the Neural Engine provider/model cannot load.
- **TUKEVISION_MAPPING:** affects the conditional ONNX Runtime / alternative-hardware path and the hardware-neutral inference/decode benchmark boundary; no current Intel/OpenVINO gap is created.
- **ADOPTION_BOUNDARY:** pattern/benchmark only. Do not add `lighter`, ONNX Runtime, Apple-specific presets, Frigate code, dependencies or configuration to TukeVision from TES. DVR/NVR remains primary recorder; LOCAL_FIRST and Evidence First remain mandatory.
- **REVISIT_CONDITION:** activate a TukeVision benchmark only if Apple Silicon becomes a supported deployment target or the current Intel/OpenVINO profile fails a measured portability/cost/performance requirement.
- **EXPERIENCE_RECORD:** `EXP-FRIGATE-APPLE-SILICON-001` (this document).

## Classification

**BENCHMARK | WATCH**

The upstream change is material because it demonstrates a mature CCTV reference using one ONNX model path across another edge accelerator while keeping decode acceleration and inference-provider discovery explicit. It is not an integration decision for the current TukeVision hardware profile.

## TukeVision impact record

| Field | Value |
|---|---|
| Upstream | `blakeblackshear/frigate` |
| Version/ref | `c959df32c9b5a56fe6e49ae2b90082a0ba9475a7` |
| Upstream date | 2026-09-24 |
| License | MIT |
| Material change | Apple Silicon Neural Engine ONNX execution + media-engine H.264/H.265 decode via `lighter`; explicit provider fallback |
| Problem affected | future hardware portability; local inference/decode acceleration boundary |
| Gate/capability | conditional ONNX Runtime / hardware-platform benchmark; no current gate promotion |
| Risk | community integration; extra container-runtime/device layer; codec-specific decode path; benchmark numbers are upstream evidence, not TukeVision evidence |
| Minimum benchmark | same local CCTV clip/model: inference latency, sustained FPS, decode CPU, RAM, first-frame/recovery behavior, fallback correctness, thermal stability; compare against current Intel/OpenVINO baseline |
| Next gate | only if Apple Silicon becomes a real target or current profile fails an objective portability/performance requirement |

## Engineering pattern extracted

`ACCELERATOR_AVAILABLE != MODEL_LOAD_SUCCESS`. Hardware discovery, provider registration, model-session creation and fallback must be separate observable states. Likewise, video decode acceleration is codec/device specific and must not be inferred merely from host architecture.

## Permanent limits preserved

- `LOCAL_FIRST`
- DVR/NVR remains primary recorder
- Evidence First
- vendor neutrality
- `AI result = lead, not fact`
- no biometrics
- license/provenance verification

## Decision log

No decision changed. `TES/DECISION_LOG.md` is intentionally untouched.
