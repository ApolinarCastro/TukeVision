# Radar Refresh — 2026-09-16 — Frigate upstream material change

## Scope
Documentation-only TES evidence record. No runtime, code, tests, dependencies, or configuration changes.

## Source
- SOURCE: Frigate
- UPSTREAM_CANONICAL: `blakeblackshear/frigate`
- FORGE: GitHub
- LICENSE: MIT (existing verified TES boundary; no code reuse authorized by this record)
- VERIFIED_AT: 2026-09-16
- VERSION_BASELINE: `v0.18.0` stable (2026-09-12)
- MATERIAL_REF_1: `41003837383b11f568eebb8a6d33c6398724180c` — 2026-09-15
- MATERIAL_REF_2: `64d6366ac4be29cf9044a2a0e11ba29464ad9765` — 2026-09-16

## Verification completeness
- SOURCE_VERIFIED=YES
- VERSION_OR_REF_VERIFIED=YES
- LICENSE_VERIFIED=YES
- CAPABILITIES_EXTRACTED=YES
- TUKEVISION_MAPPING=YES
- ADOPTION_BOUNDARY=YES
- REVISIT_CONDITION=YES
- EXPERIENCE_RECORD=YES (this record; canonical EXPERIENCE_STORE reconciliation pending safe full-file write)

## Material changes

### 1. Async ONVIF isolation + authorization/source-identity fixes
Commit `4100383` fixes several patterns material to TukeVision:
- an ONVIF PTZ information request previously blocked the async API event loop while waiting on a slow/unreachable camera; it now awaits the controller future asynchronously;
- JWT refresh now rejects roles removed from configuration instead of preserving stale authorization;
- cached preview matching now uses exact camera identity instead of prefix matching, preventing cross-camera frame mixups and potential unauthorized frame exposure;
- case/export authorization is tightened for attaching exports to existing cases.

### 2. Explicit live-stream technology selection and WebRTC readiness
Commit `64d6366` adds explicit live streaming technology selection, prevents persisted WebRTC preference from being incorrectly downgraded during asynchronous capability probing, handles blocked persistence without indefinite waiting, and adds configurable ICE servers.

## TukeVision mapping
- Gate 0C / presentation freshness and source identity: exact camera identity is mandatory; no prefix/ambiguous cache lookup may substitute another source frame.
- Gate 1 / ONVIF onboarding and device control: slow/unreachable ONVIF operations must be isolated and must not block unrelated camera/control paths.
- P0-70 / authorization: authorization must be revalidated against current policy; stale role/session state cannot retain access after policy removal.
- Evidence First / investigations: attaching/exporting evidence must preserve authorization and exact source linkage.
- WebRTC remains WATCH/AUXILIARY: the new Frigate pattern is relevant only if TukeVision later requires browser/remote live viewing; it does not justify a UI migration now.

## Classification
- Frigate overall: `ACTIVE_ENGINEERING_CANDIDATE / P0-HIGH` remains.
- `4100383`: `ADAPTAR + BENCHMARK`.
- `64d6366`: `WATCH + BENCHMARK_WHEN_WEBRTC_GATE_OPENS`.
- Product adoption: NO.
- Second NVR: NO.
- Direct code copy: NO without explicit license/design review.

## Problem solved / risk
Current TukeVision risks addressed by these patterns are false source association, cross-camera evidence contamination, control-plane stalls caused by one device, stale authorization, and future WebRTC state/fallback ambiguity. These are correctness/security patterns, not a reason to import Frigate.

## Minimum decisive benchmark
1. Simulate one slow/unreachable ONVIF device while other camera/control operations continue; unrelated paths must remain responsive.
2. Verify exact source identity for cached/latest frames with deliberately similar camera names; cross-camera substitution must be zero.
3. Remove/change an operator role during an active session and verify subsequent privileged evidence/control access is denied according to current policy.
4. Only when WebRTC becomes an active TukeVision requirement: persist transport choice, reload during capability probing, test ICE configuration/failure, and verify deterministic fallback without false LIVE.

## Next gate
`GATE0C_SOURCE_IDENTITY + GATE1_ONVIF_ISOLATION + AUTH_POLICY_REVALIDATION`. WebRTC remains conditional.

## Canonical reconciliation required
The following canonical files should be reconciled on this documentation branch when a safe non-truncating full-file write is available:
- `TES/TECHNOLOGY_RADAR.md`: append this Frigate material delta; keep candidate priority unchanged.
- `TES/KNOWLEDGE_SOURCE_INDEX.md`: update Frigate `LAST_VERIFIED_REF` to include `4100383` / `64d6366` with distinct capability mapping.
- `TES/EXPERIENCE_STORE.md`: add an immutable Frigate experience record for ONVIF isolation, exact camera identity, policy revalidation and conditional WebRTC transport state.
- `TES/DECISION_LOG.md`: NO CHANGE; no adoption/architecture decision changed.

This record does not claim canonical reconciliation has already occurred.