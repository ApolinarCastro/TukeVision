# FRIGATE-OSS — lifecycle / tracking / observability delta — 2026-09-20

SOURCE_VERIFIED=YES  
CANONICAL_UPSTREAM=`https://github.com/blakeblackshear/frigate`  
VERSION_OR_REF_VERIFIED=YES — `52f50a7396ebdef7a22aa9682b275ca4828f6399` (2026-09-20)  
LICENSE_VERIFIED=YES — MIT for repository code/config/docs; trademark assets excluded  
CAPABILITIES_EXTRACTED=YES — dynamic-camera lifecycle race handling; watchdog coverage; isolated tracked-object expiry; motion-background recovery; FFmpeg restart diagnostics  
TUKEVISION_MAPPING=YES — Gate 0C lifecycle/freshness, tracking continuity, recovery, observability  
ADOPTION_BOUNDARY=YES — pattern/benchmark only; no second NVR; no direct architecture transplant  
REVISIT_CONDITION=YES — activate when TukeVision shows matching lifecycle race, collateral track loss, non-recovering motion/background state or insufficient FFmpeg restart evidence  
EXPERIENCE_RECORD=`EXP-FRIGATE-2026-09-20-LIFECYCLE-TRACKING`  
CLASSIFICATION=`ADAPTAR | BENCHMARK`

## Experience record

### EXP-FRIGATE-2026-09-20-LIFECYCLE-TRACKING

- PROBLEM: source/worker races, collateral tracker-state deletion, recovery after large scene transitions, and insufficient restart diagnostics can create silent or hard-to-reproduce CCTV failures.
- PATTERN: prerequisite-state gating + watchdog-supervised workers + target-only state removal + background-model convergence during suppression + one bounded diagnostic dump per restart.
- DECISION: ADAPTAR / BENCHMARK; no runtime adoption in this radar run.
- BOUNDARY: Frigate remains reference only; TukeVision does not adopt continuous recording/storage or become a second NVR.
- RISK: topology/implementation differences mean upstream fixes are not evidence of identical TukeVision bugs.
- MINIMUM_BENCHMARK: induced add/remove race, stationary-object expiry with peers, scene transition, and FFmpeg restart; measure recovery, track continuity, stale duration, CPU/RAM and diagnostic provenance.
- NEXT_GATE: reproduce matching FAIL in TukeVision before adapting any pattern.
