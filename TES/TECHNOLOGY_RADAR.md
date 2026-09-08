# Radar de Tecnología — TukeVision V3

El Radar de Tecnología clasifica tecnologías, proyectos, estándares y patrones evaluados para TukeVision bajo gobernanza TES V3.

**Regla vigente:** el Radar es un sistema activo de evaluación. Todo elemento TES en `EVALUATE`, `WATCH`, `BENCHMARK`, `TARGET` o equivalente entra en la cola activa y debe ser reactivado cuando un problema real coincida con su área de experiencia.

```text
PROBLEMA / BRECHA
→ TES-FIRST SEARCH
→ EXPERIENCIAS RELACIONADAS
→ ACTIVE_EVALUATION
→ BENCHMARK / CONTRATO / PRUEBA
→ ADAPT | INTEGRATE | ALREADY_RESOLVED | RESERVE | REJECT
```

---

## 1. `ADOPT` — Adoptadas / baseline vigente

| Tecnología / Capacidad | Aporte | Estado |
| :--- | :--- | :--- |
| **OpenVINO Edge Runtime** | Inferencia eficiente en hardware Intel x86_64/iGPU. | `ADOPTED / CERTIFIED` |
| **PyAV / FFmpeg** | Ingesta y decodificación RTSP/H.264/H.265. | `ADOPTED / CERTIFIED` |
| **ByteTrack** | Tracking multiobjeto actual. | `ADOPTED / BASELINE` |
| **Tkinter + DesignTokens** | UI nativa de bajo consumo. | `ADOPTED` |
| **SQLite Structured Indexing** | Persistencia/búsqueda estructurada local. | `IMPLEMENTED / OPERATIONAL` |

---

## 2. `ADAPT` — Patrones incorporados o en adaptación activa

| Experiencia | Origen | Adaptación TukeVision | Estado |
| :--- | :--- | :--- | :--- |
| **ClearCam — RTSP/FFmpeg resilience** | `roryclear/clearcam` | startup grace, failure threshold, single-owner decoder, first-frame confirmation. | `ADAPTED + ACTIVE_BENCHMARK` |
| **ClearCam — selective inference / event search / stationary tracking** | `roryclear/clearcam` | candidatos para cómputo adaptativo, P0-65 e identidad temporal. | `ACTIVE_EVALUATION` |
| **God's Eye View** | referencia espacial | spatial scene state, viewshed, freshness, provenance, agent context. | `ADAPTED` |
| **Ambient.ai / Agentic monitoring** | industria | atención selectiva, reducción de carga del operador, case-oriented investigation. | `ADAPT_PATTERN` |
| **HiFocus IntelliSeek** | industria | investigación histórica local bajo demanda sin indexar todo el CCTV. | `ADAPT_PATTERN` |
| **Purpose-Bound Investigation** | gobernanza de búsqueda CCTV | purpose → case → permission → scope → query → lead → evidence → audit. | `ADOPT_GOVERNANCE_PATTERN` |
| **Agentic Video Understanding** | referencia técnica | temporal search, dynamic re-sampling, selective high-FPS inspection. | `ADAPT_PATTERN / BENCHMARK_REQUIRED` |
| **March Networks / Avigilon** | VMS enterprise | correlación multifuente, investigación, multisitio, atención selectiva. | `ADAPT_PATTERN` |
| **Access + Video + AI open convergence** | PACS/Mercury/Alocity pattern | `ACCESS` como `NormalizedObservation`, correlación neutral de proveedor. | `CONTRACT_ADAPTATION` |

---

## 3. `ACTIVE_EVALUATION` — Cola activa importada desde TES

Estos elementos no pueden permanecer “dormidos”. Deben revisarse cuando aparezca una brecha relacionada y, además, en la revisión periódica del Radar.

| Candidato / experiencia | Problema que puede resolver | Componente relacionado | Próxima decisión / `REVISIT_WHEN` |
| :--- | :--- | :--- | :--- |
| **ClearCam completo como referencia de ingeniería** | resiliencia RTSP, playback, inferencia selectiva, tracking, event search | SourceManager, ViewModel, tracking, P0-65 | benchmark contra fallos reales antes de reinventar |
| **Frigate** | lifecycle de cámaras, ffmpeg/go2rtc, multicámara, hardware acceleration, events/search | SourceManager, ingestion, resilience | auditar cuando haya defecto de lifecycle/recovery o benchmark de ingestión |
| **ONVIF Media Signing** | autenticidad/provenance de evidencia desde origen | EvidenceStore, provenance, investigation | validar hardware firmado cuando exista; contrato permanece activo |
| **ONVIF Analytics Metadata / Profile M** | interoperabilidad de metadata y eventos IA | contracts/evidence | evaluar cuando se conecte fuente ONVIF con metadata analítica |
| **ONVIF Profile V** | interoperabilidad futura de video/cloud | source contracts | readiness; no migrar cloud sin necesidad demostrada |
| **ONNX Runtime fallback** | hardware no Intel / portabilidad | inference provider | benchmark si OpenVINO no cubre hardware objetivo |
| **OC-SORT** | ID switches / stationary tracking / oclusión | tracking | benchmark si ByteTrack falla en defecto reproducible |
| **CoTracker / TAPNet / Trace Anything** | point/dense tracking y recovery compleja | future TrackerContract | evaluar sólo ante necesidad de tracking no-bbox |
| **SmolVLM** | análisis contextual local de evidencia | EvidenceSelector / ContextAnalyzer | benchmark con evidencia selectiva y presupuesto RAM/latencia |
| **FastVLM** | VLM local de baja latencia | ContextAnalyzer | benchmark cuando haya hardware compatible |
| **Qwen3-VL** | análisis VLM local/edge | ContextAnalyzer | benchmark selectivo; no VLM continuo |
| **Semantic NLP / Semantic Investigation** | consulta natural sobre evidencia | P0-65 | activar al consolidar índice representativo y scope de investigación |
| **DVR/NVR AI On-Demand** | investigación histórica sin embeddings de todo el video | P0-65 / DVR connector | activar cuando API/export del DVR esté disponible |
| **Attention Orchestrator Metrics** | medir reducción de carga cognitiva | P0-66 / Agent Monitor | evaluar con baseline operacional real |
| **NCSC agentic security patterns** | mínimo privilegio, aislamiento, safe mode | autonomy/governance | integrar al habilitar acciones de agente |
| **WebRTC Gateway Auxiliar** | visualización remota | presentation/source gateway | sólo ante requisito real de navegador/remoto |
| **screen2ipcam** | fuentes legacy/POS como RTSP/ONVIF | Universal Source Connector | evaluar si aparece fuente de pantalla/POS requerida |
| **SmartPSS Lite** | patrones de VMS/DVR, UX y operaciones | connector/UI/investigation | benchmark de comportamiento, no dependencia |
| **March Networks** | video + datos + acceso + multisite | correlation/investigation | adaptar contrato cuando se materialicen fuentes no-video |
| **Avigilon** | search, appearance, access/video, normality, multisite | investigation/correlation | benchmark de experiencia enterprise, sin vendor lock-in |
| **RapidVMS** | referencia VMS | ingestion/storage/UI | `BENCHMARK_REFERENCE_ONLY`; no segundo NVR |
| **JetBrains Junie** | tooling de agentes de desarrollo | engineering workflow | benchmark si se requiere subagente CI/CD estandarizado |
| **Access Control / PACS** | credenciales, puertas, visitantes + video | multimodal contracts / correlation | formalizar `AccessObservation`; proveedor concreto sólo ante integración real |

---

## 4. `WATCH` — Vigilar evolución, sin bloquear trabajo actual

| Tecnología / capacidad | Razón | Activar cuando |
| :--- | :--- | :--- |
| **Local VLM ecosystem** | cambios rápidos de rendimiento/modelos | exista caso de uso contextual y presupuesto medible |
| **Semantic retrieval models** | calidad/coste cambian rápidamente | P0-65 requiera embeddings locales |
| **WebRTC / browser delivery** | útil sólo si cambia el requisito de despliegue | acceso remoto sea requisito real |
| **Edge enriched events** | cámaras/controladores pueden entregar eventos enriquecidos | Source Adapter reciba metadata verificable |

---

## 5. `RESERVE` — Futuro detrás de contratos neutrales

| Tecnología | Motivo |
| :--- | :--- |
| **Radar mmWave** | útil en oscuridad/niebla/privacidad, sin prioridad actual. |
| **Cámaras térmicas** | caso de uso específico; no bloquea retail estándar. |
| **Audio anómalo** | privacidad, disponibilidad de micrófonos y validación pendientes. |
| **Dense/point tracking continuo** | coste alto sin brecha actual demostrada. |

---

## 6. `REJECT / NO DIRECT INTEGRATION`

| Tecnología / patrón | Motivo | Reapertura |
| :--- | :--- | :--- |
| **Detectron2 como runtime edge principal** | coste/mantenimiento no justificado frente al baseline actual; evaluación documental no demuestra mejora en nuestro hardware. | sólo benchmark focalizado si aparece necesidad de segmentación/keypoints no cubierta |
| **Chromium/Electron UI** | consumo y complejidad incompatibles con objetivo ligero actual. | sólo si Tkinter deja de cumplir un requisito productivo demostrado |
| **Grabación continua 24/7 en TukeVision** | duplica DVR/NVR primario. | no reabrir salvo cambio explícito de producto |
| **ClearCam como producto/base de código** | GPL-3.0 + arquitectura propia + rol NVR no deseado. | patrones sí; copia directa al core no |
| **RapidVMS como integración de producto** | segundo NVR + conflicto de arquitectura/UI. | referencia/benchmark únicamente |

---

## 7. Reglas de evaluación expedita

### 7.1 TES-first
Antes de desarrollar una solución para un problema real:

1. buscar Experience Cards relacionadas;
2. revisar este Radar;
3. revisar decisiones y `REVISIT_WHEN`;
4. elevar candidatos coincidentes a `ACTIVE_EVALUATION`;
5. ejecutar el benchmark mínimo que pueda decidir;
6. registrar resultado.

### 7.2 No exigir que el baseline “falle por completo”
Una tecnología puede entrar a benchmark si aporta una mejora material demostrable en:

- estabilidad;
- precisión;
- latencia;
- uso de CPU/RAM;
- recuperación;
- trazabilidad;
- carga del operador;
- velocidad de investigación;
- mantenibilidad.

No es necesario esperar un colapso del componente actual para comparar una alternativa prometedora.

### 7.3 No adoptar por novedad

`NEW != BETTER`.

La salida válida de una evaluación es:

`ADAPT | INTEGRATE | ALREADY_RESOLVED | RESERVE | REJECT`.

### 7.4 Licencias y soberanía
- verificar licencia antes de reutilización;
- ClearCam GPL: estudiar/benchmark/reimplementar patrón, no copiar al core;
- no enviar video/embeddings/evidencia sensible a servicios externos sin autorización explícita.

---

## 8. Regla de actualización

Todo hallazgo material nuevo debe:

```text
RADAR FINDING
→ SOURCE VERIFICATION
→ TES MAPPING
→ ACTIVE_EVALUATION OR DECISION
→ EXPERIENCE UPDATE
```

Y todo problema técnico debe empezar con:

```text
TES CONSULTED = YES
```

antes de abrir una solución nueva.
