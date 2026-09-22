# Qwen Live Harness — TES Source Record

- `SOURCE_ID`: `QWEN-LIVE-HARNESS`
- `CANONICAL_UPSTREAM`: `https://github.com/QwenLM/Qwen-Live-Harness`
- `FORGE`: GitHub
- `VERSION_OR_REF`: v1.0.0, released 2026-09-21
- `LAST_VERIFIED_AT`: 2026-09-21
- `LICENSE`: Apache-2.0
- `MATURITY`: new public v1.0.0 / active upstream
- `CAPABILITIES`: realtime audio/video interaction; camera/screen context; on-demand visual analysis; live feed; proactive audio/visual/time conditions; background harness delegation; long-term memory.
- `TUKEVISION_MAPPING`: P0-65 semantic investigation; P0-66 attention orchestration; capture/presentation/coordinator separation.
- `CLASSIFICATION`: `WATCH | ADAPTAR (PATTERN-ONLY) | REJECT_CURRENT_CLOUD_PATH`
- `ADOPTION_BOUNDARY`: no product integration, no CCTV/customer media to DashScope/Qwen Omni Realtime API, no Electron adoption; pattern study only.
- `RISK`: cloud media egress, external API dependency, inference/sampling latency and mistakes, non-safety-critical monitoring semantics.
- `BENCHMARK_MINIMUM`: synthetic/authorized local media only; measure missed events, false escalation, time-to-attention, latency/resources, provenance; any TukeVision implementation requires `MEDIA_EGRESS=0`.
- `REVISIT_CONDITION`: local Omni/VLM backend becomes available and compatible, or measured P0-66 gap justifies a local benchmark.
- `EXPERIENCE_RECORD`: `EXP-QWEN-LIVE-001` (documented in `TES/06_Research/RADAR_REFRESH_2026-09-21_QWEN_LIVE.md`).

## Evidence boundary

The upstream README states that the desktop experience requires an internet connection to Alibaba Cloud Model Studio DashScope API; camera/screen can be used as visual context; live feed defaults to 1 FPS at 720p; proactive monitoring uses 1 FPS/two-second chunks; and sampling/model inference can introduce delay and mistakes, so the monitor is not a safety-critical alarm system.

These properties make the project useful as an architectural/UX reference but incompatible with TukeVision's permanent LOCAL_FIRST/no-customer-CCTV-egress boundary in its current form.
