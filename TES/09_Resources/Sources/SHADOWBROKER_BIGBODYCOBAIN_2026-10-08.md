# ShadowBroker — source record for TukeVision

**VERIFIED_AT:** 2026-10-08  
**UPSTREAM:** BigBodyCobain/Shadowbroker  
**VERIFIED_REF:** 84ab6cba53e9d35952bf6fb2c5633b252235a859  
**LICENSE:** AGPL-3.0  
**PRODUCT_CHANGE:** NONE

## Verified relevant patterns

1. **CCTV media proxy hardening**
   - allowed-host validation;
   - HTTP/HTTPS scheme restriction;
   - redirect following performed manually;
   - every redirect hop revalidates the destination host;
   - bounded redirect count;
   - per-source timeout/cache/header profiles.

2. **Agent cost/blast-radius gating**
   - thin agent surface;
   - deterministic routing to targeted commands;
   - expensive full telemetry/search/report commands require explicit confirmation;
   - latency tiers and anti-patterns are machine-readable.

3. **Compact telemetry access**
   - targeted entity/layer reads and change-oriented queries are preferred to full dumps;
   - batching/playbooks reduce sequential command loops.

4. **Heavy work isolation**
   - network-heavy or large data refreshes are dispatched away from the single request worker so operator UI/data bootstrap does not stall.

5. **Outbound-data governance**
   - explicit documentation of browser vs backend third-party calls;
   - opt-in controls, operator-identifiable egress, accepted privacy tradeoffs, and self-hosting alternatives.

## TukeVision decision

```text
CLASSIFICATION = BENCHMARK / ADAPT_PATTERN
CORE_DEPENDENCY = NO
INSTALL_NOW = NO
COPY_AGPL_CODE = NO
GATE0C_IMPACT = NONE
```

## Why not direct adoption

ShadowBroker is a broad OSINT/geospatial platform with public CCTV harvesting, recon, mesh communications and many external feeds. That scope is materially different from TukeVision's local CCTV/runtime/evidence problem. Its Docker defaults also allocate up to 4 GiB to the backend plus 512 MiB to the frontend.

Direct code reuse carries AGPL-3.0 obligations. TukeVision should extract design lessons and implement equivalent narrow patterns independently only when a proven product gap exists.

## Candidate future gates

- `TV-AGENT-SURFACE-001`: targeted/confirmed capability routing.
- `TV-STATE-DELTA-001`: what-changed / compact state query versus full snapshot reads.
- `TV-MEDIA-PROXY-SSRF-001`: redirect-safe proxy benchmark if remote web playback is introduced.
- `TV-OUTBOUND-REGISTRY-001`: auditable third-party egress registry before external connectors are promoted.
