# RADAR RECONCILIATION
**MISSION:** TV-KNOWLEDGE-RADAR-RECONCILIATION-02
**DATE:** 2026-09-08
**MODE:** ACTIVE_EVALUATION

## 1. OBJETIVO

Evitar que una experiencia útil permanezca dormida en TES. Toda fuente con relación directa a una brecha actual debe pasar a evaluación activa, benchmark o decisión explícita.

Regla:

```text
DISCOVERY
→ VERIFY
→ MAP_TO_TUKEVISION
→ ACTIVE_EVALUATION
→ BENCHMARK
→ DECISION
```

No se crean módulos automáticamente. Se activa la evaluación, no la adopción ciega.

## 2. ACTIVE / ADOPTED BASELINE

- OpenVINO Edge Runtime
- PyAV / FFmpeg
- ByteTrack
- Tkinter + DesignTokens
- SQLite Structured Indexing

Estos componentes se consultan como baseline antes de recomendar reemplazos.

## 3. EXPERIENCIAS ACTIVADAS DESDE TES

### P0-ACTIVE

- **ClearCam** — `ACTIVE_ENGINEERING_CANDIDATE / HIGH`
  - RTSP recovery ya adaptado parcialmente.
  - Activar benchmark de playback/freshness, selective inference, stationary/recovery tracking, event/similar-image search.
  - GPL-3.0: no copiar código al core.

- **Frigate** — `ACTIVE_BENCHMARK_REFERENCE`
  - auditar ingestion, ffmpeg/go2rtc lifecycle, recovery, hardware acceleration, events, search, storage y health.
  - límite: no segundo NVR.

- **ONVIF Media Signing** — `ACTIVE_SANDBOX_BENCHMARK / CONTRACT_READY`
  - benchmark sign→verify→tamper→verify_fail.
  - hardware físico pendiente cuando corresponda.

- **NCSC Agentic Security** — `ACTIVE_GOVERNANCE`
  - minimum privilege, deny-by-default, isolation, audit, human control, safe mode.

- **Alocity/Mercury open access pattern** — `ACTIVE_CONTRACT_PATTERN`
  - ACCESS pasa a fuente operacional normalizada.
  - no crear módulo Mercury/Alocity.
  - `CREDENTIAL_EVENT != PERSON_IDENTITY`.

- **Purpose-Bound / Flock investigation governance** — `ACTIVE_GOVERNANCE`
  - purpose, case, permission, camera/time scope, audit.
  - AI result = candidate lead.

### P1-ACTIVE

- **HiFocus IntelliSeek** — historical on-demand analysis, no full-frame indexing.
- **Ambient.ai** — attention reduction and operator prioritization.
- **Avigilon** — enterprise search, multisite, privacy, video+access patterns.
- **March Networks** — connected intelligence across video/data/access/multisite.
- **SmartPSS Lite** — operator workflow / VMS UX benchmark.
- **Agentic Video Understanding** — local pattern benchmark for goal-directed temporal search and dynamic resampling.

### CONDITIONAL

- OC-SORT — activate on proven ID-switch/occlusion/recovery defect.
- CoTracker / TAPNet / Trace Anything — activate only if bbox tracking is insufficient.
- SmolVLM / FastVLM / Qwen3-VL — activate when structured investigation cannot satisfy a real need.
- ONNX Runtime — activate for hardware/platform not served by OpenVINO.
- screen2ipcam — activate on POS/legacy-screen source requirement.

### RESERVE

- Radar mmWave
- Thermal
- Audio analytics

## 4. RECONCILIACIÓN DE FUENTES YA CONOCIDAS

- **God's Eye View**: `ADAPTED / WATCH`; consultar para spatial state, viewshed, handoff, freshness/provenance.
- **Ambient.ai**: `ADAPTED_PATTERN / P1-ACTIVE`.
- **HiFocus IntelliSeek**: `ADAPTED_PARTIAL / P1-ACTIVE`.
- **ONVIF Media Signing**: `CONTRACT_READY / P0-ACTIVE`.
- **Detectron2**: `REJECTED_FOR_CURRENT_EDGE_PROFILE / WATCH`; reabrir sólo si cambia hardware o aparece brecha de segmentación.
- **RapidVMS**: `BENCHMARK_REFERENCE_ONLY`; integración directa rechazada por second-NVR conflict.
- **MAGI**: `DISCOVERY_LAYER`; nunca autoridad directa.
- **Profile M / Profile V**: `WATCH_READINESS`.

## 5. CONSULTA OBLIGATORIA ANTE PROBLEMAS

Desde esta reconciliación:

```text
PROBLEM
→ TES/KNOWLEDGE_SOURCE_INDEX.md
→ TES/EXPERIENCE_STORE.md
→ TES/DECISION_LOG.md
→ TES/TECHNOLOGY_RADAR.md
→ EXISTING CAPABILITY
→ DECIDE
```

Una nueva solución debe declarar:

`TES_MATCHES=<fuentes/experiencias consultadas>`

o

`TES_MATCHES=NO_RELEVANT_EXPERIENCE_FOUND`.

## 6. REGLA DE FRESCURA

Para fuentes GitHub activas, cada revisión relacionada debe comprobar upstream original y sólo actualizar TES si existe cambio material.

Mínimo:

- README/documentación vigente;
- actividad/release relevante;
- licencia;
- cambios de arquitectura/capacidad;
- condición de reevaluación;
- impacto frente al baseline TukeVision.

## 7. CAMBIOS MATERIALES 2026-09-08

- ClearCam deja de ser sólo experiencia RTSP almacenada y pasa a `ACTIVE_ENGINEERING_CANDIDATE`.
- Frigate pasa a `ACTIVE_BENCHMARK_REFERENCE`.
- ONVIF Media Signing pasa a benchmark activo sin sobredeclarar hardware.
- ACCESS se incorpora al readiness multimodal por contrato neutral de proveedor.
- Purpose-bound investigation pasa a gobernanza obligatoria para búsqueda IA.
- Todas las experiencias `EVALUATE/WATCH/TARGET` reciben condición explícita de activación o permanecen `RESERVE`.

## 8. DOCUMENTOS CANÓNICOS RECONCILIADOS

- `TES/ACTIVE_EVALUATION_PROTOCOL.md`
- `TES/KNOWLEDGE_SOURCE_INDEX.md`
- `TES/EXPERIENCE_STORE.md`
- `TES/TECHNOLOGY_RADAR.md`
- `TES/DECISION_LOG.md`

## 9. DECISIÓN

`TES = ACTIVE_ENGINEERING_MEMORY`, no archivo pasivo.

Objetivo:

`LEARN → ADAPT → VERIFY`

antes de:

`INVENT → FAIL → PATCH`.
