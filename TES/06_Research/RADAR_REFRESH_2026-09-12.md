# Radar Refresh — 2026-09-12

## Material change: Frigate 0.18.0 stable

**Classification:** `BENCHMARK / ADAPTAR`  
**Recommended TES state:** `ACTIVE_ENGINEERING_CANDIDATE`  
**Priority:** `P0-HIGH`

### Source verification

- `SOURCE_VERIFIED=YES`
- Canonical upstream: `https://github.com/blakeblackshear/frigate`
- `VERSION_OR_REF_VERIFIED=YES`
- Release: `v0.18.0`
- Published: `2026-09-12T13:17:35Z`
- Release target commit: `77a66e75c61862b048a07c1295877f4b31343504`
- `LICENSE_VERIFIED=YES`
- License: MIT

### Material changes relevant to TukeVision

Frigate 0.18.0 is the first stable 0.18 release and materially changes the value of Frigate as an engineering reference for current TukeVision gaps:

1. **Dynamic configuration**: many camera, ONVIF, enrichment and go2rtc settings can be applied without restart.
2. **Profiles**: named camera configuration overrides can be switched dynamically and persist across restarts.
3. **Generic process watchdog**: crashed or stalled subprocesses can be restarted automatically.
4. **Camera/role health signaling**: explicit camera-role status topics improve health observability.
5. **ONVIF lifecycle**: ONVIF support is refactored around profile selection and dynamic configuration.
6. **Debug Replay**: recorded footage can be replayed through detection/motion pipelines for reproducible tuning and regression analysis.
7. **Motion Search / Motion Review**: targeted spatial search and review workflows reduce brute-force historical analysis.
8. **Case Management / exports**: investigation artifacts can be grouped into named cases.
9. **Full UI configuration**: validated global/camera-level configuration and restart-impact visibility provide a mature operator pattern.

### TukeVision mapping

- **Gate 0C / recovery design:** process watchdog, explicit camera-role health, planned state transitions, profile switching.
- **Gate 1:** dynamic ONVIF/camera configuration and capability-driven onboarding.
- **Investigation / evidence:** Debug Replay, Motion Search, case organization as benchmark patterns only.
- **Operator UX:** configuration validation, global-vs-camera overrides, restart-impact feedback.

### Adoption boundary

- `DIRECT_PRODUCT_INTEGRATION=NO`
- `SECOND_NVR=NO`
- `DIRECT_CODE_COPY=NO`
- DVR/NVR remains the primary recorder.
- TukeVision remains local-first and vendor-neutral.
- Frigate deletion/retention behavior is not adopted automatically; TukeVision evidence-retention policy remains authoritative.

### Benchmark minimum

Before any new Gate 0C lifecycle implementation, compare the stable TukeVision baseline against Frigate 0.18 patterns for:

1. planned profile/config transition without false degraded state;
2. process/watchdog recovery after real decoder failure;
3. per-camera health state during reconnect;
4. avoidance of duplicate decoder ownership;
5. UI responsiveness during grid/focus transitions.

No Frigate installation is required unless a disposable benchmark environment is explicitly authorized.

### Revisit condition

Revisit when:

- Gate 0C is redesigned from the stable baseline;
- Gate 1 camera/ONVIF onboarding is authorized;
- Frigate publishes a later stable release that materially changes lifecycle, health, ONVIF, replay or investigation behavior.

## Other active upstreams reviewed

- **ClearCam:** no new release newer than the already tracked 0.2.8 was verified in this refresh; decision unchanged.
- **Shinobi / GitLab:** no material change verified beyond the live-grid/substream/navigation/auth work already recorded.
- **ONVIF:** no material change verified after TLS Configuration Add-on 2.0 RC already recorded.
- **NCSC / Alocity / Avigilon / March Networks / Ambient.ai / HiFocus / SmartPSS Lite:** no new primary-source change found in this refresh that changes an existing TES decision.

## Decision

`FRIGATE-OSS` is no longer adequately represented by `ACTIVE_EVALUATION` alone. For current lifecycle/recovery/onboarding gaps, the correct operational state is:

```text
STATUS=ACTIVE_ENGINEERING_CANDIDATE
PRIORITY=P0-HIGH
ADOPTION_MODE=BENCHMARK + PATTERN_ADAPTATION
DIRECT_PRODUCT_ADOPTION=NO
DIRECT_CODE_COPY=NO
```

This documentation update does not authorize runtime changes, dependency changes, tests, configuration changes or Gate progression.
