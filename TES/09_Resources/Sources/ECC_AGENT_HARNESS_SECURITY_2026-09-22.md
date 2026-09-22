# ECC agent-harness security patterns — 2026-09-22

## Source validation

- `SOURCE_ID=ECC-AGENT-HARNESS`
- `CANONICAL_UPSTREAM=https://github.com/affaan-m/ECC`
- `SOURCE_VERIFIED=YES`
- `VERSION_OR_REF_VERIFIED=YES` — `bf70150eb2df8070024e5bdf08e4aa08959e2735` (2026-09-21)
- `LICENSE_VERIFIED=YES` — MIT
- `CAPABILITIES_EXTRACTED=YES`
- `TUKEVISION_MAPPING=YES`
- `ADOPTION_BOUNDARY=YES`
- `REVISIT_CONDITION=YES`
- `EXPERIENCE_RECORD=EXP-ECC-SECURITY-001`

## Material change

ECC is an agent-harness optimization/security project rather than CCTV runtime. Commit `bf70150e` hardened GateGuard denial-path rendering by stripping dangerous invisible Unicode, including zero-width characters, variation selectors, tag characters, bidi-adjacent/invisible ranges, C1 controls and line/paragraph separators. The stated failure mode is security-review deception: a malicious path can look clean to a human while containing hidden code points.

A neighboring commit, `8b951d3b`, hardens compliance/evidence ordering so a failed prerequisite cannot continue supplying evidence that lets a dependent step pass. This is relevant as a governance pattern for any future tool-enabled research or maintenance agent around TukeVision/TES.

## TukeVision mapping

**Classification:** `ADAPTAR | BENCHMARK` (pattern-only).

Affected problem/capability:

1. TES/radar automation and future tool-enabled maintenance: untrusted repository paths, filenames and tool output must not be rendered into approval/denial evidence without normalization/sanitization.
2. Evidence First governance: a failed prerequisite/gate must not remain admissible evidence for a downstream PASS.
3. NCSC-style agentic security controls: deny-by-default and human-readable audit output are insufficient if rendered identifiers can contain deceptive invisible Unicode.

No ECC runtime, dependency, hook, skill or code is adopted into TukeVision.

## Adoption boundary

- Pattern-only research source.
- No dependency/runtime/config/product change.
- No direct code copy required.
- Does not affect DVR/NVR primary recording, LOCAL_FIRST, no-biometrics, provider neutrality, or `AI result = lead, no fact`.

## Minimum benchmark

Before implementing an equivalent control in a TukeVision agent/tooling boundary, use a synthetic corpus containing normal paths plus bidi controls, zero-width characters, variation selectors, tag characters, C0/C1 controls and U+2028/U+2029. Required result: denial/audit output remains visually unambiguous and preserves legitimate visible path text. For gate dependency semantics, construct A→B→C where A fails and assert B/C cannot inherit A evidence into PASS.

## Risk

`MEDIUM` for future autonomous/tool-enabled maintenance; `LOW` for current CCTV runtime because this source is not part of runtime.

## Revisit condition / next gate

Revisit when TukeVision introduces or expands autonomous repository/file tooling, approval gates, generated evidence chains, or any agent workflow that renders untrusted identifiers to a human reviewer. Next gate: add a local synthetic security benchmark before any implementation decision.
