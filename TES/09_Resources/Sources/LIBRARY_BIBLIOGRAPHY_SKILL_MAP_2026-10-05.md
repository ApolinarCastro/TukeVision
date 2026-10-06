# Library Bibliography -> Repository Skills Map — 2026-10-05

## Scope

This record documents the knowledge synthesis used to create the root-scoped repository skills under `.agents/skills/`.

The source corpus was selected from the user's Library by semantic relevance to TukeVision: CCTV/video analytics, RTSP/ONVIF, edge AI, evidence/provenance, agentic governance, model evaluation, technology radar, and existing TukeVision engineering records.

## Material source groups

### 1. TukeVision engineering history and TES-derived notes
Reusable themes:
- local-first and vendor-neutral architecture;
- DVR/NVR remains primary recorder;
- resilient RTSP lifecycle;
- event-triggered VLM;
- semantic evidence over representative frames;
- structured/versioned records;
- privacy-aware investigation;
- technology discovery -> upstream verification -> benchmark;
- Experience/Failure -> reusable knowledge.

### 2. TukeVision Agent Monitor plans and walkthroughs
Reusable themes:
- deterministic attention/orchestration before model reasoning;
- FACT/INFERENCE/UNKNOWN separation;
- read-only tool policy and default deny;
- kill switch/safe mode preserving CCTV core;
- source health awareness and provenance.

### 3. AI Engineering — Building Applications with Foundation Models
Reusable themes:
- evaluation-driven development;
- evaluate components and systems;
- tie technical evaluation to business outcomes;
- explicit cost/latency/throughput metrics;
- context/tools/guardrails/router progression;
- build-vs-buy and on-device model selection;
- monitoring, traces, feedback loops;
- structured outputs and tool governance.

### 4. Project audits and implementation plans
Reusable themes:
- evidence before certification;
- prevent documentation/runtime contradictions;
- finite gates and regression protection;
- preserve certified components unless a direct dependency is demonstrated.

## Skills created

1. `tukevision-project-execution-gate`
2. `tukevision-evidence-first`
3. `tukevision-stream-onboarding`
4. `tukevision-edge-ai-benchmark`
5. `tukevision-agent-governance`
6. `tukevision-technology-radar`

## Excluded from skill conversion

The following are intentionally not converted into skills:
- branding-only instructions;
- obsolete implementation proposals;
- vendor-specific feature lists without a reusable workflow;
- unverified performance claims;
- project-history facts that belong in TES rather than procedural instructions;
- recommendations that conflict with current canonical decisions.

## Placement decision

For Codex-compatible repository-scoped discovery, the skills are installed at:

`.agents/skills/<skill-name>/SKILL.md`

The repository root `AGENTS.md` is the mandatory routing/usage entry point.

No runtime, tests, dependencies, model files, or product configuration are changed by this skill installation.
