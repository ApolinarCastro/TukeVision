# Radar de Tecnología — TukeVision V3

**UPDATED:** 2026-09-08  
**MODE:** ACTIVE_EVALUATION  
**RULE:** toda experiencia relevante debe poder pasar de conocimiento a benchmark/decisión; `TES_REFERENCE_ONLY` ya no es un estado final válido para candidatos que resuelven brechas actuales.

El Radar clasifica tecnologías, bibliotecas, estándares, productos de referencia y patrones bajo la gobernanza TES V3.

---

## 0. Cola Activa de Evaluación

Esta cola se consulta antes de diseñar soluciones nuevas.

### P0-ACTIVE — impacto directo en problemas/capacidades actuales

| Candidato / experiencia | Brecha TukeVision | Acción expedita | Restricción |
|---|---|---|---|
| **ClearCam (`roryclear/clearcam`)** | resiliencia RTSP, playback/freshness, tracking temporal, selective inference, event/semantic search | **BENCHMARK + ADAPT PATTERNS** | GPL-3.0; no copiar código al core |
| **Frigate** | lifecycle multicámara, recovery, aceleración, eventos, storage/search | **AUDIT/BENCHMARK** contra ClearCam y TukeVision | no convertir TukeVision en segundo NVR |
| **ONVIF Media Signing** | provenance e integridad desde origen | **SANDBOX BENCHMARK** sign→verify→tamper→fail | hardware físico puede quedar pendiente |
| **NCSC Agentic Security** | mínimo privilegio, safe mode, control herramientas | **ADAPT GOVERNANCE** | guía/patrón, no dependencia |
| **Alocity/Mercury access+video pattern** | correlación ACCESS + VIDEO + LOCATION + TIME | **CONTRACT READINESS** | proveedor-neutral; no módulo Mercury |
| **Purpose-Bound / Flock governance pattern** | abuso de búsqueda semántica / ampliación de scope | **ADAPT GOVERNANCE** | AI result = lead, no fact |

### P1-ACTIVE — puede acelerar siguiente value slice

| Candidato / experiencia | Brecha | Acción |
|---|---|---|
| **HiFocus IntelliSeek** | investigación histórica sin indexar cada frame | evaluar análisis local bajo demanda sobre DVR/NVR |
| **Ambient.ai** | reducción de carga cognitiva / atención selectiva | adaptar métricas y flujo, no producto |
| **Avigilon** | búsqueda, multisitio, privacidad, video+access | extraer patrones enterprise |
| **March Networks** | video + datos + acceso + multisitio | comparar con agregador/correlación TukeVision |
| **SmartPSS Lite** | UX/operación VMS real | benchmark de producto y flujos operador |
| **Agentic Video Understanding** | procesamiento de video largo caro | benchmark patrón local de muestreo dirigido |

### CONDITIONAL BENCHMARK

- OC-SORT: activar ante ID switches/oclusiones/recovery deficientes medidos.
- CoTracker / TAPNet / Trace Anything: activar sólo si bbox tracking demuestra ser insuficiente.
- SmolVLM / FastVLM / Qwen3-VL: activar cuando investigación/evidencia requiera VLM local selectivo.
- ONNX Runtime: activar ante hardware/plataforma no cubierta satisfactoriamente por OpenVINO.
- screen2ipcam: activar con necesidad real POS/pantalla legacy.

---

```text
               ▲
               │      ADOPT
               │   • OpenVINO
               │   • PyAV / FFmpeg
               │   • ByteTrack
               │   • Tkinter + DesignTokens
               │   • SQLite Structured Indexing
               │
    ADAPT      │      EVALUATE / ACTIVE
 • God's Eye   │   • ClearCam broader benchmark
 • Ambient.ai  │   • Frigate audit
 • IntelliSeek │   • ONVIF Media Signing
 • ClearCam RTSP│  • Access+Video contract
───────────────┼────────────────►
    WATCH      │      RESERVE
 • Local VLM   │   • Radar mmWave
 • Profile M/V │   • Thermal
 • WebRTC Aux  │   • Audio analytics
               │
               │      REJECT / CURRENT PROFILE
               │   • Detectron2 as edge production runtime
               │   • Chromium/Electron UI
               │   • Continuous 24/7 recording in TukeVision host
```

---

## 1. `ADOPT` — adoptadas en el perfil actual

| Tecnología / capacidad | Justificación | Estado |
|---|---|---|
| **OpenVINO Edge Runtime** | runtime primario de inferencia optimizado para perfil Intel actual | `ADOPTED / VERIFY PER CURRENT BASELINE` |
| **PyAV / FFmpeg** | ingesta/decodificación y lifecycle de streams | `ADOPTED` |
| **ByteTrack** | tracking bbox actual | `ADOPTED`; no reemplazar sin benchmark |
| **Tkinter + DesignTokens** | UI nativa de bajo consumo | `ADOPTED` |
| **SQLite Structured Indexing** | eventos/evidencia/búsqueda estructurada local | `IMPLEMENTED / OPERATIONAL` |

> La presencia en `ADOPT` no autoriza sobredeclarar certificación física. La madurez exacta se consulta en `CAPABILITY_MATRIX.md` y evidencia correspondiente.

---

## 2. `ADAPT` — patrones incorporados sin dependencia directa

| Patrón | Origen | Adaptación TukeVision | Estado |
|---|---|---|---|
| **God's Eye View** | referencia espacial/command center | spatial scene state, viewshed, handoff, freshness/provenance | `ADAPTED / WATCH` |
| **Ambient.ai / agentic monitoring** | industria | atención selectiva, investigación y reducción de carga | `ADAPTED_PATTERN` |
| **HiFocus IntelliSeek** | industria | búsqueda estructurada + dirección hacia análisis histórico bajo demanda | `ADAPTED_PARTIAL / ACTIVE_EVALUATION` |
| **ClearCam RTSP Recovery** | `roryclear/clearcam` | startup grace, consecutive-failure threshold, single-owner decoder, first-frame recovery | `ADAPTED_PARTIAL` |
| **Purpose-Bound Investigation** | experiencia de gobernanza CCTV IA | purpose→case→permission→scope→query→lead→evidence→human/audit | `ADOPT_GOVERNANCE_PATTERN` |
| **Agentic Video Selection** | procesamiento de video dirigido | muestreo/atención selectiva como patrón local futuro | `ADAPT_PATTERN / BENCHMARK` |

### Regla especial ClearCam

ClearCam deja de estar limitado a “RTSP pattern learned”. Se clasifica además como:

```text
STATUS = ACTIVE_ENGINEERING_CANDIDATE
PRIORITY = HIGH
ADOPTION_MODE = BENCHMARK + PATTERN_ADAPTATION
DIRECT_CORE_COPY = NO
GPL_BOUNDARY = ACTIVE
```

Targets activos:

1. RTSP / decoder supervision / playback freshness.
2. selective inference / wait-for-frame.
3. stationary/recovery tracking y comparación OC-SORT.
4. event/semantic search e indexed evidence.
5. local VLM sólo como benchmark selectivo.

---

## 3. `EVALUATE / ACTIVE`

| Tecnología / experiencia | Motivo | Gate de decisión |
|---|---|---|
| **ClearCam broader benchmark** | ya resolvió parcialmente problemas de resiliencia; contiene patrones adicionales relevantes | mismo video/hardware: recovery, CPU/RAM, stale frames, ID switches, search latency |
| **Frigate** | referencia OSS madura CCTV/NVR | mapear ingestion, go2rtc/ffmpeg, lifecycle, hardware accel, events, search, recovery; adoptar sólo patrones útiles |
| **ONVIF Media Signing** | autenticidad/integridad desde captura | benchmark de referencia; `SOURCE_UNSIGNED` cuando no exista firma real |
| **NCSC agentic security** | control externo al modelo | mapear mínimo privilegio, deny-by-default, isolation, safe mode, audit |
| **Alocity/Mercury pattern** | convergencia abierta access+video+AI | formalizar `SOURCE_TYPE=ACCESS` y `AccessObservation`; no integración propietaria |
| **Avigilon / March Networks** | experiencia enterprise | identificar palancas reales que mejoren correlación/investigación/multisitio |
| **SmartPSS Lite** | benchmark operativo VMS | comparar UX y operaciones que TukeVision deba simplificar/mejorar |

---

## 4. `WATCH`

| Tecnología / capacidad | Condición de reevaluación |
|---|---|
| **Semantic NLP / Local VLM** | activar cuando búsqueda estructurada sea insuficiente para una necesidad real |
| **SmolVLM / FastVLM / Qwen3-VL** | medir sólo en benchmark local y selectivo; no VLM continuo |
| **ONVIF Profile M** | cuando metadata/eventos interoperables sean necesarios en integración física |
| **ONVIF Profile V** | readiness únicamente; no migrar local-first a cloud |
| **WebRTC Gateway** | cuando exista requerimiento real de visualización web remota |
| **screen2ipcam** | cuando se necesite incorporar pantalla/POS legacy como fuente |
| **MAGI / repo discovery** | discovery layer; cada candidato requiere fuente original |

---

## 5. `RESERVE`

| Tecnología | Motivo |
|---|---|
| **Radar mmWave** | útil en condiciones específicas, no prioridad retail actual |
| **Cámaras térmicas** | reservar para incendio/industrial/caso térmico concreto |
| **Audio analítico** | privacidad/hardware/caso operacional aún no justifican implementación |
| **CoTracker / TAPNet / Trace Anything** | tracking denso/point tracking sólo si el baseline bbox no resuelve una brecha real |

---

## 6. `REJECT / CURRENT PROFILE`

| Tecnología / enfoque | Decisión | Reabrir cuando |
|---|---|---|
| **Detectron2 como runtime edge productivo** | `REJECTED_FOR_CURRENT_PROFILE` por costo/compatibilidad frente al baseline ligero | cambie hardware o exista problema de segmentación no resoluble por baseline |
| **Chromium/Electron UI** | rechazado por consumo y duplicación de stack | cambie necesidad de producto/plataforma |
| **Grabación continua 24/7 en host TukeVision** | rechazado; DVR/NVR conserva rol primario | no reabrir salvo cambio explícito de producto |
| **RapidVMS como dependencia/producto** | no integrar; referencia benchmark | sólo patrones aislados compatibles con límites TukeVision |

---

## 7. Fuentes multimodales — readiness neutral de proveedor

Formalizar como contrato, no como drivers inmediatos:

```text
SOURCE_TYPE =
VIDEO
ACCESS
INTERCOM
RADAR
THERMAL
AUDIO
SENSOR
OTHER_AUTHORIZED_SOURCE
```

`ACCESS` pasa a ser señal operacional activa de diseño. Regla epistémica:

```text
CREDENTIAL_EVENT ≠ PERSON_IDENTITY
ACCESS_EVENT ≠ VISUAL_CONFIRMATION
```

La correlación posterior decide relaciones con evidencia y confianza explícita.

---

## 8. Regla de resolución de problemas

Antes de crear un nuevo componente:

```text
PROBLEM
→ TES/KNOWLEDGE_SOURCE_INDEX
→ TES/EXPERIENCE_STORE
→ TES/DECISION_LOG
→ TECHNOLOGY_RADAR
→ EXISTING CAPABILITY
→ BENCHMARK / ADAPT
→ NEW CODE ONLY IF GAP REMAINS
```

Consultar [ACTIVE_EVALUATION_PROTOCOL.md](ACTIVE_EVALUATION_PROTOCOL.md).

---

## 9. Mantenimiento del radar

Un cambio upstream NO cambia automáticamente una decisión. Actualizar el radar sólo si existe cambio material en:

- capacidad;
- madurez;
- licencia;
- compatibilidad;
- costo/rendimiento relevante;
- brecha TukeVision;
- condición de reevaluación.

Cada fuente activa debe estar indexada en [KNOWLEDGE_SOURCE_INDEX.md](KNOWLEDGE_SOURCE_INDEX.md).
