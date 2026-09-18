# RADAR REFRESH — 2026-09-17 — Serval

## Material discovery

### Flickersoft/serval — v0.2.5 / 596613ccc7b97fe471b09a6bd085c52f57d9f733 — 2026-09-06

- SOURCE_VERIFIED=YES — canonical upstream: `Flickersoft/serval` on GitHub.
- VERSION_OR_REF_VERIFIED=YES — latest stable release `v0.2.5`, published 2026-09-06; release commit/ref observed at `596613ccc7b97fe471b09a6bd085c52f57d9f733`.
- LICENSE_VERIFIED=YES — GNU AGPL-3.0-or-later according to canonical upstream. This is a strong adoption boundary: no direct core copy or product incorporation without explicit legal/license review.
- CAPABILITIES_EXTRACTED=YES — self-hosted/on-device AI; object, scene and speech understanding; local runtime path; WebRTC live view; ONVIF/PTZ; measured testing story; v0.2.5 specifically fixes a process/memory leak.
- TUKEVISION_MAPPING=YES — relevant patterns map to resource hardening, local selective multimodal inference, graceful degradation, live-view latency and future AUDIO observation readiness. TukeVision remains intelligence/monitoring above the DVR/NVR and does not inherit Serval recording architecture.
- ADOPTION_BOUNDARY=YES — `ADAPTAR / BENCHMARK / WATCH`; pattern-only. Do not adopt Serval as NVR, do not move primary recording away from DVR/NVR, do not copy AGPL code into TukeVision core, do not enable continuous speech/scene inference by default.
- REVISIT_CONDITION=YES — revisit if TukeVision opens a measured local audio/scene-understanding requirement, encounters process/RSS leakage under long-running inference, or requires a low-latency local WebRTC benchmark.
- EXPERIENCE_RECORD=YES — `EXP-SERVAL-001` established by this record.

## Why this is material

The source is a newly discovered, active 2026 upstream whose explicit design combines fully local object/scene/speech inference with operational camera handling. Its latest stable release fixes a process/memory leak, which is directly relevant to TukeVision's production-hardening requirement for bounded RSS/process lifecycle. The broader NVR feature set is NOT a reason for adoption and conflicts with TukeVision's primary-recorder boundary.

## Classification

`BENCHMARK + ADAPTAR + WATCH`

Maturity: early (`v0.2.5`); useful as an engineering reference, not as a production dependency.

## TukeVision problem / gate

- Resource hardening: detect process/RSS leakage and orphan inference workers.
- Graceful degradation: AI failure must not blind live CCTV.
- Local-first multimodal readiness: scene/speech understanding remains selective and local when/if activated.
- WebRTC remains auxiliary/conditional, not a core architectural migration.

## Minimum decisive benchmark

1. Run a representative local inference workload for >=30 minutes with process/RSS/thread/queue telemetry.
2. Induce inference-worker failure/restart and verify video/presentation remains available.
3. Compare local selective scene inference against current TukeVision evidence workflow for latency, CPU/RAM and source-linked output.
4. If audio is evaluated, use a controlled local sample only; verify no network egress and classify output as inference, never fact.

PASS only if the pattern demonstrates a measurable improvement without changing the DVR/NVR primary-recorder role or introducing AGPL code into core.

## Risk

- AGPL-3.0-or-later license boundary.
- Early project maturity.
- Feature overlap with NVR responsibilities that TukeVision explicitly rejects.
- Speech/scene inference can increase compute and privacy exposure if made continuous.

## Next gate

`RESOURCE_HARDENING_BENCHMARK` first. Audio/scene understanding remains `WATCH` until a concrete operational requirement exists.

## TES reconciliation required

Add `EXP-SERVAL-001` to `TES/EXPERIENCE_STORE.md`, index the canonical source in `TES/KNOWLEDGE_SOURCE_INDEX.md`, and add Serval as `BENCHMARK/WATCH — pattern only` in `TES/TECHNOLOGY_RADAR.md`. `TES/DECISION_LOG.md` does not change because no architecture/adoption decision changed.
