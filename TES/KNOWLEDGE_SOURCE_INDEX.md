# Índice Canónico de Fuentes de Conocimiento — TukeVision TES V3

**STATUS:** ACTIVE
**UPDATED:** 2026-09-08

Este índice convierte las fuentes de experiencia en conocimiento consultable y reevaluable. Una fuente registrada aquí debe tener una decisión, una condición de reevaluación y un mapeo hacia TukeVision.

## Estados

- `ACTIVE_EVALUATION`: evaluación prioritaria contra brechas actuales.
- `ADAPTED`: patrón ya adaptado; seguir upstream para regresiones/mejoras.
- `BENCHMARK`: requiere comparación reproducible.
- `WATCH`: seguir cambios materiales.
- `RESERVE`: no activar hasta que aparezca condición.
- `REJECTED_FOR_CURRENT_PROFILE`: no usar en perfil actual; reabrir sólo si cambia la condición.
- `DISCOVERY_LAYER`: sirve para descubrir; no es autoridad técnica.

## Fuentes activas y dormidas reconciliadas

| SOURCE_ID | Fuente / upstream | Tipo | Estado TES | Mapeo principal | Condición / siguiente acción |
|---|---|---|---|---|---|
| CLEARCAM-RORYCLEAR | `https://github.com/roryclear/clearcam` | OSS CCTV / ingeniería | **ACTIVE_EVALUATION / ADAPTED_PARTIAL** | RTSP, FFmpeg lifecycle, tracking, selective inference, event/semantic search | Benchmark inmediato de resiliencia, tracking y búsqueda; GPL-3.0, no copiar código al core |
| FRIGATE-OSS | `https://github.com/blakeblackshear/frigate` | OSS NVR/CCTV | **ACTIVE_EVALUATION** | multicámara, lifecycle, aceleración, eventos, búsqueda, recovery | Auditoría comparativa contra ClearCam/TukeVision; no convertir TukeVision en segundo NVR |
| ONVIF-MEDIA-SIGNING | `https://github.com/onvif/media-signing-framework` | estándar / referencia oficial | **ACTIVE_EVALUATION / CONTRACT_READY** | Evidence, provenance, cadena de custodia | Sandbox sign→verify→tamper→fail; hardware físico cuando esté disponible |
| DETECTRON2-FAIR | `https://github.com/facebookresearch/detectron2` | CV framework | **REJECTED_FOR_CURRENT_PROFILE / WATCH** | percepción/segmentación | Reabrir sólo si cambia hardware o aparece brecha que YOLO/OpenVINO no resuelva |
| GODS-EYE-VIEW | referencia ya registrada en TES | arquitectura/UX espacial | **ADAPTED / WATCH** | estado espacial, viewshed, handoff, provenance | Consultar ante problemas espaciales/multicámara; no integrar aplicación externa |
| AMBIENT-AI | referencia industrial | agentic monitoring / UX | **ADAPTED / WATCH** | Agent Monitor, atención selectiva | Consultar métricas de reducción de carga y priorización |
| HIFOCUS-INTELLISEEK | referencia industrial | investigación CCTV | **ADAPTED_PARTIAL / ACTIVE_EVALUATION** | P0-65, búsqueda histórica | Evaluar análisis local bajo demanda sobre DVR/NVR sin indexar todo el video |
| AVIGILON | referencia enterprise | VMS / analytics | **ACTIVE_EVALUATION** | búsqueda, multisitio, privacidad, video+access | Extraer patrones; no adoptar ecosistema vertical |
| MARCH-NETWORKS | referencia enterprise | VMS / connected intelligence | **ACTIVE_EVALUATION** | agregador, correlación, investigación | Comparar patrón video+datos+acceso+multisitio |
| SMARTPSS-LITE | experiencia de producto | VMS / operación | **ACTIVE_EVALUATION** | UX, operación, interoperabilidad | Consultar como benchmark de producto sin copiar arquitectura |
| NCSC-AGENTIC-SECURITY | guía autoridad | seguridad / agentes | **ACTIVE_EVALUATION** | autonomía, mínimo privilegio, safe mode | Integrar como control/gobernanza, no como dependencia |
| PURPOSE-BOUND-INVESTIGATION | experiencia de gobernanza | privacidad / investigación | **ADAPTED** | P0-59, P0-65, P0-66, P1-69 | Toda búsqueda IA debe usar purpose/case/scope/audit |
| AGENTIC-VIDEO-UNDERSTANDING | referencia técnica | procesamiento selectivo | **ACTIVE_EVALUATION** | P0-62/P0-64/P0-65/P0-76 | Benchmark patrón local de muestreo dirigido; no subir video cliente a cloud |
| OC-SORT | tracker candidato | tracking | **CONDITIONAL_BENCHMARK** | `src/tracking/` | Activar ante ID switches/oclusiones/recovery deficientes demostrados |
| COTRACKER | tracker candidato | point tracking | **RESERVE / CONDITIONAL** | tracking experimental | Activar sólo si bbox tracking resulta insuficiente |
| TAPNET | tracker candidato | point tracking | **RESERVE / CONDITIONAL** | tracking experimental | Igual condición que CoTracker |
| TRACE-ANYTHING | tracker/segmentación candidato | tracking experimental | **RESERVE / CONDITIONAL** | seguimiento denso | Benchmark sólo ante necesidad demostrada |
| SMOLVLM | VLM local candidato | VLM | **WATCH / CONDITIONAL_BENCHMARK** | Context Analyzer / evidence | Activar cuando P0-65 requiera lenguaje natural local bajo presupuesto edge |
| FASTVLM | VLM local candidato | VLM | **WATCH / CONDITIONAL_BENCHMARK** | Context Analyzer / evidence | Comparar latencia/calidad local cuando se active VLM |
| QWEN3-VL | VLM candidato | VLM | **WATCH / CONDITIONAL_BENCHMARK** | evidence summaries / investigation | Sólo local y selectivo; medir RAM/latencia |
| SCREEN2IPCAM | SourceForge | source adapter | **WATCH** | P0-67 Universal Source Connector | Activar cuando exista necesidad POS/pantalla legacy |
| RAPIDVMS | referencia VMS | VMS | **BENCHMARK_REFERENCE_ONLY** | lifecycle / VMS | No integrar por conflicto segundo-NVR; extraer sólo patrones |
| ONVIF-PROFILE-M | estándar | metadata/events | **WATCH / P1** | observaciones normalizadas | Preparar interoperabilidad sin dependencia obligatoria |
| ONVIF-PROFILE-V | estándar | cloud interoperability | **WATCH / P2** | conectividad futura | Readiness únicamente; local-first permanece |
| ALOCITY-MERCURY | referencia industria 2026-09-08 | access+video+AI | **ACTIVE_EVALUATION / CONTRACT_PATTERN** | ACCESS Observation, correlación, multimodal | Formalizar fuente ACCESS neutral; no integrar proveedor |
| FLOCK-FREEFORM-GOVERNANCE | experiencia reciente | semantic investigation governance | **ACTIVE_EVALUATION / GOVERNANCE** | purpose-bound search, audit | Integrar patrón de scopes/permisos; resultado IA = lead |
| MAGI-ARCHIVE | corpus de descubrimiento | discovery layer | **DISCOVERY_LAYER** | radar / experience engine | Descubrir candidatos; verificar siempre fuente original |
| RADAR-MMWAVE | tecnología futura | sensor | **RESERVE** | multimodal observation | Reabrir sólo por caso físico/privacidad/entorno que lo justifique |
| THERMAL | tecnología futura | sensor | **RESERVE** | multimodal observation | Reabrir por incendio/industrial/condición térmica real |
| AUDIO-ANALYTICS | tecnología futura | sensor | **RESERVE** | multimodal observation | Reabrir con base legal, hardware y caso operativo claros |

## Política de forjas — GitHub + GitLab

TES mantiene **GitHub y GitLab como fuentes prioritarias de conocimiento técnico**. El radar no debe limitar la exploración a una sola forja cuando busca soluciones, referencias, librerías, benchmarks o implementaciones maduras.

Para cada fuente basada en código se deben registrar, cuando sea aplicable:

```text
FORGE = GITHUB | GITLAB | OTHER
CANONICAL_UPSTREAM = <url>
MIRRORS = <urls opcionales>
LAST_VERIFIED_REF = <commit/tag/release>
LAST_VERIFIED_AT = <timestamp/date>
LICENSE = <license>
TES_DECISION = <estado>
REVISIT_WHEN = <condición>
```

Regla de búsqueda:

```text
PROBLEMA / BRECHA
→ TES
→ GITHUB SEARCH
→ GITLAB SEARCH
→ FUENTES ORIGINALES
→ EVIDENCIA
→ BENCHMARK / DECISIÓN
```

No se debe declarar `NO_RELEVANT_EXTERNAL_EXPERIENCE_FOUND` sin haber considerado ambas forjas, salvo que una sea manifiestamente irrelevante para el dominio o no esté accesible; esa excepción debe quedar registrada.

Cuando el mismo proyecto esté alojado o espejado en ambas forjas, se conserva **un único SOURCE_ID** y se identifica el upstream canónico para evitar duplicar conocimiento.

## Refresh log — fuentes GitHub / GitLab

### 2026-09-08 — `roryclear/clearcam` — GitHub

- Upstream: `main` activo y repositorio no archivado.
- Latest release verificada: **0.2.8**, publicada 2026-08-31.
- Cambios materiales del release: streams de `.ts` a `.m4s`, correcciones de scrubbing, mejor sincronización temporal entre feeds y startup más rápido.
- Impacto TukeVision: refuerza prioridad del benchmark de `playback/freshness`, sincronización multicámara y startup/recovery; no cambia la frontera GPL ni autoriza copia directa.
- Decisión: `ACTIVE_EVALUATION_HIGH` se mantiene y gana prioridad operativa.

### GitLab

- GitLab queda activado como forge de búsqueda y actualización de igual prioridad que GitHub.
- No se registra aquí un proyecto GitLab específico sin upstream verificado; los candidatos se incorporarán por `SOURCE_ID` conforme sean identificados y validados.

## Regla de consulta

Ante un problema, el agente/ingeniero debe buscar primero por:

1. síntoma;
2. subsistema;
3. patrón;
4. experiencia relacionada;
5. decisión previa.

Si hay una coincidencia, la solución nueva debe explicar por qué no reutiliza/adapta esa experiencia.

## Regla de frescura

Las fuentes `ACTIVE_EVALUATION`, `BENCHMARK`, `WATCH` y `DISCOVERY_LAYER` deben revisarse cuando:

- se presenta un problema relacionado;
- se toca el subsistema correspondiente;
- aparece una release/cambio material conocido;
- una decisión depende de una característica upstream;
- el radar ejecuta una revisión periódica.

La revisión debe comprobar el upstream canónico, sea GitHub o GitLab, y actualizar `EXPERIENCE_STORE.md`, `TECHNOLOGY_RADAR.md` y `DECISION_LOG.md` sólo cuando exista cambio material.
