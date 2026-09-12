# Radar de Tecnología — TukeVision V3

**UPDATED:** 2026-09-11  
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
| **Shinobi (`Shinobi-Systems/Shinobi`, GitLab)** | live-grid render, substream switching, next/previous monitor navigation, ONVIF scanner, RTSP transport | **BENCHMARK / ADAPT PATTERNS** contra Gate 0C y Gate 1 | licencia Shinobi Open Source EULA; no copiar código al core |
| **ONVIF Media Signing** | provenance e integridad desde origen | **SANDBOX BENCHMARK** sign→verify→tamper→fail | hardware físico puede quedar pendiente |
| **ONVIF TLS Configuration Add-on 2.0 RC** | configuración TLS interoperable y endurecimiento del onboarding LAN/DVR | **BENCHMARK + CONTRACT READINESS** | Release Candidate; no declarar conformidad antes de finalización/test tools |
| **GeoVision GV-LPC2011/2211 advisory 2026-09** | Gate 1 puede asumir que discovery/ONVIF auth son benignos; el advisory expone replay WS-Security, command injection y DoS en discovery | **ADAPTAR + BENCHMARK DE SEGURIDAD** | vendor-specific; no extrapolar CVE a otros equipos, sí reutilizar patrón de controles negativos |
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
 • IntelliSeek │   • Shinobi live-grid/substream benchmark
 • ClearCam RTSP│  • ONVIF Media Signing
               │   • ONVIF TLS Configuration 2.0 RC
               │   • GeoVision ONVIF security patterns
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
| **ONVIF negative-security patterns** | GeoVision GV-LPC2011/2211 advisory 2026-09 | exigir replay resistance, input bounds y aislamiento de valores ONVIF antes de Gate 1; tratar discovery/auth como superficie hostil | `ADAPT_GOVERNANCE / BENCHMARK_PENDING` |

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
| **Shinobi (GitLab upstream)** | upstream activo con fixes recientes de live grid, substream y next/previous monitor navigation que coinciden con defectos físicos Gate 0C | benchmark de patrón sobre navegación, ownership de paneles y transición de substream; no integrar producto ni copiar código |
| **ONVIF Media Signing** | autenticidad/integridad desde captura | benchmark de referencia; `SOURCE_UNSIGNED` cuando no exista firma real |
| **ONVIF TLS Configuration Add-on 2.0 RC** | RC publicada 2026-09-09 con requisitos TLS más fuertes; impacto directo en Gate 1 LAN/DVR onboarding | mapear configuración/certificados/cipher policy y capacidad del DVR; implementar sólo cuando exista soporte real y especificación/test tool aplicables |
| **GeoVision GV-LPC2011/2211 security advisory 2026-09** | advisory oficial del 2026-09-10 agrupa 23 CVE y demuestra que ONVIF discovery/auth/event subscription puede ser una superficie de ataque real | antes de Gate 1: pruebas negativas para replay, malformed/excessive discovery scopes, parámetros de callback/subscribe y sanitización; inventario de firmware del DVR/cámaras |
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
| **ONVIF TLS Configuration Add-on 2.0** | reevaluar al publicarse especificación final/test tools a fin de 2026 o antes si Gate 1 descubre capacidad TLS configurable en DVR/cámaras |
| **GeoVision GV-LPC2011/2211** | reevaluar sólo para el producto si aparece hardware GeoVision o nuevos CVE relevantes; los patrones defensivos ya pasan a Gate 1 vendor-neutral |
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
| **Shinobi como dependencia/producto** | no integrar; benchmark de patrones únicamente por rol NVR y licencia/EULA comercial | reabrir sólo si cambia explícitamente el modelo de producto/licencia |

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

---

## 10. Refresh 2026-09-10

### ONVIF TLS Configuration Add-on 2.0 RC — `BENCHMARK / WATCH`

- **Upstream canónico:** ONVIF; especificación oficial en ONVIF y desarrollo público en `onvif/specs`.
- **Cambio material:** ONVIF publicó el 2026-09-09 la Release Candidate 2.0 del TLS Configuration Add-on, orientada a métodos criptográficos más fuertes y configuración TLS interoperable; la final está prevista para fin de 2026.
- **Mapeo TukeVision:** Gate 1 LAN/DVR onboarding, discovery/configuración ONVIF, seguridad de transporte y capability negotiation.
- **Riesgo:** RC no equivale a estándar final ni a conformidad del DVR/cámara; no sobredeclarar soporte.
- **Siguiente gate:** durante Gate 1 inventariar capacidades TLS/ONVIF reales del DVR/cámaras y mantener fallback seguro; sandbox sólo si hardware expone la función.

### Shinobi GitLab — `BENCHMARK / ADAPTAR`

- **Upstream canónico:** `gitlab.com/Shinobi-Systems/Shinobi`; no se usa mirror/fork como fuente.
- **Actividad verificada:** commit `c4cb68d0` (2026-08-20) corrige Live Grid; MR !548 incluye fixes de `open next/previous monitor navigation` y `loading substream issues`; MR !557 (2026-08-05) añade hardening de autenticación/permisos y rutas.
- **Licencia:** Shinobi Open Source Software License Agreement (EULA propia; uso comercial sujeto a condiciones). No copiar código al core.
- **Mapeo TukeVision:** defectos físicos Gate 0C (grid, navegación foco, substream) y seguridad de onboarding/operación en Gate 1.
- **Siguiente gate:** benchmark de comportamiento/patrón desde baseline estable antes de nuevo diseño; `KNOWLEDGE ≠ DEPENDENCY`.

---

## 11. Refresh 2026-09-11

### GeoVision GV-LPC2011/2211 — `ADAPTAR / BENCHMARK`

- **Fuente primaria:** GeoVision Cyber Security, advisory `GV-LPC-2026-09-01`, publicado el **2026-09-10**, estado `Completed`, con **23 CVE** (`CVE-2026-88268` a `CVE-2026-88290`).
- **Hallazgos materiales verificados en registros CVE asociados:**
  - `CVE-2026-88278`: replay de ONVIF WS-Security UsernameToken/PasswordDigest por falta de freshness/nonce reuse protection; CVSS 9.8.
  - `CVE-2026-88277`: command injection autenticado a través de parámetros ONVIF Subscribe/ConsumerReference; ejecución de comandos con privilegios elevados en la versión afectada.
  - `CVE-2026-88287`: DoS remoto no autenticado mediante exceso de `Scopes` en ONVIF WS-Discovery Probe; la versión 1.14 figura como no afectada en el registro CVE.
- **Problema que resuelve para TukeVision:** no integrar Gate 1 suponiendo que discovery, autenticación ONVIF o callbacks son datos confiables. El onboarding debe validar firmware/capacidades y tratar respuestas/inputs ONVIF como no confiables.
- **Mapeo:** Gate 1 LAN/DVR onboarding, discovery, credenciales, capability negotiation, suscripciones/eventos, segmentación de red y auditoría de dispositivo.
- **Impacto:** alto para el diseño de seguridad de Gate 1; bajo para runtime actual porque TukeVision no incorpora GeoVision ni expone esos endpoints como servidor.
- **Riesgo:** extrapolar vulnerabilidades de un producto específico a todo ONVIF. La adaptación permitida es el patrón defensivo, no la afirmación de que ONVIF sea inseguro ni la copia de mitigaciones propietarias.
- **Siguiente gate:** añadir al diseño de Gate 1 un `DEVICE_SECURITY_INVENTORY` y un benchmark negativo: replay de credenciales/tokens cuando aplique, payloads de discovery acotados, sanitización estricta de callback/URI/Subscribe y aislamiento de credenciales. No implementar hasta que Gate 1 sea autorizado.
- **Reevaluación:** si el hardware real es GeoVision, verificar firmware contra advisory antes de onboarding; si no, mantener sólo los controles vendor-neutral y seguir PSIRT/CVE de los fabricantes reales.

### Cobertura de forjas y upstream — 2026-09-11

- **GitHub:** revisados upstreams activos de ClearCam y Frigate. ClearCam no presenta cambios posteriores al commit `91f2f77` del 2026-09-08 que alteren la decisión TES. Frigate 0.18 RC2 (2026-09-07) mejora playback/UI y CUDA, pero no cambia el boundary TukeVision ni resuelve mejor que los candidatos ya activos la brecha Gate 0C/Gate 1; se mantiene `ACTIVE_EVALUATION` sin nueva adopción.
- **GitLab:** revisado el upstream canónico Shinobi; no se detectó cambio material posterior al conjunto ya documentado (live-grid/substream/next-prev/auth hardening). No se duplicaron forks/mirrors.
- **ONVIF:** no hay cambio material posterior a TLS Configuration Add-on 2.0 RC del 2026-09-09; la clasificación previa se mantiene.
- **Seguridad de fabricante:** el advisory GeoVision del 2026-09-10 sí constituye cambio material y activa la actualización TES de este refresh.
