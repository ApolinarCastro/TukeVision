# TukeVision — Repository Agent Instructions

This file is the root entry point for repository-local agent behavior.

## Mandatory governance

Before material analysis, architecture changes, code changes, debugging, testing, recommendations, or continuation:
1. Read the current project state from the repository, not from chat memory.
2. Apply `TES/ACTIVE_EVALUATION_PROTOCOL.md`, `TES/DECISION_LOG.md`, `TES/TECHNOLOGY_RADAR.md`, `TES/KNOWLEDGE_SOURCE_INDEX.md`, and the current capability/evidence state when applicable.
3. Preserve `FACT != INFERENCE`, `INFERENCE != EVIDENCE`, `NO_EVIDENCE != NEGATIVE_EVIDENCE`, and `UNKNOWN` as a valid state.
4. Never promote `NOT_TESTED` directly to `PASS`.
5. Never claim physical validation without physical/runtime evidence.

## Mandatory repository skills

Repository skills live under `.agents/skills/`.

Use the following skill whenever its trigger applies:

- `$tukevision-project-execution-gate`: before any material project work or architectural recommendation.
- `$tukevision-evidence-first`: whenever evidence, provenance, factual claims, investigations, audit trails, media integrity, or certification are involved.
- `$tukevision-stream-onboarding`: whenever RTSP, ONVIF, LAN/DVR discovery, source onboarding, credentials, or camera capability negotiation are involved.
- `$tukevision-edge-ai-benchmark`: whenever considering a detector, tracker, VLM, inference runtime, model cascade, accelerator, or hardware portability change.
- `$tukevision-agent-governance`: whenever Agent Monitor, autonomy, tools/actions, routing, reasoning, escalation, safe mode, or model-driven decisions are involved.
- `$tukevision-technology-radar`: whenever reviewing external technology, repositories, standards, papers, books, vendor capabilities, or proposing a new dependency/pattern.

Read the selected `SKILL.md` first and load only the supporting TES material needed for that task.

## Architectural boundaries

- TukeVision is local-first and vendor-neutral.
- DVR/NVR remains the primary recorder.
- Customer CCTV is not uploaded to external services without an explicit approved privacy/security decision.
- No biometrics by default.
- AI output is a lead/observation, not a fact.
- Deterministic safety and policy rules have precedence over probabilistic/model recommendations.
- Do not introduce a second NVR, duplicate a working subsystem, or add infrastructure without a demonstrated gap.
