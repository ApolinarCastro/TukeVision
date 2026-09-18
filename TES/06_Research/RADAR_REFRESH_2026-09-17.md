# Radar/TES refresh — 2026-09-17

## Material change: Frigate dev — atomic zone rename/reference integrity

- SOURCE_ID: `FRIGATE-OSS`
- CANONICAL_UPSTREAM: `https://github.com/blakeblackshear/frigate`
- FORGE: `GITHUB`
- VERIFIED_REF: `10a0d5ea373025b9a53fbc90a1c701d76b160928`
- VERIFIED_REF_DATE: `2026-09-16T18:07:05Z`
- UPSTREAM_RELEASE_BASELINE: `0.18.0` stable, published 2026-09-12
- LICENSE: `MIT` (upstream LICENSE verified 2026-09-17)
- MATURITY: stable 0.18.0 exists; this finding is from post-0.18 `dev`, therefore pattern evidence only and not a stable-release adoption signal.

### Verification completeness

- SOURCE_VERIFIED=YES
- VERSION_OR_REF_VERIFIED=YES
- LICENSE_VERIFIED=YES
- CAPABILITIES_EXTRACTED=YES
- TUKEVISION_MAPPING=YES
- ADOPTION_BOUNDARY=YES
- REVISIT_CONDITION=YES
- EXPERIENCE_RECORD=YES — `EXP-FRIGATE-2026-09-17-ZONE-REF-INTEGRITY`

### What changed

Frigate commit `10a0d5ea...` changes zone rename handling so the rename is persisted as one configuration body and dependent references (`required_zones` and profile overrides) move with the renamed zone instead of leaving stale references.

### TukeVision problem / capability mapping

This is relevant to TukeVision's zone/configuration integrity and Evidence First boundary. A zone identifier used by situations, policies, evidence selection or operator views must not be renamed in one place while dependent references retain the previous identifier.

Affected capability/gate:

- zone/configuration lifecycle;
- situation/evidence reference integrity;
- operator configuration UX;
- documentation/productization gate requiring real, non-fabricated zones.

### TES classification

- PREVIOUS: `FRIGATE-OSS = ACTIVE_ENGINEERING_CANDIDATE / P0-HIGH; BENCHMARK + ADAPT PATTERNS`
- RECOMMENDED: **unchanged overall**, with new sub-classification `ADAPTAR / BENCHMARK — ATOMIC_REFERENCE_UPDATE_PATTERN`.
- ACTIVE_ENGINEERING_CANDIDATE: **YES, remains**. This commit strengthens an already active candidate but does not justify adopting Frigate as a product.

### Adoption boundary

- Do not integrate Frigate as NVR.
- Do not copy external code without explicit license review despite MIT permissiveness.
- Adapt the invariant/pattern only.
- DVR/NVR remains primary recorder.
- Local-first and Evidence First remain mandatory.

### Risk

`ZONE_RENAME -> STALE_DEPENDENT_REFERENCE` can silently mis-scope rules, situations or evidence. The risk is referential inconsistency rather than video transport failure.

### Minimum decisive benchmark

On a disposable TukeVision configuration containing one zone referenced by at least two dependent objects:

1. rename the zone once;
2. verify the zone definition and every dependent reference change atomically or transactionally;
3. verify zero references to the old zone ID/name remain;
4. force a failed write and verify rollback/no half-renamed state;
5. verify existing evidence keeps immutable provenance and is not rewritten as if the historical zone name had always been the new one.

PASS only if `STALE_ZONE_REFERENCES=0`, partial updates are impossible/recoverable, and historical evidence is preserved.

### Next gate

`ZONE_REFERENCE_INTEGRITY_BENCHMARK` before any future zone rename/configuration workflow is considered production-safe.

### Canonical TES reconciliation required

The following canonical files should incorporate this experience when a safe non-destructive full-file update is available:

- `TES/TECHNOLOGY_RADAR.md` — add Frigate atomic zone/reference update pattern under active benchmark/adaptation targets.
- `TES/KNOWLEDGE_SOURCE_INDEX.md` — advance `FRIGATE-OSS` verified ref and add revisit condition for zone/configuration lifecycle.
- `TES/EXPERIENCE_STORE.md` — add `EXP-FRIGATE-2026-09-17-ZONE-REF-INTEGRITY`.
- `TES/DECISION_LOG.md` — **NO CHANGE**; no architecture/adoption decision changed.

## Explicit freshness checks in this execution

- Frigate: stable release remains `0.18.0`; upstream `dev` advanced through `10a0d5ea...` and this commit is material as described above.
- ClearCam: latest verified relevant commits remain `84b8740a...` / Qwen-without-provider-identity family already captured by prior TES refresh; no new material delta found in this execution.
- ECC (`affaan-m/ECC`): latest stable release remains `v2.2.1`; no CCTV/TukeVision runtime capability change found that warrants TES promotion in this execution.
- Shinobi canonical GitLab upstream: no newer material upstream signal found than the already tracked live-grid/substream evidence.
- ONVIF primary sources/specs: no newer material publication found that changes the current Media Signing / TLS Configuration / Profile V decisions.

## Forge coverage

GitHub and GitLab were both considered as first-class forges. ONVIF primary sources were also checked. Mirrors/forks were not promoted as canonical evidence.
