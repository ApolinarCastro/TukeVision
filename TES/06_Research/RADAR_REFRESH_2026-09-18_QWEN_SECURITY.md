# Radar/TES Refresh — 2026-09-18 — Qwen-MM-Plugins security hardening

## Material finding

### QwenLM/Qwen-MM-Plugins — omni-memory log redaction

- `SOURCE_VERIFIED=YES`
- `CANONICAL_UPSTREAM=https://github.com/QwenLM/Qwen-MM-Plugins`
- `VERSION_OR_REF_VERIFIED=YES` — `fac5c9e307737afadd15bacda0314870e886864c`, 2026-09-18
- `LICENSE_VERIFIED=YES` — Apache-2.0 repository license
- `CAPABILITIES_EXTRACTED=YES` — `omni-memory` now redacts environment values and provider messages in the watch/logging path; capability release 1.1.3, distribution train 1.1.7 per upstream commit message.
- `TUKEVISION_MAPPING=YES` — local multimodal investigation/memory tooling, operator observability, secret-safe logs, Evidence First support surfaces.
- `ADOPTION_BOUNDARY=YES` — engineering/reference pattern only. No external CCTV upload, no direct runtime dependency introduced by this refresh, no replacement of detector/tracker/Entity Truth, and AI output remains `OBSERVATION_AI` / candidate lead.
- `REVISIT_CONDITION=YES` — reevaluate before any Qwen-MM plugin is permitted to process TukeVision evidence or when upstream changes local/native media handling, persistence, redaction, provider routing or licensing.
- `EXPERIENCE_RECORD=EXP-QWEN-MM-SEC-001`

## Classification

`ADAPTAR | BENCHMARK`

## Why material

The canonical TES already selects Qwen-MM-Plugins as a multimodal engineering/memory reference under DEC-013. The upstream security change closes a concrete leakage class: environment/provider values reaching logs during the memory watch path. This changes the security evidence for a source already selected as a TukeVision AI reference, even though it does not justify product integration.

## TukeVision problem / gate

- Problem: local AI tooling can remain local-first yet still leak credentials/provider values through logs or diagnostic artifacts.
- Capability/gate: P0-65 Semantic Investigation; future local multimodal evidence tooling; Agent Monitor/observability; secret/provenance boundary.
- Risk: treating local execution as sufficient privacy protection while logs retain secrets or provider payloads.

## Minimum benchmark

Before any integration decision, run an isolated local fixture containing synthetic sentinel environment/provider values through the relevant memory/watch path and assert:

1. sentinel secrets never appear in stdout/stderr/log files;
2. evidence identifiers/provenance needed for audit remain available;
3. no image/video leaves the host;
4. plugin failure cannot block CCTV capture/presentation;
5. output is classified as AI observation/lead, never fact.

## Next gate

Keep Qwen-MM-Plugins as `BENCHMARK / ADAPTAR`. Promote no runtime dependency. Reevaluate only after the redaction benchmark and a concrete P0-65/local-VLM need.

## Same-pass freshness notes

- Frigate: no newer material canonical change identified beyond the already recorded 2026-09-17 GenAI-review/audio refs.
- ClearCam: no newer material canonical change identified beyond the already recorded 2026-09-16 local-Qwen ref.
- ECC: latest visible release remains v2.2.1; recent sponsor/documentation changes do not alter CCTV/product capability.
- ONVIF: no new material release found beyond the already tracked Media Signing/TLS/spec work.
- OpenBMB MiniCPM/MiniCPM-V: current local/edge candidates remain covered by DEC-013; no same-pass change requiring a new TukeVision decision was identified.
- OpenViewer / `sonnvntu/openviewer-releases`: remains reference-only under the existing provenance/license boundary; no promotion.
- Shinobi canonical GitLab: latest visible commit remains `c4cb68d0` (2026-08-20); no material delta found.

## Permanent boundaries

`LOCAL_FIRST`; DVR/NVR remains primary recorder; Evidence First; vendor-neutral; no biometrics; no customer CCTV upload to external services; no third-party code copied into TukeVision core by this refresh.
