# TukeVision Experience Store (TES)

Este documento registra aprendizajes operacionales y referencias arquitectónicas extraídas del uso en el mundo real, alineados a resiliencia, adaptabilidad y `Failure -> Experience`.

Desde 2026-09-08 el Experience Store es **fuente obligatoria de consulta antes de diseñar una solución nueva**. Ver `ACTIVE_EVALUATION_PROTOCOL.md` y `KNOWLEDGE_SOURCE_INDEX.md`.

## Registro de Fuentes

### SOURCE_ID=CLEARCAM-RORYCLEAR
* **SOURCE_TYPE**: PUBLIC_GITHUB_PROJECT
* **PROJECT**: `roryclear/clearcam`
* **LICENSE**: GPL-3.0
* **MATURITY**: ACTIVE_PRODUCT_ENGINEERING
* **DECISION**: ACTIVE_EVALUATION + ADAPT_BENCHMARK
* **DIRECT_CODE_REUSE**: PROHIBITED
* **PRIORITY**: HIGH

**Áreas de experiencia relevantes**: RTSP, FFmpeg lifecycle, stream recovery, decoder supervision, event recording, playback/freshness, selective inference, tracking, semantic/event search, local VLM, mobile notifications, real-world camera interoperability.

### SOURCE_ID=FRIGATE-OSS
* **SOURCE_TYPE**: PUBLIC_GITHUB_PROJECT
* **PROJECT**: `blakeblackshear/frigate`
* **DECISION**: ACTIVE_EVALUATION / BENCHMARK_REFERENCE
* **DIRECT_PRODUCT_INTEGRATION**: NO

**Áreas**: multicamera ingestion, ffmpeg/go2rtc lifecycle, hardware acceleration, events, search, recovery, storage, health. La evaluación debe extraer patrones sin convertir TukeVision en segundo NVR.

### SOURCE_ID=SHINOBI-GITLAB
* **SOURCE_TYPE**: PUBLIC_GITLAB_UPSTREAM
* **PROJECT**: `Shinobi-Systems/Shinobi`
* **CANONICAL_UPSTREAM**: `https://gitlab.com/Shinobi-Systems/Shinobi`
* **LAST_VERIFIED_REF**: `c4cb68d0` (2026-08-20)
* **LICENSE**: Shinobi Open Source Software License Agreement (EULA propia; condiciones comerciales aplican)
* **DECISION**: BENCHMARK / ACTIVE_EVALUATION
* **DIRECT_CODE_REUSE**: NO

**Áreas**: live-grid lifecycle, next/previous monitor navigation, substream loading/switching, ONVIF scanning, RTSP transport options, monitor startup queueing y hardening de auth/permisos.

### SOURCE_ID=ONVIF-MEDIA-SIGNING
* **SOURCE_TYPE**: OFFICIAL_GITHUB_UPSTREAM
* **PROJECT**: `onvif/media-signing-framework`
* **LICENSE**: MIT
* **DECISION**: CONTRACT_READY / ACTIVE_SANDBOX_BENCHMARK

### SOURCE_ID=ONVIF-TLS-CONFIG-2
* **SOURCE_TYPE**: OFFICIAL_STANDARD + OFFICIAL_GITHUB_DEVELOPMENT
* **PROJECT**: ONVIF TLS Configuration Add-on 2.0 Release Candidate
* **CANONICAL_UPSTREAM**: ONVIF
* **DEVELOPMENT_REPO**: `onvif/specs`
* **LAST_VERIFIED_AT**: 2026-09-10
* **DECISION**: BENCHMARK / WATCH / CONTRACT_READINESS

**Áreas**: TLS configuration, certificate/cipher policy, secure device/VMS communication, Gate 1 LAN/DVR onboarding and capability negotiation.

### SOURCE_ID=NCSC-AGENTIC-SECURITY
* **SOURCE_TYPE**: AUTHORITY_GUIDANCE
* **DECISION**: ACTIVE_EVALUATION / ADAPT_GOVERNANCE

**Áreas**: minimum privilege, deny-by-default tools, isolation, audit, human control, safe mode.

### SOURCE_ID=ALOCITY-MERCURY-PATTERN
* **SOURCE_TYPE**: INDUSTRY_REFERENCE
* **DECISION**: ACTIVE_EVALUATION / CONTRACT_PATTERN

**Áreas**: access + video + visitor/location context + AI, edge-enriched access events, vendor-neutral PACS adapters.

### SOURCE_ID=FLOCK-FREEFORM-GOVERNANCE
* **SOURCE_TYPE**: INDUSTRY/RESEARCH_EXPERIENCE
* **DECISION**: ACTIVE_EVALUATION / GOVERNANCE_PATTERN

**Áreas**: purpose-bound search, case reference, permission, camera/time scope, anomalous-use audit, AI result as candidate lead.

### SOURCE_ID=AVIGILON-ENTERPRISE
* **SOURCE_TYPE**: INDUSTRY_REFERENCE
* **DECISION**: ACTIVE_EVALUATION

**Áreas**: selective attention, appearance/search patterns, multisite, access+video, privacy, PTZ governance.

### SOURCE_ID=MARCH-NETWORKS
* **SOURCE_TYPE**: INDUSTRY_REFERENCE
* **DECISION**: ACTIVE_EVALUATION

**Áreas**: video + operational data + access + multisite → investigation.

### SOURCE_ID=HIFOCUS-INTELLISEEK
* **SOURCE_TYPE**: INDUSTRY_REFERENCE
* **DECISION**: ADAPTED_PARTIAL / ACTIVE_EVALUATION

**Áreas**: structured search, local/on-demand historical analysis, avoiding full-frame permanent indexing.

### SOURCE_ID=MAGI-ARCHIVE
* **SOURCE_TYPE**: DISCOVERY_LAYER
* **DECISION**: DISCOVER_ONLY

**Regla**: MAGI descubre → fuente original verifica → benchmark decide.

---

## Experience Cards

### EXP-CLEARCAM-001
* **PROBLEM**: Premature stream restart. Se reinician decodificadores que simplemente estaban inicializando y no habían tenido tiempo de entregar el primer frame.
* **PATTERN**: Startup grace before recovery.
* **DECISION**: ADAPTED_POST_F12 (Añadido `startup_grace_seconds` al `SourceManager`, verificado con tests automatizados).

### EXP-CLEARCAM-002
* **PROBLEM**: Repeated frame-read failures. Cámaras del mundo real pierden frames aislados; reiniciar el pipeline entero por un frame perdido genera latencia e inestabilidad.
* **PATTERN**: Consecutive failure threshold.
* **DECISION**: ADAPTED_POST_F12 (Añadido `consecutive_failure_threshold` antes de desencadenar recuperación).

### EXP-CLEARCAM-003
* **PROBLEM**: Duplicate FFmpeg processes during recovery. Restart storms causados por crear decodificadores nuevos sin asegurar la muerte de los antiguos.
* **PATTERN**: Single-owner decoder lifecycle.
* **DECISION**: ADAPTED_POST_F12 (Implementado semáforo de reconexión y espera de cleanup del hilo antiguo antes de iniciar nueva generación).

### EXP-CLEARCAM-004
* **PROBLEM**: Recovery declared before real video returns. Creer que el stream volvió sólo porque FFmpeg arrancó, aunque la cámara no envíe datos.
* **PATTERN**: First-frame confirmation after restart.
* **DECISION**: ADAPTED_POST_F12 (La recuperación exige confirmación de recepción física de frame validada en el worker loop).

### EXP-CLEARCAM-005
* **PROBLEM**: High compute from continuous heavy inference.
* **PATTERN**: Selective/cascade inference; no aplicar modelos grandes 24/7.
* **DECISION**: ALREADY_ALIGNED (P0-62 / P0-76).

### EXP-CLEARCAM-006
* **PROBLEM**: Historical event retrieval; dificultad de investigar en terabytes de video crudo.
* **PATTERN**: Indexed evidence + semantic search.
* **DECISION**: ADAPT_TO_P0-65.

### EXP-CLEARCAM-007
* **PROBLEM**: ClearCam contiene más experiencia útil que los cuatro patrones RTSP ya adaptados, pero permanecía tratado principalmente como referencia TES.
* **PATTERN**: `REFERENCE -> ACTIVE_ENGINEERING_CANDIDATE -> BENCHMARK -> DECISION`.
* **DECISION**: ACTIVE_EVALUATION_HIGH.
* **TARGETS**: playback/freshness, wait-for-frame/selective inference, stationary/recovery tracking, event/similar-image search.
* **LICENSE_BOUNDARY**: GPL-3.0; estudio/benchmark/reimplementación independiente permitidos bajo revisión, copia directa al core prohibida por política TukeVision.

### EXP-FRIGATE-001
* **PROBLEM**: Riesgo de reinventar lifecycle multicámara, recovery, health, aceleración y event search ya tratados por un OSS CCTV maduro.
* **PATTERN**: auditar arquitectura madura antes de construir equivalente.
* **DECISION**: ACTIVE_BENCHMARK_REFERENCE.
* **BOUNDARY**: DVR/NVR sigue siendo grabador primario; no integrar Frigate como producto.

### EXP-SHINOBI-001
* **PROBLEM**: Gate 0C mostró regresiones físicas en Grid, navegación Anterior/Siguiente y transición de substream al intentar optimizar la UI local.
* **PATTERN**: revisar lifecycle de live-grid, navegación de monitor y carga de substream en un VMS real antes de rediseñar el flujo propio.
* **EVIDENCE_UPSTREAM**: commit `c4cb68d0` corrige Live Grid render; MR !548 contiene fixes de next/previous monitor navigation y substream loading; MR !557 endurece auth/permisos y rutas.
* **DECISION**: BENCHMARK / ADAPT_PATTERN_ONLY.
* **BOUNDARY**: no dependencia Shinobi, no copia de código; EULA propia con condiciones comerciales.
* **TUKEVISION_MAPPING**: Gate 0C UI lifecycle/focus navigation; Gate 1 ONVIF/LAN onboarding and security review.
* **REVISIT_WHEN**: antes de un nuevo diseño Gate 0C desde baseline estable o al definir Gate 1.

### EXP-AGENTIC-VIDEO-001
* **PROBLEM**: Expensive/static long-video processing.
* **PATTERN**: Goal-directed temporal search + dynamic re-sampling + selective high-FPS inspection.
* **DECISION**: ADAPT_PATTERN / ACTIVE_CONDITIONAL_BENCHMARK.
* **TUKEVISION_MAPPING**: P0-64, P0-65, P0-62, P0-76.
* **NOTE**: External processing pattern only. No customer video to cloud without future explicit policy. Vendor percentages remain vendor claims until own benchmark.

### EXP-PURPOSE-BOUND-INVESTIGATION-001
* **PROBLEM**: AI free search in CCTV can become an operational and privacy risk if users broaden scope arbitrarily.
* **PATTERN**: PURPOSE -> CASE -> PERMISSION -> SCOPE -> QUERY -> RESULTS (LEADS) -> EVIDENCE -> HUMAN VALIDATION -> AUDIT.
* **DECISION**: ADOPT_GOVERNANCE_PATTERN.
* **TUKEVISION_MAPPING**: P0-59, P0-65, P0-66, P1-69.
* **NOTE**: AI search result is a CANDIDATE_LEAD, not a fact or guilt.

### EXP-ONVIF-MEDIA-SIGNING-001
* **PROBLEM**: Need for standardized Edge AI origin verification and evidence integrity.
* **PATTERN**: Cryptographic signing of H.264/H.265 directly on edge hardware and downstream verification.
* **DECISION**: CONTRACT_READY / ACTIVE_SANDBOX_BENCHMARK.
* **SOURCE**: `onvif/media-signing-framework` (OFFICIAL_UPSTREAM).
* **LICENSE**: MIT.
* **NOTE**: Hardware validation remains PENDING_HARDWARE. No runtime certification without physical evidence.

### EXP-ONVIF-TLS-001
* **PROBLEM**: Gate 1 LAN/DVR onboarding puede introducir credenciales/transporte inseguros o asumir capacidades TLS inexistentes si se diseña sólo alrededor de RTSP/ONVIF básico.
* **PATTERN**: capability-driven TLS configuration con política criptográfica versionable y evidencia explícita de soporte real del dispositivo.
* **SOURCE**: ONVIF TLS Configuration Add-on 2.0 Release Candidate, publicada 2026-09-09.
* **DECISION**: BENCHMARK / CONTRACT_READINESS / WATCH.
* **TUKEVISION_MAPPING**: discovery/onboarding DVR, credential transport, device capability inventory, future ONVIF conformance readiness.
* **BOUNDARY**: RC ≠ especificación final; no declarar conformidad ni forzar feature sobre hardware que no la soporte.
* **REVISIT_WHEN**: Gate 1 pruebe hardware real o ONVIF publique final/test tools aplicables.

### EXP-NCSC-AGENT-001
* **PROBLEM**: Capacidad del modelo puede superar permisos operacionales del agente.
* **PATTERN**: minimum privilege + deny-by-default tools + isolation + audit + proportional human control + safe mode.
* **DECISION**: ADAPT_GOVERNANCE / ACTIVE.
* **TUKEVISION_MAPPING**: autonomy controller, safe mode, tool permissions, audit.

### EXP-ACCESS-CORRELATION-001
* **PROBLEM**: Video aislado carece de contexto físico de acceso, puerta, credencial y visitante.
* **PATTERN**: `ACCESS EVENT + VIDEO + LOCATION + TIME -> CORRELATION -> SITUATION`.
* **DECISION**: CONTRACT_READINESS / ACTIVE_EVALUATION.
* **RULES**: `ACCESS_EVENT != VISUAL_CONFIRMATION`; `CREDENTIAL_ASSERTION != PERSON_IDENTITY`.
* **BOUNDARY**: no Mercury/Alocity module; connector neutral de proveedor.

### EXP-INTELLISEEK-001
* **PROBLEM**: Indexar cada frame del histórico CCTV es caro e innecesario.
* **PATTERN**: lightweight representative index + local historical analysis on demand.
* **DECISION**: ADAPT_TO_P0-65 / ACTIVE_EVALUATION.
* **BOUNDARY**: DVR/NVR conserva histórico primario.

### EXP-ENTERPRISE-CONVERGENCE-001
* **PROBLEM**: Riesgo de diseñar por separado video, access, multisite e investigación.
* **SOURCES**: Avigilon + March Networks + Alocity/Mercury patterns.
* **PATTERN**: normalized observations -> correlation -> situation -> investigation/operator.
* **DECISION**: ACTIVE_PATTERN_RECONCILIATION.

### EXP-TRACKER-BENCHMARK-001
* **PROBLEM**: Sustituir tracker por moda puede introducir regresiones.
* **PATTERN**: benchmark only after proven defect.
* **CANDIDATES**: OC-SORT, CoTracker, TAPNet, Trace Anything.
* **DECISION**: CONDITIONAL_BENCHMARK.

### EXP-LOCAL-VLM-001
* **PROBLEM**: Investigación semántica puede requerir comprensión visual más allá de filtros estructurados.
* **PATTERN**: evidence selector -> local small VLM -> inference, only on demand.
* **CANDIDATES**: SmolVLM, FastVLM, Qwen3-VL.
* **DECISION**: WATCH / CONDITIONAL_BENCHMARK.
* **RULE**: no continuous VLM; no external customer-video upload.

---

## Regla Failure -> Experience

Toda falla material debe producir, cuando corresponda:

```text
FAILURE
→ ROOT_CAUSE
→ CORRECTION
→ REGRESSION_TEST
→ EXPERIENCE_RECORD
→ RELATED_SOURCES
→ LESSON
```

Antes de una corrección nueva debe ejecutarse una búsqueda en este documento y en `KNOWLEDGE_SOURCE_INDEX.md`.
