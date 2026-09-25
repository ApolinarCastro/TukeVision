# Radar Refresh — 2026-09-24 — Qwen-MM-Plugins headless lifecycle

## Material change

**Source:** `QwenLM/Qwen-MM-Plugins`  
**Canonical upstream:** https://github.com/QwenLM/Qwen-MM-Plugins  
**Verified ref:** `07736672525443c7f8a3f6405eed37d2236f023f` (2026-09-23)  
**License:** Apache-2.0  
**Classification:** `ADAPTAR | BENCHMARK`  
**Experience record:** `EXP-QWEN-MM-HEADLESS-001`

Upstream merged deterministic headless installer actions that unify configuration and expose non-interactive `install`, `update`, `uninstall`, `verify` and configuration operations, with explicit plugin/harness selection, preflight validation and dry-run support. This is material for TukeVision's controlled tooling/research lifecycle because it provides a reference pattern for auditable, non-interactive capability management without requiring GUI state.

## Minimum validation

`SOURCE_VERIFIED=YES` — canonical GitHub repository verified.  
`VERSION_OR_REF_VERIFIED=YES` — merge commit `07736672525443c7f8a3f6405eed37d2236f023f`.  
`LICENSE_VERIFIED=YES` — Apache-2.0 repository license.  
`CAPABILITIES_EXTRACTED=YES` — deterministic headless lifecycle actions, explicit target selection, preflight validation, dry-run.  
`TUKEVISION_MAPPING=YES` — research/tooling lifecycle and future local multimodal adapter operations; no product-runtime adoption authorized.  
`ADOPTION_BOUNDARY=YES` — pattern-only; do not add Qwen-MM-Plugins as runtime dependency, do not enable cloud CCTV paths, do not copy external code into core.  
`REVISIT_CONDITION=YES` — benchmark only when TukeVision needs repeatable non-interactive install/update/verify lifecycle for an approved local adapter or research tool.  
`EXPERIENCE_RECORD=EXP-QWEN-MM-HEADLESS-001`.

## TukeVision mapping

- **Problem affected:** reproducible and auditable lifecycle of optional local multimodal/research adapters.
- **Gate/capability:** research/tooling governance; future P0-65/P0-66 local selective VLM support only if separately authorized.
- **Risk:** installer automation can mutate dependencies/configuration or widen network/credential scope if copied into product operation.
- **Minimum benchmark:** on an isolated disposable workspace, prove dry-run produces no mutation; explicit target selection rejects ambiguity; verify detects drift; update/uninstall remain scoped to the selected adapter; no credential leaves its approved origin; no CCTV media leaves the local environment.
- **Next gate:** no implementation now. Revisit only when an approved local adapter requires deterministic lifecycle automation.

## Adoption boundary

This refresh changes TES knowledge only. It does **not** authorize runtime, test, dependency, configuration or product-code changes. `LOCAL_FIRST`, DVR/NVR as primary recorder, Evidence First, vendor neutrality, `AI result = lead, not fact`, no biometrics, and verified license/provenance remain unchanged.

`DECISION_LOG` is intentionally unchanged: the upstream change supplies a reusable engineering pattern but does not alter a standing TukeVision product decision.
