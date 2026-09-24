# Radar Refresh — 2026-09-24

## Material discovery: BigBrother CCTV 2.4

**SOURCE_ID:** `BIGBROTHER-CCTV-24`  
**FORGE:** GitHub  
**CANONICAL_UPSTREAM:** `https://github.com/bluedalmatian/bigbrother`  
**PROJECT_SITE:** `https://www.bigbrothercctv.org/`  
**VERSION:** `2.4`  
**LAST_VERIFIED_REF:** `1277ad1b0ddc3e4188e62432ba3b8d3d1ed376cc` (`version 2.4 packages`, 2026-09-20)  
**RELEASE_DATE:** 2026-09-21  
**LICENSE:** software GPL-3.0; bundled AI model uses separate BigBrother AI Model License 1.1  
**TES_CLASSIFICATION:** `BENCHMARK | ADAPTAR (PATTERN-ONLY)`  
**DIRECT_CODE_REUSE:** `NO`  
**DIRECT_PRODUCT_INTEGRATION:** `NO`

### Validation minimum

- `SOURCE_VERIFIED=YES` — project site links the GitHub repository as source.
- `VERSION_OR_REF_VERIFIED=YES` — site reports v2.4 (2026-09-21); GitHub HEAD observed at `1277ad1b...` with v2.4 packages.
- `LICENSE_VERIFIED=YES` — source code GPL-3.0; AI model is explicitly outside GPL and governed by BigBrother AI Model License 1.1.
- `CAPABILITIES_EXTRACTED=YES` — FFmpeg RTSP/HTTP ingest, reconnect retry, HLS live mirroring, event snapshots, faster person/vehicle detection, NVIDIA acceleration, experimental ONVIF PTZ, Linux/FreeBSD/Raspberry Pi OS.
- `TUKEVISION_MAPPING=YES` — RTSP/FFmpeg lifecycle and recovery, Gate 0C live-view transport, Gate 1 ONVIF/PTZ interoperability, selective event evidence and hardware-acceleration benchmarking.
- `ADOPTION_BOUNDARY=YES` — use only as engineering benchmark/pattern source; do not copy GPL code, do not adopt separately licensed AI model, and do not turn TukeVision into a recorder/NVR.
- `REVISIT_CONDITION=YES` — revisit if its reconnect/lifecycle or ONVIF PTZ behavior materially outperforms current TukeVision/ClearCam/Frigate patterns on the same hardware/camera, or if license/model terms change.
- `EXPERIENCE_RECORD=EXP-BIGBROTHER-001`.

## Experience record — `EXP-BIGBROTHER-001`

**PROBLEM:** TukeVision needs vendor-neutral evidence for simple FFmpeg stream recovery and ONVIF/PTZ interoperability without assuming NVR ownership.  
**PATTERN:** keep camera ingest/retry and live presentation operationally simple; treat PTZ capability as negotiated/experimental until verified on physical hardware; separate code license from model license.  
**TUKEVISION_DECISION:** `BENCHMARK | ADAPTAR (PATTERN-ONLY)`.

### Material change / relevance

Version 2.4 adds faster event detection, supported NVIDIA GPU acceleration, restored FreeBSD packages, and experimental unofficial ONVIF PTZ. The upstream explicitly states that ONVIF compatibility has not been tested or approved by ONVIF. This is relevant as an independent CCTV/FFmpeg implementation and as a negative reminder that protocol support claims are not physical interoperability evidence.

### TukeVision boundary

Permanent limits remain unchanged:

- `LOCAL_FIRST`.
- DVR/NVR remains the primary recorder.
- Evidence First.
- provider neutrality.
- `AI result = lead, no fact`.
- no biometrics.
- provenance and license verification required.

BigBrother's continuous-recording/storage role is therefore **not** adopted. Its GPL source is **not** copied into the core. Its separately licensed AI model is **not** adopted. No runtime, tests, dependencies, configuration or product code are changed by this refresh.

### Minimum benchmark

If activated, compare against the current TukeVision baseline and existing ClearCam/Frigate evidence using the same camera/hardware:

1. RTSP disconnect → reconnect recovery time and stale-frame behavior.
2. FFmpeg process ownership/cleanup after repeated failures.
3. CPU/RAM and latency for live presentation without recording ownership.
4. ONVIF PTZ capability discovery and command failure behavior on real hardware; never infer compatibility from documentation alone.
5. NVIDIA acceleration only on representative hardware, measuring throughput, latency and recovery regressions.

**NEXT_GATE:** no implementation. Revisit only when a measured TukeVision gap matches one of the above patterns or physical Gate 1 hardware enables an interoperability benchmark.

## Mandatory-source sweep

The current canonical HEAD was read first. Since the prior canonical update, GitHub commit checks found no newer commits in `blakeblackshear/frigate`, `roryclear/clearcam`, `affaan-m/ECC`, `onvif/media-signing-framework`, `onvif/specs`, `QwenLM/Qwen-MM-Plugins`, `OpenBMB/MiniCPM`, `OpenBMB/MiniCPM-V`, or `sonnvntu/openviewer-releases`. Shinobi's canonical GitLab evidence reviewed in this sweep did not expose a newer material change than the already-recorded live-grid/substream/ONVIF work. No decision-log change is warranted.

---

## Material update: Frigate restart-rate observability hardening

**SOURCE_ID:** `FRIGATE-OSS`  
**FORGE:** GitHub  
**CANONICAL_UPSTREAM:** `https://github.com/blakeblackshear/frigate`  
**LAST_VERIFIED_REF:** `397f5253a568abddbe0f7968fd99b400ca9f1ac0` (2026-09-24)  
**LICENSE:** MIT  
**TES_CLASSIFICATION:** `ADAPTAR | BENCHMARK`  
**DIRECT_PRODUCT_INTEGRATION:** `NO`

### Validation minimum

- `SOURCE_VERIFIED=YES` — canonical Frigate upstream verified on GitHub.
- `VERSION_OR_REF_VERIFIED=YES` — commit `397f5253...` verified on 2026-09-24.
- `LICENSE_VERIFIED=YES` — MIT at the verified ref.
- `CAPABILITIES_EXTRACTED=YES` — event-rate/FPS observability now prevents restart-buffer bursts from being interpreted as 100+ FPS by enforcing a minimum one-second denominator while preserving true sub-second configured windows.
- `TUKEVISION_MAPPING=YES` — FFmpeg restart/recovery observability, detector health metrics, stale/buffered-frame diagnosis and operator telemetry.
- `ADOPTION_BOUNDARY=YES` — adapt the invariant/benchmark only; do not adopt Frigate as recorder/NVR and do not change runtime in this TES refresh.
- `REVISIT_CONDITION=YES` — activate implementation work only if TukeVision telemetry shows restart-adjacent FPS/rate spikes, misleading detector-health values or alerting derived from undersized elapsed-time windows.
- `EXPERIENCE_RECORD=EXP-FRIGATE-RATE-001`.

## Experience record — `EXP-FRIGATE-RATE-001`

**PROBLEM:** immediately after an FFmpeg/detector restart, buffered events can be counted over only a few milliseconds and create physically misleading FPS/rate telemetry.  
**PATTERN:** health/rate metrics must define an explicit observation-window contract and must not divide restart bursts by an accidentally tiny elapsed interval. Frigate's fix uses at least a one-second divisor for the normal case while keeping intentionally configured sub-second windows internally consistent.  
**TUKEVISION_DECISION:** `ADAPTAR | BENCHMARK`; pattern only.

### Materiality and TukeVision mapping

This is material because it changes the trustworthiness of lifecycle observability rather than merely refactoring implementation. A false 100+ FPS signal immediately after recovery can hide instability, corrupt health interpretation or trigger incorrect operational conclusions. For TukeVision the relevant gate is lifecycle/observability around RTSP/FFmpeg recovery; the DVR/NVR remains the primary recorder.

### Minimum benchmark

1. Force repeated RTSP/FFmpeg restarts with buffered frames pending.
2. Capture raw event/frame counts, elapsed observation time and reported FPS/rate before/during/after recovery.
3. Assert no impossible restart-adjacent spike is emitted solely because elapsed time is a few milliseconds.
4. Verify a deliberately configured sub-second measurement window still reports its intended true rate.
5. Confirm health/alert logic consumes the stabilized metric without masking real sustained overload.

**RISK:** over-smoothing could hide a genuine short burst; therefore the raw count, elapsed window and stabilized health metric should remain distinguishable in evidence/telemetry.  
**NEXT_GATE:** benchmark against current TukeVision restart telemetry before any product-code change.

### Sweep delta

The previous mandatory-source statement above describes the earlier same-day sweep. A later check found this new Frigate commit at 2026-09-24T12:28:00Z. No new material decision change was found in the other mandatory sources during this refresh. `DECISION_LOG.md` remains unchanged because the Frigate boundary and classification are not changed; only a new engineering/observability pattern is recorded.
