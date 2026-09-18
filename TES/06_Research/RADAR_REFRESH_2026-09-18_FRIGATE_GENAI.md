# Radar/TES Refresh — 2026-09-18 — Frigate GenAI review

## Material change

### Frigate — annotated frames for GenAI Review

- **SOURCE_VERIFIED:** YES — canonical upstream `blakeblackshear/frigate`.
- **VERSION_OR_REF_VERIFIED:** YES — commit `eccd10cd941a4abdce0cd6ae2aa6b274f7fdbafe`, committed 2026-09-17T16:28:37Z. Stable release remains `v0.18.0` (`77a66e7`, 2026-09-12); this finding is post-release development evidence, not a stable-release adoption signal.
- **LICENSE_VERIFIED:** YES — MIT for Frigate repository source/config/docs; trademark boundary remains separate.
- **CAPABILITIES_EXTRACTED:** GenAI Review can use annotated frames and richer object data to help models that have weak temporal understanding. This is a selective-review pattern, not a reason to run a VLM continuously.
- **TUKEVISION_MAPPING:** P0-64 Evidence Selector; P0-65 Semantic Investigation; investigation/evidence review; FACT/INFERENCE/UNKNOWN contract. Potentially addresses the open design problem of obtaining useful temporal context for selective local VLM review without indexing or semantically processing every CCTV frame.
- **ADOPTION_BOUNDARY:** `ADAPTAR + BENCHMARK`. Do not adopt Frigate as product/NVR. DVR/NVR remains primary recorder. Do not copy external implementation merely because MIT permits reuse; any reuse still requires explicit engineering/license review. Preserve source frames, timestamps and provenance. An annotated frame is derived presentation/evidence context and must never replace or mutate original evidence.
- **REVISIT_CONDITION:** promote only if a local selective-VLM benchmark demonstrates materially better investigation usefulness/temporal interpretation than representative clean frames while staying within CPU/RAM/latency/privacy budgets and preserving traceability.
- **EXPERIENCE_RECORD:** `EXP-FRIGATE-2026-09-18-ANNOTATED-GENAI-REVIEW`.

## Classification

`ADAPTAR | BENCHMARK`

Frigate remains `ACTIVE_ENGINEERING_CANDIDATE / P0-HIGH`; this commit does not justify integrating Frigate or changing the recorder architecture.

## TukeVision problem / gate affected

Current TukeVision direction deliberately avoids continuous VLM and full-frame semantic indexing. The new upstream pattern provides a concrete benchmark candidate for the middle ground:

`representative source frames + deterministic annotations + object metadata -> selective local VLM review -> candidate inference -> source-linked evidence`

Affected capabilities/gates:

- P0-64 Evidence Selector;
- P0-65 Semantic Investigation;
- source-linked investigation;
- provenance / Evidence First;
- selective local VLM benchmark.

## Minimum decisive benchmark

Use the same real DVR/NVR evidence window and the same local VLM/model for both paths:

1. clean representative frames + object metadata;
2. the same representative frames with deterministic annotations + identical object metadata.

Measure:

- investigation-answer usefulness against human-reviewed ground truth;
- temporal/order errors;
- unsupported assertions;
- latency;
- CPU/RAM;
- input/token/image cost where measurable;
- exact traceability from every result to original camera/frame/timestamp.

Gate conditions:

- `ORIGINAL_EVIDENCE_MUTATED=0`;
- `DERIVED_ANNOTATION_PROVENANCE=100%`;
- `UNSUPPORTED_FACT_PROMOTION=0`;
- annotations must be reproducible from stored source-linked observations;
- no external media egress;
- no continuous VLM.

## Secondary upstream change — audio transcription

Commit `334073967b1ab89154652a9ea1e0cd15831f7d01` (2026-09-17T21:34:47Z) adds GenAI-backed audio transcription to Frigate. It is fresh and capability-relevant but **does not cross TukeVision's current adoption threshold**: audio analytics remains RESERVE/WATCH because there is no current operational requirement sufficient to justify the privacy, capture, storage and governance expansion. Classification remains `WATCH / RESERVE`; no separate experience promotion in this refresh.

Revisit audio only when an explicit authorized use case, hardware/source contract, retention policy, privacy assessment and measurable operational benefit exist.

## Other explicitly checked active sources

- ClearCam canonical upstream: latest material ref remains the 2026-09-16 local-Qwen/no-user-ID work already captured by the existing ClearCam experience; no new classification change found in this pass.
- ECC (`affaan-m/ECC`): latest stable release remains `v2.2.1` (2026-09-08). Recent 2026-09-17 commits observed are sponsorship/documentation changes, not a material TukeVision CCTV/runtime capability change.
- ONVIF: TLS Configuration Add-on 2.0 remains Release Candidate published 2026-09-09; no newer primary ONVIF publication found that changes the current TES decision.
- Shinobi canonical GitLab upstream: public upstream still surfaces `c4cb68d0` (2026-08-20) as most recent visible commit; no material delta found.

## Canonical TES reconciliation

Required semantic updates:

- `TES/TECHNOLOGY_RADAR.md`: add annotated-frame selective GenAI review under Frigate active benchmark targets.
- `TES/KNOWLEDGE_SOURCE_INDEX.md`: register canonical ref, license verification, capability mapping, boundary and revisit condition.
- `TES/EXPERIENCE_STORE.md`: add `EXP-FRIGATE-2026-09-18-ANNOTATED-GENAI-REVIEW`.
- `TES/DECISION_LOG.md`: **NO CHANGE** — no architecture/adoption decision changed.

The three large canonical index files are not replaced in this commit because the available GitHub content read is truncated while file update requires complete replacement. Replacing them from partial content would violate the TES history-preservation and Evidence First rules. This refresh is therefore the append-only evidence record and explicit reconciliation blocker; it does not falsely claim canonical-index reconciliation is complete.
