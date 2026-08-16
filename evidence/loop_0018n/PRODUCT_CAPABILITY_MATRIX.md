# LOOP-0018N — PRODUCT_CAPABILITY_MATRIX (PASO 3)

Columnas: CAPABILITY | CURRENT_BASE_STATUS | PORTABLE_STATUS | OBSIDIAN_DESIGN_STATUS |
EXTERNAL_REFERENCE | GAP | REUSE_OPTION | IMPLEMENTATION_REQUIRED | PRIORITY | DEPENDENCY |
ESTIMATED_COMPLEXITY | NEXT_ACTION.

Estados: BASE/portable → EXISTE_CERTIFICADO | EXISTE_VALIDADO | EXPERIMENTAL | DISEÑADO | NO_EXISTE.

| CAPABILITY | BASE | PORTABLE | OBSIDIAN | EXT_REF | GAP | REUSE_OPTION | IMPL_REQUIRED | PRIO | DEP | COMPLEXITY | NEXT_ACTION |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RTSP lifecycle (open/read/stall/reconnect) | EXISTE_CERTIFICADO (E01_COMPAT `ccacb3d`) | EXPERIMENTAL_CERTIFICADO | Diseñado DEC-0032 | OpenCV | Ninguno | REUSABLE_AS_IS | NO | — | — | — | Cerrado |
| camera health (last_frame_age, stall_count, state) | PARCIAL (RTSPSource expone state/last_valid_frame_age_ms/stall_count) | PARCIAL | Diseñado (LOOP-0018) | — | Falta agregación por cámara en capa multicámara | ADAPT (envolver en PerCameraHealth) | SÍ (pequeño) | 1 | SourceManager | LOW | En SourceManager |
| channel/subtype selector | EXISTE (rtsp_url.py channel 1-16 + subtype) | EXISTE | C-01/C-02 certificados | DVR real | Falta mapeo config→cámara | REUSABLE_AS_IS | NO | — | SourceManager | — | Reutilizar en SourceManager |
| multicamera orchestration | NO_EXISTE | NO_EXISTE (E-04 grid UI vacío) | Arquitectura Multi-Tienda (diseño parcial) | NVIDIA DeepStream (referencia) | NÚCLEO | CUSTOM (SourceManager pequeño) | SÍ | 1 | — | MEDIUM | ESTE LOOP |
| SourceManager | NO_EXISTE | NO_EXISTE | NO | — | NÚCLEO | CUSTOM (contrato mínimo §PASO6) | SÍ | 1 | — | MEDIUM | ESTE LOOP |
| 4x4 grid real (16 feeds) | NO_EXISTE | UI E-04 (grid_safe_limit) | NO | DVR 16ch | UI sin datos | REUSE E-04 (post SourceManager) | NO ahora | 2 | SourceManager+E04 | MEDIUM | Post 4-cam |
| per-camera pipeline | NO_EXISTE | pipeline unicámara (E01) | Diseñado | — | Falta 1 pipeline/cámara | ADAPT (Pipeline por cámara) | SÍ | 1 | SourceManager | MEDIUM | ESTE LOOP (mínimo) |
| YOLO detección | EXISTE_CERTIFICADO (YOLO11n) | EXISTE | DEC-0023 | Ultralytics | — | REUSABLE_AS_IS | NO | — | — | — | Reutilizar |
| ByteTrack tracking | EXISTE_CERTIFICADO (trackers 2.5.0) | EXISTE | DEC-0023 | ByteTrack | — | REUSABLE_AS_IS | NO | — | — | — | Reutilizar |
| trajectory | NO_EXISTE | EXPERIMENTAL (E-02) | NO | people flow refs | Integración multicámara + tests | REUSE E-02 (ADAPT) | NO ahora | 3 | multicámara | LOW | Post 4-cam |
| flow IN/OUT/INSIDE | NO_EXISTE | EXPERIMENTAL (E-02 FlowCounter) | NO | people flow | Tests | REUSE E-02 | NO ahora | 3 | trajectory | LOW | Post 4-cam |
| zones | EXISTE_CERTIFICADO (polygon) | EXISTE | DEC-0014 | OpenCV | Multi-zona/cámara | REUSABLE_AS_IS | ADAPT | 3 | per-camera | LOW | Post 4-cam |
| dwell | EXISTE (stay_seconds) | EXISTE | DEC (permanencia) | — | — | REUSABLE_AS_IS | NO | — | — | — | — |
| events | EXISTE_CERTIFICADO | EXISTE | DEC-0002/0006 | NVIDIA model | — | REUSABLE_AS_IS | NO | — | — | — | — |
| risk | EXISTE_CERTIFICADO | EXISTE | DEC-0009 | — | — | REUSABLE_AS_IS | NO | — | — | — | — |
| evidence | EXISTE_CERTIFICADO (immutable) | EXISTE | DEC-0007 | — | — | REUSABLE_AS_IS | NO | — | — | — | — |
| activity recognition | NO_EXISTE | NO_EXISTE | NO | CNN/activity refs | NUEVA (Activity Layer spec) | CUSTOM diseñado | NO ahora | 4 | trajectory | HIGH | Diseñado (spec) |
| interaction recognition | NO_EXISTE | NO_EXISTE | NO | Pyresearch refs | NUEVA | CUSTOM diseñado | NO ahora | 5 | activity | HIGH | Diseñado (spec) |
| heatmaps | NO_EXISTE | NO_EXISTE | NO | people flow refs | NUEVA | CUSTOM | NO ahora | 6 | trajectory | MEDIUM | Diseñado |
| segmentation selectiva | NO_EXISTE | NO_EXISTE | NO | OpenCV | NUEVA | CUSTOM | NO ahora | 7 | — | HIGH | Pendiente gap |
| ReID/context identity | NO_EXISTE | EXPERIMENTAL (E-03) | DEC-0013 CONFLICTO | Face SDK / CactusCompute refs | BLOQUEADO gobernanza | REUSE E-03 condicionado | NO ahora | 8 | DEC-0013 | HIGH | Decisión humana |
| person vs mannequin | NO_EXISTE | NO_EXISTE | NO | Pyresearch | NUEVA | CUSTOM | NO ahora | 7 | activity | MEDIUM | Pendiente gap |
| snapshot (per-camera) | PARCIAL (FrameSnapshot unicámara) | PARCIAL | NO | — | Necesita por cámara | ADAPT | SÍ | 1 | SourceManager | LOW | ESTE LOOP |
| recording/clip | PARCIAL (VideoWriter single) | PARCIAL | DEC-0007 | — | Por cámara | ADAPT | NO ahora | 3 | per-camera | MEDIUM | Post 4-cam |
| playback | NO_EXISTE | NO_EXISTE | NO | — | NUEVA | CUSTOM | NO ahora | 6 | evidence | MEDIUM | Pendiente |
| OSD layers | PARCIAL (annotate) | PARCIAL | NO | — | Por cámara | ADAPT | NO ahora | 3 | per-camera | LOW | Post 4-cam |
| telemetry | PARCIAL (logs/monitor) | PARCIAL | LOOP-0018L monitor | — | Agregación | ADAPT | NO ahora | 3 | SourceManager | LOW | Post 4-cam |
| alerting | EXISTE_CERTIFICADO | EXISTE | DEC-0010 | n8n (futuro) | — | REUSABLE_AS_IS | NO | — | — | — | — |
| search/replay | NO_EXISTE | NO_EXISTE | NO | — | NUEVA | CUSTOM | NO ahora | 6 | evidence | HIGH | Pendiente |
| web/API presentation | NO_EXISTE | NO_EXISTE | NO (Next.js REJECTED) | — | NUEVA | CUSTOM | NO ahora | 7 | — | HIGH | Sin gap demostrado |
| configuration/persistence | EXISTE (config/default.json) | EXISTE | DEC | JSON local | Multi-cámara en config | ADAPT | NO ahora | 2 | SourceManager | LOW | Config cámaras |
| secret management | EXISTE_CERTIFICADO (redact/build_rtsp_url) | EXISTE | AC-SEC tests | — | — | REUSABLE_AS_IS | NO | — | — | — | Reutilizar |
| ONVIF/discovery | NO_EXISTE | NO_EXISTE | NO | — | NUEVA | CUSTOM/EXT | NO ahora | 7 | — | HIGH | Sin gap autorizado |
| PTZ | NO_EXISTE | NO_EXISTE | NO | — | NUEVA | CUSTOM | NO ahora | 7 | — | HIGH | Sin gap autorizado |
| AI second opinion | NO_EXISTE | NO_EXISTE | Diseñado (ARCH #14 IA posterior) | Qwen MM (rejected) | NUEVA (Policy) | CUSTOM diseñado | NO ahora | 5 | event+evidence | MEDIUM | Diseñado (spec) |
| reasoning over candidate events | NO_EXISTE | NO_EXISTE | Diseñado (DEC-0011 humano) | — | NUEVA | CUSTOM diseñado | NO ahora | 5 | AI second opinion | MEDIUM | Diseñado (spec) |

## Prioridad resumida

- **PRIO 1 (ESTE LOOP):** SourceManager, multicamera orchestration (4), per-camera pipeline mínimo, snapshot por cámara, camera health agregada.
- **PRIO 2:** config multi-cámara, grid UI (E-04).
- **PRIO 3:** trajectory/flow (E-02), recording, OSD, telemetry, zones multi-cámara.
- **PRIO 4-5:** Activity Layer, interaction, AI second opinion (specs).
- **PRIO 6-7:** heatmaps, playback, search, segmentation, web/API, ONVIF/PTZ.
- **PRIO 8:** ReID (bloqueado por DEC-0013).

## GAP que este LOOP cierra
`multicamera orchestration` + `SourceManager` + `per-camera pipeline` + `per-camera health/snapshot`.
Todo lo demás queda como roadmap sin implementación.