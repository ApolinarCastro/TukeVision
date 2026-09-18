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
* **LAST_VERIFIED_AT**: 2026-09-13
* **DECISION**: BENCHMARK / WATCH / CONTRACT_READINESS

**Áreas**: TLS configuration, certificate/cipher policy, secure device/VMS communication, Gate 1 LAN/DVR onboarding and capability negotiation.

### SOURCE_ID=GEOVISION-LPC-2026-09
* **SOURCE_TYPE**: VENDOR_PSIRT / PRIMARY_SECURITY_SOURCE
* **PROJECT**: GeoVision GV-LPC2011/2211 Security Advisory `GV-LPC-2026-09-01`
* **CANONICAL_UPSTREAM**: `https://www.geovision.com.tw/tw/cyber_security.php`
* **LAST_VERIFIED_AT**: 2026-09-11
* **LICENSE**: N/A — vendor advisory, no code adoption
* **DECISION**: ADAPTAR / BENCHMARK / WATCH

**Áreas**: ONVIF WS-Security replay resistance, WS-Discovery input bounds, Subscribe/callback sanitization, firmware inventory, device onboarding security.

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
* **SOURCE_TYPE**: VENDOR_PRIMARY / INDUSTRY_REFERENCE
* **CANONICAL_UPSTREAM**: `https://www.marchnetworks.com/`
* **LAST_VERIFIED_REF**: `2026 Mid-Year Release` (2026-08-11)
* **LICENSE**: proprietary product/reference; no code adoption
* **DECISION**: BENCHMARK / ACTIVE_EVALUATION
* **DIRECT_PRODUCT_INTEGRATION**: NO

**Áreas**: representative-snapshot search, natural-language/image investigation, video + operational data + access + multisite correlation. Local-first y DVR/NVR primario permanecen como límites obligatorios.

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

### EXP-GEOVISION-ONVIF-SEC-001
* **PROBLEM**: Tratar discovery, autenticación y suscripciones ONVIF como una superficie confiable durante Gate 1 puede permitir replay, agotamiento/DoS o inyección a través de datos provenientes del dispositivo/red.
* **SOURCE**: GeoVision advisory `GV-LPC-2026-09-01`, publicado 2026-09-10, 23 CVE.
* **PRIMARY_PATTERNS**: `CVE-2026-88278` (WS-Security PasswordDigest replay), `CVE-2026-88277` (command injection en ONVIF Subscribe) y `CVE-2026-88287` (WS-Discovery Scopes DoS).
* **PATTERN**: DEVICE INPUT IS UNTRUSTED -> CAPABILITY/FIRMWARE INVENTORY -> BOUNDED PARSING -> TOKEN FRESHNESS/REPLAY RESISTANCE -> URI/CALLBACK SANITIZATION -> LEAST-PRIVILEGE NETWORK SEGMENT.
* **DECISION**: ADAPTAR / BENCHMARK.
* **TUKEVISION_MAPPING**: Gate 1 LAN/DVR onboarding, discovery, auth, event subscription, device security inventory.
* **BOUNDARY**: vulnerabilidades GeoVision no se extrapolan a todo ONVIF; sólo se adaptan controles defensivos vendor-neutral. No hay dependencia ni copia de código.
* **REVISIT_WHEN**: Gate 1 sea autorizado o se conozcan marca/modelo/firmware reales del DVR/cámaras.

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

### EXP-CLEARCAM-008
* **PROBLEM**: Un camino de alertas/VLM ligado a un servicio externo contradice local-first y degrada operación offline.
* **SOURCE**: `roryclear/clearcam`, refs `2f65c739...`, `3e693451...`, `078c6cc8...`, verificadas 2026-09-13.
* **PATTERN**: self-hosted event endpoint + selective Qwen summary without vendor user identity.
* **DECISION**: ADAPTAR / BENCHMARK.
* **TUKEVISION_MAPPING**: P0-62/P0-65/P0-76, event delivery y futuras notificaciones LAN.
* **BOUNDARY**: GPL-3.0; no copiar implementación. Reimplementar patrón únicamente si benchmark demuestra valor.
* **BENCHMARK**: evento local -> VLM selectivo -> endpoint LAN propio -> receipt/audit; medir latencia, offline/failure y egress de media.
* **REVISIT_WHEN**: se active slice de notificaciones/eventos o distribución LAN de resultados.

### EXP-ONVIF-TLS-002
* **PROBLEM**: Confundir aceptación de configuración TLS con activación efectiva produce falsos estados OK/FAIL y recovery prematuro.
* **SOURCE**: `onvif/specs` commit `bf3ea360e20247d68c2ae0e9c9a715a948f79d78` (2026-09-11).
* **PATTERN**: `CONFIGURATION_ACCEPTED != CONFIGURATION_ACTIVE`; usar duración estimada y estado transicional antes de verificar conectividad.
* **DECISION**: ADAPTAR / CONTRACT_READINESS / BENCHMARK.
* **TUKEVISION_MAPPING**: Gate 1 TLS onboarding, health transitions y timeout policy.
* **BOUNDARY**: RC/spec development ≠ soporte del dispositivo; no declarar conformidad sin hardware/test tool.
* **BENCHMARK**: detectar capacidad/SetupDuration, aplicar en sandbox, esperar y verificar handshake/conectividad antes de ACTIVE.
* **REVISIT_WHEN**: Gate 1 tenga hardware TLS-configurable o ONVIF publique final/test tools.

### EXP-ONVIF-WEBRTC-001
* **PROBLEM**: teardown implícito puede dejar recursos ICE/TURN/sesión retenidos en una futura pasarela WebRTC.
* **SOURCE**: `onvif/specs` commit `f1b0e50df6ad2779083686406c264806673ba076` (2026-09-11).
* **PATTERN**: close signaling explícito antes del teardown para liberar recursos remotos.
* **DECISION**: WATCH / CONTRACT_READINESS.
* **TUKEVISION_MAPPING**: WebRTC Gateway futuro; no afecta runtime actual.
* **REVISIT_WHEN**: exista requerimiento real de visualización web/remota.

### EXP-AMBIENT-002
* **PROBLEM**: `STREAM_UP/DOWN` no captura degradación visual; investigaciones dispersas y cambios de credenciales/red pueden perder contexto operativo si obligan re-onboarding.
* **SOURCE**: Ambient.ai, release de plataforma publicada 2026-08-26.
* **CAPABILITIES**: Agentic Video Walls, `degraded` camera health, credential/network updates without losing history, Case Management, Semantic/Similarity Search y stream-density optimization.
* **PATTERN**: HEALTH = connectivity + view quality; case = ordered clips + metadata + editable narrative + role/audit controls.
* **DECISION**: ADAPTAR / BENCHMARK; no producto/cloud dependency.
* **TUKEVISION_MAPPING**: Gate 0C health/attention; P0-59/P0-65/P0-66; Gate 1 maintenance.
* **BOUNDARY**: métricas del proveedor son claims, no evidencia TukeVision; preservar local-first y DVR/NVR primario.
* **BENCHMARK**: `DEGRADED_VIEW` independiente de `STREAM_DOWN` + case local cronológico con clips/metadata/audit.
* **REVISIT_WHEN**: se reabra observabilidad Gate 0C o slice de investigación/case management.

### EXP-MARCH-001
* **PROBLEM**: La investigación sobre histórico puede volverse costosa si intenta analizar continuamente todos los frames, y los eventos de acceso pueden quedar separados del video que los valida.
* **SOURCE**: March Networks `2026 Mid-Year Release`, publicada 2026-08-11 en el upstream oficial.
* **CAPABILITIES**: Searchlight AI, AI Smart Search sobre snapshots a intervalos configurables, búsqueda por texto/imagen, búsqueda expandida de rostro/matrícula y correlación C•CURE access→video.
* **PATTERN**: `REPRESENTATIVE_SNAPSHOTS -> SEARCHABLE_INDEX -> QUERY -> CANDIDATE_RESULT -> SOURCE_VIDEO/EVIDENCE`; para acceso: `ACCESS_EVENT -> RELATED_VIDEO -> HUMAN_VALIDATION`.
* **DECISION**: BENCHMARK / ADAPTAR PATTERN; no producto/cloud dependency.
* **TUKEVISION_MAPPING**: P0-65 investigación, `AccessObservation`, agregador/correlación multisitio y Evidence First.
* **BOUNDARY**: March Networks es producto propietario/cloud-capable; TukeVision no adopta Searchlight Cloud ni reemplaza el DVR/NVR primario. Resultado IA sigue siendo lead, no hecho.
* **BENCHMARK**: sobre video local/DVR, comparar índice de snapshots representativos vs. procesamiento continuo en recall útil, latencia, CPU/RAM y trazabilidad al clip/frame fuente; validar access-event→video sin identidad inferida.
* **REVISIT_WHEN**: se active el slice P0-65 de investigación histórica o el conector ACCESS/correlación.

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

---

## EXP-CLEARCAM-009 — Local Qwen without provider identity dependency
- SOURCE_VERIFIED: YES — `roryclear/clearcam`
- VERSION_OR_REF_VERIFIED: YES — `84b8740a6c5fb103d24714fdc8d9af997192115e`, 2026-09-16
- LICENSE_VERIFIED: YES — GPL-3.0
- CAPABILITIES_EXTRACTED: YES — selective local Qwen path can operate without ClearCam user identity/key dependency
- TUKEVISION_MAPPING: P0-64 / P0-65 / P0-76; local-first selective VLM and source-linked investigation
- ADOPTION_BOUNDARY: benchmark and independently reimplement pattern only; no direct GPL core copy; no product adoption
- REVISIT_CONDITION: benchmark demonstrates useful source-linked output with zero media egress, bounded latency/resources and graceful AI failure
- EXPERIENCE_RECORD: YES
- CLASSIFICATION: ADAPTAR / BENCHMARK
- RISK: accidental SaaS/identity coupling or GPL contamination
- MINIMUM_BENCHMARK: real event -> local Qwen -> structured result -> source evidence/LAN; verify no media egress
- NEXT_GATE: P0-64/P0-65 selective investigation benchmark

## EXP-FRIGATE-2026-09-18-ANNOTATED-GENAI-REVIEW — Representative annotated evidence
- SOURCE_VERIFIED: YES — `blakeblackshear/frigate`
- VERSION_OR_REF_VERIFIED: YES — `eccd10cd941a4abdce0cd6ae2aa6b274f7fdbafe` (2026-09-17); related lifecycle refs `64d6366a`, `10a0d5ea`; audio ref `33407396`
- LICENSE_VERIFIED: YES — MIT
- CAPABILITIES_EXTRACTED: YES — annotated representative frames for GenAI review; exact zone-reference updates; explicit live transport handling; optional GenAI audio transcription
- TUKEVISION_MAPPING: Gate 0C, P0-64 Evidence Selector, P0-65 Semantic Investigation, provenance/reference integrity
- ADOPTION_BOUNDARY: patterns/benchmark only; no Frigate product adoption; no second NVR; audio remains WATCH/RESERVE
- REVISIT_CONDITION: same-evidence benchmark demonstrates measurable investigation gain without source mutation or unsupported claims
- EXPERIENCE_RECORD: YES
- CLASSIFICATION: ADAPTAR / BENCHMARK
- RISK: annotations can bias model output or be mistaken for original evidence
- MINIMUM_BENCHMARK: clean vs annotated representative frames over identical real evidence; measure utility, hallucination/unsupported claims, latency, CPU/RAM and source traceability; `ORIGINAL_EVIDENCE_MUTATED=0`
- NEXT_GATE: P0-64/P0-65 benchmark before any new implementation

## EXP-SERVAL-001 — Bounded process/memory lifecycle
- SOURCE_VERIFIED: YES — `Flickersoft/serval`
- VERSION_OR_REF_VERIFIED: YES — v0.2.5 / `596613ccc7b97fe471b09a6bd085c52f57d9f733`, 2026-09-06
- LICENSE_VERIFIED: YES — AGPL-3.0-or-later
- CAPABILITIES_EXTRACTED: YES — upstream fix specifically addresses process/memory leakage in a local AI/NVR-oriented runtime
- TUKEVISION_MAPPING: resource hardening, worker lifecycle and graceful degradation
- ADOPTION_BOUNDARY: benchmark pattern only; no AGPL code copy into core; no Serval/NVR adoption
- REVISIT_CONDITION: TukeVision evidence shows matching resource leak/orphan process defect or the benchmark proves a reusable lifecycle pattern
- EXPERIENCE_RECORD: YES
- CLASSIFICATION: BENCHMARK / ADAPTAR / WATCH
- RISK: early-project maturity plus AGPL boundary and NVR-role overlap
- MINIMUM_BENCHMARK: >=1800s local load with RSS/process/thread/queue telemetry + induced AI-worker failure/restart while video continues
- NEXT_GATE: resource-hardening benchmark only when matching defect is evidenced

---

### SOURCE_ID=QWEN-MM-PLUGINS
* **SOURCE_TYPE**: PUBLIC_GITHUB_PROJECT
* **PROJECT**: `QwenLM/Qwen-MM-Plugins`
* **LAST_VERIFIED_REF**: `fac5c9e307737afadd15bacda0314870e886864c` (2026-09-18)
* **LICENSE**: Apache-2.0
* **DECISION**: ACTIVE_ENGINEERING_CANDIDATE / BENCHMARK
* **DIRECT_RUNTIME_DEPENDENCY**: NO

**Áreas**: multimodal agent tools, local media inspection, Skill+MCP boundaries, hierarchical long-video memory, event/entity/OCR/time retrieval.

### SOURCE_ID=MINICPM-OPENBMB
* **SOURCE_TYPE**: PUBLIC_GITHUB_PROJECT
* **PROJECTS**: `OpenBMB/MiniCPM`, `OpenBMB/MiniCPM-V`
* **LAST_VERIFIED_REFS**: `310e3fce1d8378e26471577c55084ea44bd9c8c3`; `6ada8e8ef5e2979670fc94406f02b87c3c7e7ee0`
* **REPOSITORY_CODE_LICENSE**: Apache-2.0
* **MODEL_LICENSE_RULE**: verificar el checkpoint/model card exacto antes de despliegue o redistribución.
* **DECISION**: ACTIVE_AI_TECH_BASE / SELECTIVE_BENCHMARK

**Áreas**: MiniCPM-V como intérprete visual semántico local; MiniCPM5-2B como reasoning/agentic layer; inferencia selectiva y local-first.

### SOURCE_ID=OPENVIEWER
* **SOURCE_TYPE**: PRODUCT / ARCHITECTURE_REFERENCE
* **REFERENCE**: `https://aiopenviewer.com/`
* **PUBLIC_RELEASES**: `sonnvntu/openviewer-releases`
* **LAST_VERIFIED_REF**: `fbb5d9f7ba548cc2ba6da7ce2f7dedd874ce83b6`
* **LICENSE_STATUS**: public releases repository proprietary; source packs require individual verification.
* **DECISION**: ACTIVE_ENGINEERING_REFERENCE / PATTERN_BENCHMARK
* **DIRECT_CODE_REUSE**: BLOCKED_PENDING_LICENSE

**Áreas**: vision spine + plugins, model/plugin boundary, reconnect lifecycle, Detection→Classification→Rule→Alert, future remote-access patterns.

### EXP-QWEN-MM-001 — Multimodal engineering layer and bounded video memory
* **PROBLEM**: agentes de ingeniería y futura investigación multimodal requieren inspección de medios y memoria de video sin crear herramientas ad-hoc por cada ejecución.
* **PATTERN**: local multimodal tools + Skill/MCP boundary + hierarchical video memory -> retrieve candidate interval -> return to original video for verification.
* **DECISION**: BENCHMARK / ENGINEERING_TOOL / ARCHITECTURAL_PATTERN.
* **TUKEVISION_MAPPING**: Evidence inspection, P0-64, P0-65, agent tooling.
* **BOUNDARY**: memoria aproximada no es Entity Truth; no customer CCTV cloud upload.
* **REVISIT_WHEN**: benchmark local demuestre reducción de trabajo manual y buena trazabilidad a evidencia fuente.

### EXP-MINICPM-001 — Selective local semantic interpretation
* **PROBLEM**: comprender actividad/contexto más allá de detección/tracking sin ejecutar un VLM pesado 24/7 sobre todos los canales.
* **PATTERN**: event candidate -> keyframe/short clip -> local MiniCPM-V -> structured semantic observation -> deterministic validation -> Situation/Evidence.
* **DECISION**: ACTIVE_AI_TECH_BASE / BENCHMARK.
* **TUKEVISION_MAPPING**: P0-64 Evidence Selector, P0-65 Semantic Investigation, Gate 5 analysis/interpretation.
* **BOUNDARY**: `OBSERVATION_AI != ENTITY_TRUTH`; detector/tracker/temporal engine remain authoritative for their domains.
* **BENCHMARK**: semantic accuracy, hallucination, latency, RAM/VRAM/CPU, Spanish output quality, evidence traceability.

### EXP-OPENVIEWER-001 — Vision spine and plugin boundary
* **PROBLEM**: riesgo de acoplar modelos/IA al pipeline central y convertir cada nueva capacidad en un segundo sistema.
* **PATTERN**: stable vision spine -> plugins -> Detection→Classification→Rule→Alert, with reconnect/lifecycle isolated from model plugins.
* **DECISION**: ADAPT_PATTERN / BENCHMARK_REFERENCE.
* **TUKEVISION_MAPPING**: future semantic plugin boundary, lifecycle/reconnect and remote-access design.
* **BOUNDARY**: no code adoption while source-pack provenance/license remains unresolved.
