# Radar refresh — 2026-09-22 — ECC agent-harness security

## Verdict

`MATERIAL_CHANGE=YES`

`affaan-m/ECC` is explicitly monitored by the Radar and was not yet represented in the canonical TES source index/searchable records. Fresh upstream security changes provide two reusable governance patterns for future TukeVision tool-enabled automation:

- sanitize dangerous invisible Unicode in untrusted paths/identifiers before presenting denial or approval evidence to humans;
- do not allow a failed prerequisite step to continue supplying evidence that can make downstream dependent gates pass.

Classification: `ADAPTAR | BENCHMARK`.

## Validation matrix

| Requirement | Result |
|---|---|
| SOURCE_VERIFIED | YES — `affaan-m/ECC` |
| VERSION_OR_REF_VERIFIED | YES — `bf70150e`, with related `8b951d3b` |
| LICENSE_VERIFIED | YES — MIT |
| CAPABILITIES_EXTRACTED | YES |
| TUKEVISION_MAPPING | YES — agent/tool security + Evidence First gate semantics |
| ADOPTION_BOUNDARY | YES — pattern-only; no dependency/code adoption |
| REVISIT_CONDITION | YES — autonomous file/repo tooling or evidence-chain expansion |
| EXPERIENCE_RECORD | `EXP-ECC-SECURITY-001` |

## Materiality and boundary

This changes TES knowledge/security readiness, not product architecture. It does not justify modifying `DECISION_LOG.md`: existing LOCAL_FIRST, Evidence First, least-privilege/safe-tooling and provenance boundaries remain valid. No runtime, tests, dependencies, configuration or product files are changed.

ClearCam `20ea21c0` was also inspected: it only advances its pinned tinygrad commit in `requirements.txt`; no demonstrated TukeVision capability, compatibility or decision change was established, so no TES decision change is recorded for that update.

Qwen-MM-Plugins changes after the already-recorded `video-spatio` capability were README/community-link/badge changes and are non-material. Frigate's latest observed material DEEPX NPU work is already represented by the preceding canonical refresh; no new decision change is required in this run.
