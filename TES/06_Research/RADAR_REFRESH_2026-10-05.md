# RADAR REFRESH — 2026-10-05

**TASK:** TUKEVISION-RADAR-REFRESH-2026-10-05  
**STATUS:** PASS_PENDING_MERGE  
**BASE_HEAD:** cc5a823a7c17de1958ace11db36cfa02a3a6760e  
**MATERIAL_CHANGE:** YES

## Confirmed material findings

1. **ONVIF Media Signing r26.6.2**
   - Commit: `807ea4bf16d13ff9d4fd2913fc09e3a7476cb305`
   - Fixes unsafe handling of `UNDEFINED_TAG` in tampered SEI that could continue into an absent decoder and crash.
   - TukeVision impact: add fail-closed adversarial parsing benchmark with `PROCESS_CRASH=0`.
   - Decision remains `ACTIVE_EVALUATION / CONTRACT_READY`.

2. **CamSniff 2.3.0**
   - Upstream: `John0n1/CamSniff`, MIT.
   - Useful patterns: explicit target containment, bounded RTSP/ONVIF probing, evidence + negative-evidence scoring, schema-versioned inventory.
   - TukeVision impact: Gate 1 discovery/onboarding benchmark.
   - Boundary: no credential guessing, high-rate scanning, Masscan defaults, aggressive modes or sensitive capture in normal product behavior.
   - Decision: `BENCHMARK + ADAPT_PATTERN`.

3. **Edge Impulse inferencing family**
   - Primary ref: `inferencing-sdk-cpp` v1.95.14, commit `4505ca2f427556557164c3dfeb6b63b7e1f88c8f`.
   - Useful only for future edge portability/model packaging gaps.
   - Decision: `WATCH / CONDITIONAL_BENCHMARK`; OpenVINO baseline unchanged.

## Verified no architecture change

- Frigate latest stable observed remains 0.18.0; no new stable release requiring decision change.
- Jev / TypeSafe Python SDK is now v0.7.2 with optional HTTP/2 support; role remains WATCH/EXPERIMENTAL.
- Qwen-MM-Plugins remains active upstream; no current finding forces a TukeVision architecture change.
- ONVIF TLS Configuration 2.0 remains RC; no production conformance claim.

## Files changed

- `TES/TECHNOLOGY_RADAR.md`
- `TES/KNOWLEDGE_SOURCE_INDEX.md`
- `TES/EXPERIENCE_STORE.md`
- `TES/06_Research/RADAR_REFRESH_2026-10-05.md`

No runtime, tests, dependencies, product configuration or DECISION_LOG changed.
