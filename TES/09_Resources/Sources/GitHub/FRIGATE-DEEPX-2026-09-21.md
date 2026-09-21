# Source Record — Frigate DEEPX NPU — 2026-09-21

- **CANONICAL_UPSTREAM:** `https://github.com/blakeblackshear/frigate`
- **FORGE:** GitHub
- **VERIFIED_REF:** `af0ba191966812cf9ac8515d95b1dd221363d17e`
- **VERIFIED_DATE:** 2026-09-21
- **LICENSE:** MIT
- **SOURCE_VERIFIED:** YES
- **VERSION_OR_REF_VERIFIED:** YES
- **LICENSE_VERIFIED:** YES
- **CAPABILITIES_EXTRACTED:** YES
- **TUKEVISION_MAPPING:** hardware acceleration / detector abstraction / future edge portability
- **ADOPTION_BOUNDARY:** pattern/benchmark only; no Frigate dependency; no second NVR; no runtime change without hardware evidence
- **REVISIT_CONDITION:** real DEEPX target hardware or demonstrated gap in current OpenVINO profile
- **EXPERIENCE_RECORD:** `EXP-FRIGATE-DEEPX-001` in `TES/06_Research/RADAR_REFRESH_2026-09-21_FRIGATE_DEEPX.md`
- **CLASSIFICATION:** `BENCHMARK | RESERVE`

## Material change

Frigate added DEEPX NPU detector/runtime integration with model/driver integrity checks, SSD and DAMO-YOLO support, anchor-free/PPU decoding, YOLO-generic/YOLOX handling, configurable score/NMS thresholds and latency documentation.

## TukeVision consequence

This does not justify replacing OpenVINO in the current Intel profile. It strengthens the architectural requirement that detector/inference boundaries remain hardware-neutral enough to benchmark a new accelerator without contaminating capture, evidence, investigation or DVR/NVR ownership.

## Minimum benchmark

On real DEEPX hardware only: identical model/dataset/workload versus current backend; accuracy, p50/p95 latency, sustained FPS, CPU/RAM, accelerator load, >=1800 s stability, failure/recovery and evidence provenance. Upstream latency is not accepted as TukeVision performance evidence.