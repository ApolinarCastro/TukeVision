# Radar Refresh — 2026-09-16

## Material change: ClearCam local Qwen without vendor identity

- **SOURCE_ID:** `CLEARCAM-RORYCLEAR`
- **SOURCE_VERIFIED:** YES — canonical upstream `roryclear/clearcam`
- **VERSION_OR_REF_VERIFIED:** YES — `84b8740a6c5fb103d24714fdc8d9af997192115e`
- **REF_DATE:** 2026-09-15 author / 2026-09-16 upstream commit
- **LICENSE_VERIFIED:** YES — GPL-3.0 boundary already recorded; direct core copy remains prohibited
- **CAPABILITIES_EXTRACTED:** YES
- **TUKEVISION_MAPPING:** YES
- **ADOPTION_BOUNDARY:** YES
- **REVISIT_CONDITION:** YES
- **EXPERIENCE_RECORD:** PENDING_CANONICAL_RECONCILIATION (`EXP-CLEARCAM-009` proposed below)

### What changed

ClearCam changed its settings path so absence of the ClearCam key no longer forces `use_qwen=False`; only the vendor `userID` is cleared. This makes local Qwen execution independent from ClearCam user identity/key. The immediately preceding upstream commits include regression coverage around the newer Telegram path and a revert, so the verified material point is specifically the Qwen/key decoupling in `84b8740a...`.

### TukeVision problem addressed

TukeVision requires local-first selective VLM interpretation without vendor identity, cloud account or external-service dependency. This upstream change strengthens the already-recorded `EXP-CLEARCAM-008` self-hosted event-path pattern by demonstrating that the local Qwen path can remain enabled when vendor credentials are absent.

### Classification

`ADAPTAR / BENCHMARK`

ClearCam remains `ACTIVE_ENGINEERING_CANDIDATE / HIGH`. No product adoption, no second NVR and no GPL code copy.

### Mapping

- P0-62 selective inference
- P0-65 semantic investigation
- P0-76 local AI/VLM path
- future LAN event/notification delivery
- local-first / offline operation

### Risk

The upstream commit is recent and unsigned, and it changes a small conditional rather than publishing a stable release. Treat it as engineering evidence/pattern, not a certified implementation. Validate behavior independently in TukeVision before any design decision.

### Minimum decisive benchmark

`LOCAL EVENT -> SELECTIVE LOCAL QWEN -> STRUCTURED RESULT -> LOCAL/LAN EVIDENCE PATH`

Acceptance checks:
1. no vendor account/key required;
2. zero customer media egress to Internet;
3. bounded queue/backpressure;
4. AI failure does not interrupt core video;
5. output remains `OBSERVATION_AI`, never canonical evidence truth;
6. compare latency/CPU/RAM against no-VLM baseline.

### Next gate

Do not interrupt Gate 0C. Revisit when the local selective-VLM/event slice is authorized, or earlier only if a Gate 0C diagnostic explicitly needs semantic interpretation.

### Proposed Experience Store record

`EXP-CLEARCAM-009 — VENDOR_IDENTITY_DECOUPLED_LOCAL_QWEN`

Pattern: `NO_VENDOR_KEY -> LOCAL_QWEN_STILL_AVAILABLE -> LOCAL_RESULT_PATH`, with GPL boundary and independent benchmark requirement.

## Other mandatory active-source checks

- **Frigate:** canonical GitHub release remains `v0.18.0` (`77a66e7`, 2026-09-12). No newer stable release was found in this execution; no classification change. Its 0.19 development branch contains breaking work and is not promoted into TES on that basis.
- **Shinobi:** canonical GitLab upstream remains the first-class source; no newer material release/commit was established in this execution that changes the current `BENCHMARK / ADAPT_PATTERN_ONLY` decision.
- **ONVIF:** TLS Configuration Add-on 2.0 remains Release Candidate dated 2026-09-09; no newer final publication established in this execution.
- **ECC / affaan-m/ECC:** explicitly checked as required; no CCTV-specific material change established that changes the current TukeVision decision.

## Canonical reconciliation status

`TECHNOLOGY_RADAR.md`, `KNOWLEDGE_SOURCE_INDEX.md` and `EXPERIENCE_STORE.md` require canonical reconciliation for this new ClearCam ref/experience. The available GitHub write action replaces complete files rather than applying a safe partial patch; because these TES files are large and the connector returns them in truncated/ranged reads, this execution does **not** overwrite them and risk deleting preserved history. `DECISION_LOG.md` remains unchanged because no adoption/architecture decision changed.

This refresh file preserves the verified evidence without modifying runtime, code, tests, dependencies or configuration.