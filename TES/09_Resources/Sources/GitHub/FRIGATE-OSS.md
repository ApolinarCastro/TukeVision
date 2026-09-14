# FRIGATE-OSS — Canonical Source Record

**SOURCE_ID:** `FRIGATE-OSS`  
**STATUS:** `ACTIVE_ENGINEERING_CANDIDATE`  
**PRIORITY:** `P0-HIGH`

## Canonical upstream

- Forge: GitHub
- Upstream: `https://github.com/blakeblackshear/frigate`
- Repository: `blakeblackshear/frigate`
- Canonical branch: `dev`
- Project role: OSS NVR/CCTV with local realtime object detection

## Verification

- `SOURCE_VERIFIED=YES`
- `VERSION_OR_REF_VERIFIED=YES`
- Latest stable release verified: `v0.18.0`
- Published: `2026-09-12T13:17:35Z`
- Target commit: `77a66e75c61862b048a07c1295877f4b31343504`
- Repository active/non-archived at verification time.
- `LICENSE_VERIFIED=YES`
- License: MIT

## Capabilities extracted

Relevant capabilities verified from the 0.18.0 release and upstream:

- multicamera ffmpeg/go2rtc lifecycle;
- dynamic camera/go2rtc/ONVIF configuration without unnecessary restart;
- named profiles with runtime camera overrides;
- generic process watchdog for crashed/stalled subprocesses;
- explicit camera-role health/status signaling;
- ONVIF profile selection and dynamic ONVIF updates;
- Debug Replay through motion/detection pipelines;
- motion review/search;
- semantic search / GenAI tooling;
- investigation-oriented case/export organization;
- operator configuration UI with validation and restart-impact visibility;
- hardware acceleration across multiple accelerator families.

`CAPABILITIES_EXTRACTED=YES`

## TukeVision mapping

### Current high-value mapping

- **Gate 0C:** decoder/process lifecycle, planned transitions, recovery, health semantics, watchdog behavior.
- **Gate 1:** camera/ONVIF onboarding, dynamic configuration, explicit capability/state transitions.
- **Investigation/evidence:** Debug Replay, Motion Search and case organization are benchmark patterns for future authorized work.
- **Operator UX:** validated per-camera/global configuration and explicit restart requirements.

`TUKEVISION_MAPPING=YES`

## Adoption boundary

- `DIRECT_PRODUCT_INTEGRATION=NO`
- `DIRECT_CODE_COPY=NO`
- `SECOND_NVR=NO`
- DVR/NVR remains primary recorder.
- TukeVision remains local-first and vendor-neutral.
- Do not import Frigate retention/deletion policy into TukeVision evidence handling.
- Use patterns only after benchmark and license/architecture review.

`ADOPTION_BOUNDARY=YES`

## Revisit condition

Re-evaluate when:

1. Gate 0C is redesigned from the last stable baseline;
2. Gate 1 ONVIF/LAN onboarding is authorized;
3. Frigate publishes a later stable release affecting lifecycle, health, ONVIF, replay, search or operator workflows;
4. TukeVision demonstrates a measurable gap in recovery, health, UI transition or investigation flow that Frigate already addresses.

`REVISIT_CONDITION=YES`

## Experience record

### EXP-FRIGATE-002

**Problem:** TukeVision has spent repeated cycles redesigning camera lifecycle and UI transition behavior while a mature OSS CCTV system exposes explicit patterns for process supervision, camera-role health and dynamic configuration.

**Pattern:**

```text
PLANNED_TRANSITION
-> explicit transitional state
-> preserve process ownership
-> no false failure escalation
-> first valid post-transition state/frame
-> steady health

REAL_FAILURE
-> explicit unhealthy/reconnecting state
-> bounded watchdog recovery
-> new process generation only after prior ownership cleanup
-> health restored only from runtime evidence
```

**Decision:** `BENCHMARK / ADAPTAR`, elevated to `ACTIVE_ENGINEERING_CANDIDATE` for the current Gate 0C/Gate 1 problem set.

**Minimum benchmark:** compare planned transition semantics, real failure recovery, camera-role health, process ownership and grid/focus responsiveness before implementing a new Gate 0C lifecycle design.

**Boundary:** benchmark and independent pattern adaptation only; do not turn TukeVision into Frigate or a second NVR.

`EXPERIENCE_RECORD=YES`

## Incorporation completeness

```text
SOURCE_VERIFIED=YES
VERSION_OR_REF_VERIFIED=YES
LICENSE_VERIFIED=YES
CAPABILITIES_EXTRACTED=YES
TUKEVISION_MAPPING=YES
ADOPTION_BOUNDARY=YES
REVISIT_CONDITION=YES
EXPERIENCE_RECORD=YES
```
