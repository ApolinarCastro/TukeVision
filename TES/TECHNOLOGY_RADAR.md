# Radar de Tecnología — TukeVision V3

**UPDATED:** 2026-09-25  
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
| **March Networks** | investigación histórica + video/datos/acceso/multisitio | **BENCHMARK** de snapshot-search local + correlación access→video; no cloud dependency |
| **SmartPSS Lite** | UX/operación VMS real | benchmark de producto y flujos operador |
| **Agentic Video Understanding** | procesamiento de video largo caro | benchmark patrón local de muestreo dirigido |
| **Jev / TypeSafe AI — System One Models** | triage, routing, priorización y escalamiento de eventos ya detectados | **WATCH / EXPERIMENTAL → LAB**; evaluar sólo como Event Decision Engine detrás de correlación determinística y delante de Policy Engine |

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
               │   • March Networks snapshot-search/access benchmark
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
| **Representative snapshot investigation** | March Networks 2026 Mid-Year Release | snapshots configurables → índice/búsqueda → candidato → video/evidencia fuente; access-event→video como correlación | `BENCHMARK / ADAPT_PATTERN_PENDING` |

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
6. self-hosted event/notification path con VLM selectivo, sin dependencia de servicio externo.

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
| **Avigilon** | experiencia enterprise | identificar palancas reales que mejoren correlación/investigación/multisitio |
| **March Networks 2026 Mid-Year Release** | patrón explícito de AI Smart Search por snapshots y C•CURE access→video que coincide con P0-65 y correlación ACCESS | benchmark local: snapshots representativos vs. análisis continuo + trazabilidad a evidencia; no integrar producto/cloud |
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
| **WebRTC Gateway** | cuando exista requerimiento real de visualización web remota; incorporar close signaling explícito si se implementa ONVIF WebRTC |
| **screen2ipcam** | cuando se necesite incorporar pantalla/POS legacy como fuente |
| **MAGI / repo discovery** | discovery layer; cada candidato requiere fuente original |
| **Jev / TypeSafe AI — System One Models** | `WATCH / EXPERIMENTAL`; promover sólo por `WATCH → LAB → BENCHMARK → CANDIDATE → PRODUCTION` con datos propios, calibración y Policy Engine |

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

---

## 12. Refresh 2026-09-13

### ClearCam self-hosted notification/Qwen path — `ADAPTAR / BENCHMARK`

- **Upstream canónico:** `github.com/roryclear/clearcam`.
- **Refs verificadas:** `2f65c739d546481edcc78d85213737fda9d0b28a`, `3e69345160c879071c302142005f56693b4cf140`, `078c6cc83714bb0dd1ebdd7ba6919c1890c21559`; integradas en `main` el 2026-09-13.
- **Cambio material:** ClearCam permite mantener Qwen/notificaciones cuando no existe `userID` si se usa `server_url` propio y añade soporte/helper para servidor receptor. El patrón reduce dependencia de servicio SaaS para el camino evento→resumen→notificación.
- **Mapeo TukeVision:** P0-62/P0-65/P0-76, notificaciones/eventos locales, futura distribución LAN de resultados y operación offline/local-first.
- **Riesgo:** GPL-3.0 y commits no firmados; no copiar código al core. El patrón se estudia y se reimplementa de forma independiente sólo tras benchmark.
- **Benchmark mínimo:** `evento local -> VLM selectivo -> endpoint LAN propio -> evidencia recibida`, midiendo latencia, fallo de endpoint, comportamiento offline y verificando que imagen/video no salga a Internet.
- **Estado recomendado:** ClearCam se mantiene `ACTIVE_ENGINEERING_CANDIDATE / HIGH`; se amplía el target, no se adopta el producto.

### ONVIF TLS activation timing + WebRTC close signaling — `ADAPTAR / WATCH`

- **Upstream canónico:** `onvif/specs` como repo oficial de desarrollo; especificación publicada ONVIF sigue siendo autoridad normativa.
- **Refs verificadas:** `bf3ea360e20247d68c2ae0e9c9a715a948f79d78` y `f1b0e50df6ad2779083686406c264806673ba076`, 2026-09-11.
- **Cambio material TLS:** ONVIF añadió un atributo para indicar el tiempo estimado hasta que una nueva configuración TLS quede activa. Contrato derivado: `CONFIGURATION_ACCEPTED != CONFIGURATION_ACTIVE`.
- **Mapeo TLS:** Gate 1 LAN/DVR onboarding y health transicional. El estado debe modelarse `REQUESTED -> APPLYING -> ACTIVE | FAILED/TIMEOUT` cuando el hardware exponga esa capacidad.
- **Cambio material WebRTC:** se añadió señalización `close` para liberar recursos de sesión/ICE/TURN antes de teardown. No activa WebRTC ahora; mejora readiness del `WebRTC Gateway` si se abre ese caso futuro.
- **Benchmark mínimo TLS:** detectar capacidad/tiempo declarado, aplicar en sandbox y verificar conexión efectiva sólo después del periodo de activación; no declarar `ACTIVE` al aceptar la solicitud.
- **Estado recomendado:** TLS continúa `BENCHMARK / WATCH / CONTRACT_READINESS`; WebRTC continúa `WATCH`.

### Ambient.ai Aug-2026 platform release — `ADAPTAR / BENCHMARK`

- **Fuente primaria:** Ambient.ai, anuncio del 2026-08-26.
- **Cambio material:** Agentic Video Walls, Case Management, estado de cámara `degraded` separado de `healthy/unhealthy`, gestión de credenciales/conectividad sin re-onboarding, mayor densidad de streams y mejoras en Semantic/Similarity Search.
- **Problema TukeVision:** distinguir conectividad de calidad visual, reducir carga del operador, construir casos auditables y evitar perder historia al rotar credenciales o actualizar red.
- **Mapeo:** Gate 0C observabilidad/health, P0-59/P0-65/P0-66 investigación/evidencia y futuro onboarding/maintenance Gate 1.
- **Riesgo:** producto propietario/cloud; métricas del proveedor no son evidencia TukeVision. No adoptar VMS ni cloud path.
- **Benchmark mínimo:** validar localmente un tercer estado `DEGRADED_VIEW` independiente de `STREAM_DOWN`, más un caso cronológico con clips/metadata/audit sin depender de Ambient.
- **Estado recomendado:** `ADAPTED / WATCH` se mantiene; se extraen patrones concretos para benchmark, no integración.

### Cobertura de esta ejecución

- **GitHub:** ClearCam, Frigate, ONVIF specs/media-signing y ECC revisados; sólo ClearCam/ONVIF generan cambio TES CCTV material. Frigate continúa 0.18.0 estable sin release posterior que cambie el boundary registrado. ECC 2.2.1 no cambia una capacidad CCTV de producto.
- **GitLab:** Shinobi canónico sigue con `c4cb68d0` como último commit visible del upstream consultado; no hay novedad material posterior al benchmark ya registrado.
- **Fuentes primarias/industria:** Ambient.ai sí aporta patrón material no reconciliado previamente. March Networks, Avigilon, HiFocus, Alocity, Flock, SmartPSS y NCSC fueron revisados sin cambio que altere decisión TES en esta pasada.
- **Mirrors/forks:** ninguno incorporado como fuente independiente.

---

## 13. Refresh 2026-09-14

### March Networks 2026 Mid-Year Release — `BENCHMARK / ADAPTAR`

- **Upstream canónico:** March Networks, página oficial de la `2026 Mid-Year Release`, publicada **2026-08-11**.
- **Licencia/madurez:** producto propietario enterprise; referencia de capacidad, no dependencia ni código reutilizable.
- **Cambio material reconciliado:** la release concreta dos patrones que el TES sólo tenía registrados de forma genérica: (1) AI Smart Search sobre snapshots capturados a intervalos configurables, con búsqueda por lenguaje natural/imagen y trazabilidad al video; (2) correlación C•CURE access-control→video para investigación.
- **Problema TukeVision:** P0-65 necesita investigar histórico sin procesar continuamente cada frame; la correlación ACCESS requiere unir evento físico y video sin inferir identidad.
- **Mapeo:** P0-65 investigation/evidence, `AccessObservation`, agregador multisitio y Evidence First.
- **Boundary:** no Searchlight Cloud como dependencia, no segundo NVR, no subida de video cliente por defecto. DVR/NVR sigue siendo grabador primario y un resultado IA sigue siendo candidato hasta evidencia/humano.
- **Benchmark mínimo decisivo:** sobre el mismo histórico local/DVR, comparar `representative snapshots -> searchable index` contra análisis continuo en recall útil, latencia, CPU/RAM y capacidad de volver al clip/frame fuente; para access, validar `ACCESS_EVENT -> RELATED_VIDEO` sin convertir credencial en identidad.
- **Siguiente gate:** ejecutar sólo cuando se active el slice P0-65 o el conector ACCESS/correlación. No justifica código nuevo antes del benchmark.
- **Estado recomendado:** `ACTIVE_EVALUATION` → `BENCHMARK / ACTIVE_EVALUATION`; no `ACTIVE_ENGINEERING_CANDIDATE` porque la utilidad está en el patrón y el producto/cloud no encaja como dependencia local-first.

### Frescura verificada en la misma pasada

- **ClearCam:** `main` avanzó a `f92e3cba` el 2026-09-14, pero el commit sólo documenta la capacidad de notificaciones personalizadas ya reconciliada en `EXP-CLEARCAM-008`; no cambia decisión/capacidad.
- **Frigate:** `main` presenta actividad 2026-09-14 (incluido soporte Hailo y mantenimiento de dependencias), pero no aparece release posterior a 0.18.0 ni cambio que altere el benchmark actual Gate 0C/Gate 1.
- **ECC (`affaan-m/ECC`):** última release visible sigue `v2.2.1`; commits recientes de memoria/control-plane no cambian capacidad CCTV de producto ni el boundary TukeVision.
- **ONVIF specs:** último conjunto material sigue 2026-09-11 (`bf3ea360`, `f1b0e50d`, `3927e1d2`); sin commit posterior que cambie contrato actual.
- **GitLab Shinobi:** upstream canónico revisado; `c4cb68d0` continúa como commit reciente visible y no hay cambio material posterior para el benchmark Gate 0C/Gate 1.


---

## 14. Canonical reconciliation — 2026-09-18

This section reconciles material upstream evidence recorded in the 2026-09-16 through 2026-09-18 refresh notes into the canonical radar.

### ClearCam local Qwen without provider identity — `ADAPTAR / BENCHMARK`

- **Canonical upstream:** `roryclear/clearcam`.
- **Verified ref:** `84b8740a6c5fb103d24714fdc8d9af997192115e` (2026-09-16).
- **Material change:** local Qwen use no longer depends on a ClearCam user identity/key path.
- **TukeVision mapping:** selective local VLM for P0-64/P0-65/P0-76; local-first/offline event analysis.
- **Boundary:** GPL-3.0; pattern benchmark only, no direct core copy and no ClearCam product adoption.
- **Minimum benchmark:** real local event -> selective Qwen -> structured result -> source-linked evidence/LAN output; verify zero media egress and graceful AI failure.
- **State:** remains `ACTIVE_ENGINEERING_CANDIDATE / HIGH`; target expanded, architecture unchanged.

### Frigate post-0.18 engineering patterns — `ADAPTAR / BENCHMARK`

- **Canonical upstream:** `blakeblackshear/frigate`; stable release remains v0.18.0 while the following refs are post-release development evidence.
- **Verified refs:** `64d6366ac4be29cf9044a2a0e11ba29464ad9765` (2026-09-16), `10a0d5ea373025b9a53fbc90a1c701d76b160928` (2026-09-16), `eccd10cd941a4abdce0cd6ae2aa6b274f7fdbafe` (2026-09-17), `334073967b1ab89154652a9ea1e0cd15831f7d01` (2026-09-17).
- **Material patterns:** explicit live transport selection/async probing and ICE configuration; atomic zone-reference updates; annotated representative frames for GenAI review; optional GenAI audio transcription.
- **TukeVision mapping:** Gate 0C presentation/lifecycle; P0-64 evidence selection; P0-65 semantic investigation; reference-integrity/provenance.
- **Boundary:** MIT upstream does not imply product adoption. DVR/NVR remains primary recorder. No second NVR. Audio remains `WATCH / RESERVE`.
- **Minimum benchmark:** same real evidence, clean vs annotated representative frames, measuring investigation utility, unsupported claims, latency/CPU/RAM and exact source traceability; require `ORIGINAL_EVIDENCE_MUTATED=0`.
- **State:** remains `ACTIVE_ENGINEERING_CANDIDATE / P0-HIGH`; post-release refs are benchmark evidence, not adoption triggers.

### Serval v0.2.5 — `BENCHMARK / ADAPTAR / WATCH`

- **Canonical upstream:** `Flickersoft/serval`.
- **Verified ref:** `596613ccc7b97fe471b09a6bd085c52f57d9f733` / v0.2.5 (2026-09-06).
- **Material change:** process/memory leak fix in a local AI/NVR-oriented stack.
- **TukeVision mapping:** resource hardening, bounded worker lifecycle and graceful degradation.
- **Boundary:** AGPL-3.0-or-later; do not copy code into the core and do not adopt Serval as a second NVR.
- **Minimum benchmark:** >=30 min local load with RSS/process/thread/queue telemetry plus induced AI-worker failure/restart while video remains available.
- **State:** `WATCH / CONDITIONAL BENCHMARK`; promote only if TukeVision resource-hardening evidence shows a matching unresolved defect.

### Freshness check 2026-09-18

- Frigate latest verified canonical commit remains `334073967...` (2026-09-17); no newer material commit was found in the checked upstream.
- ClearCam latest verified canonical commit remains `84b8740a...` (2026-09-16).
- ECC latest release remains v2.2.1; 2026-09-17 commits are sponsor/documentation-only and do not change TukeVision CCTV capability.
- ONVIF `onvif/specs` latest checked commit is `b0ae7de3...` (2026-09-15), adding `Drone` to metadata ObjectType. It does not resolve a current TukeVision P0/P1 gap, so no adoption/priority change is made.
- Serval latest verified canonical commit remains `596613ccc...` (2026-09-06).
- GitLab/Shinobi remains governed by the existing canonical-GitLab benchmark record; no mirror/fork is promoted by this reconciliation.

---

## 15. Refresh 2026-09-18 — Base AI multimodal y herramientas de investigación

### Qwen-MM-Plugins — `ACTIVE_ENGINEERING_CANDIDATE / P0-HIGH`

- **SOURCE_ID:** `QWEN-MM-PLUGINS`
- **UPSTREAM:** `https://github.com/QwenLM/Qwen-MM-Plugins`
- **LAST_VERIFIED_REF:** `fac5c9e307737afadd15bacda0314870e886864c` (2026-09-18)
- **LICENSE:** Apache-2.0
- **CAPABILITIES:** inspección multimodal local para agentes, Skill+MCP por capacidad, lectura/recorte/anotación de imagen/video y patrón de memoria jerárquica para video largo.
- **TUKEVISION_MAPPING:** herramientas de ingeniería, Evidence inspection, P0-64 Evidence Selector, P0-65 Semantic Investigation y memoria de video dirigida.
- **DECISION:** `BENCHMARK + ENGINEERING_TOOL + ARCHITECTURAL_PATTERN`.
- **BOUNDARY:** no subir CCTV de cliente a servicios externos; `video-memory` cloud no se adopta tal cual. Resultado de memoria/IA = lead, debe volver a evidencia original.
- **REVISIT:** benchmark local del core y, posteriormente, reimplementación local del patrón de memoria jerárquica si aporta valor medible.

### OpenBMB MiniCPM — `ACTIVE_AI_TECH_BASE`

- **SOURCE_ID:** `MINICPM-OPENBMB`
- **UPSTREAMS:** `https://github.com/OpenBMB/MiniCPM` y `https://github.com/OpenBMB/MiniCPM-V`
- **LAST_VERIFIED_REFS:** MiniCPM `310e3fce1d8378e26471577c55084ea44bd9c8c3` (2026-09-12); MiniCPM-V `6ada8e8ef5e2979670fc94406f02b87c3c7e7ee0` (2026-09-08)
- **REPOSITORY_CODE_LICENSE:** Apache-2.0. La licencia del checkpoint/modelo concreto debe verificarse antes de despliegue o redistribución.
- **PRIMARY_CANDIDATES:** MiniCPM-V 4.6 = P0 intérprete semántico visual local; MiniCPM5-2B = P1 razonamiento/agentic local; MiniCPM-o = P2 benchmark futuro.
- **DECISION:** base tecnológica de IA local para análisis e interpretación, bajo inferencia selectiva disparada por evento.
- **BOUNDARY:** no sustituye captura, detector, tracker, Entity Truth ni reglas deterministas; no VLM continuo sobre 15 cámaras; salida = `OBSERVATION_AI`, no hecho canónico.
- **BENCHMARK:** precisión semántica, alucinación, latencia, RAM/VRAM/CPU, calidad en español y trazabilidad a evidencia fuente.

### OpenViewer — `ACTIVE_ENGINEERING_REFERENCE / P1`

- **SOURCE_ID:** `OPENVIEWER`
- **REFERENCE:** `https://aiopenviewer.com/`
- **PUBLIC_RELEASES:** `https://github.com/sonnvntu/openviewer-releases`
- **LAST_VERIFIED_REF:** `fbb5d9f7ba548cc2ba6da7ce2f7dedd874ce83b6`
- **PATTERNS:** vision spine + plugins, Detection→Classification→Rule→Alert, reconnect/lifecycle, custom model boundary y acceso remoto futuro.
- **LICENSE_STATUS:** el repositorio público de releases se presenta como propietario; cualquier source pack debe verificarse individualmente antes de reutilización.
- **DECISION:** benchmark + adaptación de patrones; no dependencia de runtime ni copia de código mientras provenance/licencia no estén resueltas.

---

## 16. Residuales PR #3 reconciliados — 2026-09-18

El PR #3 fue revisado por supersedencia. Sus aportes sustantivos ya fueron absorbidos por el TES vigente salvo tres elementos explícitos, que quedan preservados aquí antes del cierre:

- **Attention Orchestrator Metrics (P0-66)** — `ACTIVE_EVALUATION / INTERNAL_CAPABILITY`. Mantener como capacidad transversal para medir reducción de carga, falsas escalaciones, tiempo a atención e investigación. No crear un sistema paralelo de prioridad.
- **DVR/NVR AI On-Demand** — `ACTIVE_EVALUATION / P0-65 SUPPORTING_PATTERN`. Analizar histórico del DVR/NVR bajo demanda, localmente, evitando indexar continuamente todos los frames. DVR/NVR sigue siendo grabador primario.
- **JetBrains Junie** — `WATCH / BENCHMARK_COMPATIBILITY` como herramienta de ingeniería. No es dependencia del runtime. Reabrir sólo si existe necesidad real de subagentes/CI-CD estandarizados y compararlo contra ECC/OpenCode/AutoClaw/Antigravity bajo el mismo flujo de verificación.

Con esta reconciliación no queda conocimiento material exclusivo en PR #3.


---

## AI Decision Engines

### System-One Models

```text
AI Decision Engines
└── System-One Models
    ├── Jev / TypeSafe AI
    ├── alternatives
    └── research
```

### Jev / TypeSafe AI — `WATCH / EXPERIMENTAL`

```text
TECHNOLOGY=Jev / TypeSafe AI
CATEGORY=System-One Decision Model
TUKEVISION_ROLE=Experimental Event Decision Engine
STATUS=WATCH / EXPERIMENTAL
PRODUCTION_READY=FALSE
CORE_DEPENDENCY=FALSE
TESTED_WITH_TUKEVISION=FALSE
PRIORITY=MEDIUM-HIGH
```

**Hipótesis TukeVision**

```text
RTSP / CCTV
→ Detection
→ Tracking
→ Event Candidates
→ Deterministic Correlation
→ Jev Event Decision Layer
→ Policy Engine
→ Investigation / Multimodal Model / Human Review
→ Evidence
```

Principio obligatorio:

```text
Jev proposes.
Policy Engine validates.
TukeVision executes only authorized actions.
Evidence confirms or refutes.
```

Nunca: `Jev → acción autónoma directa`.

**Capacidad verificada del upstream (2026-09-25):**
- TypeSafe presentó Jev el 2026-09-15 como su primer System One Model: estado de texto/JSON + preguntas tipadas → decisiones estructuradas con probabilidades/confianza.
- API pública documentada: `POST /v1/systemone` y `GET /v1/models`.
- SDK oficial Python: `typesafe-ai/typesafe-sdk-python`; SDK oficial JS/TS: `typesafe-ai/typesafe-sdk-js`.
- Vercel AI Gateway expone Jev como `typesafe-ai/jev` y permite TypeSafe client, HTTP API y AI SDK.
- Cloudflare Workers AI expone `typesafe/jev`, con Zero Data Retention indicado por Cloudflare para esa ruta.
- Jev actualmente evalúa estado textual/estructurado; no sustituye visión, tracking, ReID, OCR, VLM ni análisis temporal.
- Las cifras públicas de velocidad/costo de TypeSafe son **claims del proveedor** hasta reproducirlas con datos TukeVision.

**Casos de uso a evaluar:**
1. Event triage: `NORMAL | RELEVANT | SUSPICIOUS | NEEDS_MORE_EVIDENCE | REQUIRES_CORRELATION | REQUIRES_MULTICAMERA_CHECK | OPERATOR_REVIEW | UNKNOWN`.
2. Next-step routing: `CORRELATE_ENTITY | CHECK_PREVIOUS_CAMERA | CHECK_NEXT_CAMERA | EXTEND_TIME_WINDOW | SEARCH_TRACK_HISTORY | RUN_MULTIMODAL_ANALYSIS | OPEN_INVESTIGATION | WAIT_FOR_MORE_EVIDENCE | NO_ACTION`.
3. Multicamera correlation support usando sólo señales ya disponibles y conservando provenance.
4. Event prioritization: `LOW_PRIORITY | MEDIUM_PRIORITY | HIGH_PRIORITY | CRITICAL_REVIEW`; las reglas determinísticas siempre tienen precedencia.
5. Multimodal gate para reducir llamadas grandes.
6. Agent Monitor router sin acceso directo a capabilities.
7. Confidence gating: `AUTO_CONTINUE | SECOND_VALIDATION | MULTIMODAL_REVIEW | HUMAN_REVIEW`; umbrales sólo después de benchmark.

**Límites epistemológicos permanentes:**
```text
FACT != INFERENCE
INFERENCE != EVIDENCE
NO_EVIDENCE != NEGATIVE_EVIDENCE
UNKNOWN is valid
```

**Privacidad inicial:** metadata estructurada antes que imágenes. No enviar rostros, streams, identificadores personales ni CCTV sensible a terceros sin evaluación específica. Preferir `camera_id, timestamp, zone, object_class, track_id, trajectory, event_descriptors`.

**Laboratorio futuro:** `/experiments/jev_event_lab/`, aislado del core. No crearlo hasta autorización de implementación.

**Benchmark mínimo futuro:** comparar A) reglas determinísticas, B) Jev, C) LLM, D) multimodal, E) híbrido; medir clasificación, FP/FN, exactitud de UNKNOWN, routing/multicámara, calibración, p50/p95, costo/1000 eventos, llamadas multimodales evitadas, intervenciones humanas y escalaciones incorrectas.

**Criterio de promoción:** `WATCH → LAB → BENCHMARK → CANDIDATE → PRODUCTION`. No saltar etapas. Debe demostrar mejora operacional propia, no aumentar errores críticos, trazabilidad/auditabilidad, respeto al Policy Engine y ventaja medible frente a reglas/modelos existentes.
