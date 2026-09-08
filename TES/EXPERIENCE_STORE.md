# TukeVision Experience Store (TES)

Este documento registra los aprendizajes operacionales y referencias arquitectónicas extraídas del uso en el mundo real, alineados a los principios de resiliencia y adaptabilidad (P0-77: Failure -> Experience).

## Registro de Fuentes

### SOURCE_ID=CLEARCAM-RORYCLEAR
* **SOURCE_TYPE**: PUBLIC_GITHUB_PROJECT
* **PROJECT**: `roryclear/clearcam`
* **LICENSE**: GPL-3.0
* **MATURITY**: ACTIVE_PRODUCT_ENGINEERING
* **DECISION**: ADAPT_BENCHMARK
* **DIRECT_CODE_REUSE**: PROHIBITED

**Áreas de experiencia relevantes**: RTSP, FFmpeg lifecycle, stream recovery, decoder supervision, event recording, playback, selective inference, tracking, semantic/event search, local VLM, mobile notifications, real-world camera interoperability.

---

## Experience Cards

### EXP-CLEARCAM-001
* **PROBLEM**: Premature stream restart. (Se reinician decodificadores que simplemente estaban inicializando y no habían tenido tiempo de entregar el primer frame).
* **PATTERN**: Startup grace before recovery.
* **DECISION**: ADAPTED_POST_F12 (Añadido `startup_grace_seconds` al `SourceManager`, verificado con tests automatizados).

### EXP-CLEARCAM-002
* **PROBLEM**: Repeated frame-read failures. (Cámaras del mundo real pierden frames aislados. Reiniciar el pipeline entero por un frame perdido genera latencia e inestabilidad).
* **PATTERN**: Consecutive failure threshold.
* **DECISION**: ADAPTED_POST_F12 (Añadido `consecutive_failure_threshold` antes de desencadenar recuperación).

### EXP-CLEARCAM-003
* **PROBLEM**: Duplicate FFmpeg processes during recovery. (*Restart storms* causados por crear decodificadores nuevos sin asegurar la muerte de los antiguos).
* **PATTERN**: Single-owner decoder lifecycle.
* **DECISION**: ADAPTED_POST_F12 (Implementado semáforo de reconexión y espera de cleanup del hilo antiguo antes de iniciar nueva generación).

### EXP-CLEARCAM-004
* **PROBLEM**: Recovery declared before real video returns. (Creer que el stream volvió solo porque FFmpeg arrancó, aunque la cámara no envíe datos).
* **PATTERN**: First-frame confirmation after restart.
* **DECISION**: ADAPTED_POST_F12 (La recuperación exige confirmación de recepción física de frame validada en el worker loop).

### EXP-CLEARCAM-005
* **PROBLEM**: High compute from continuous heavy inference.
* **PATTERN**: Selective/cascade inference (No aplicar modelos grandes 24/7).
* **DECISION**: ALREADY_ALIGNED (P0-62 / P0-76).

### EXP-CLEARCAM-006
* **PROBLEM**: Historical event retrieval (Dificultad de investigar en terabytes de video crudo).
* **PATTERN**: Indexed evidence + semantic search.
* **DECISION**: ADAPT_TO_P0-65 (Búsqueda semántica usando metadatos y VLM ligero).

### EXP-AGENTIC-VIDEO-001
* **PROBLEM**: Expensive/static long-video processing.
* **PATTERN**: Goal-directed temporal search + dynamic re-sampling + selective high-FPS inspection.
* **DECISION**: ADAPT_PATTERN (BENCHMARK_FUTURE).
* **TUKEVISION_MAPPING**: P0-64, P0-65, P0-62, P0-76.
* **SOURCE**: Google Agentic Video Understanding (VENDOR_TECHNICAL_REFERENCE).
* **NOTE**: External processing pattern only. No customer video to cloud without future explicit policy. Vendor percentages are VENDOR_BENCHMARK_CLAIM.

### EXP-PURPOSE-BOUND-INVESTIGATION-001
* **PROBLEM**: AI free search in CCTV can become an operational and privacy risk if users broaden scope arbitrarily.
* **PATTERN**: PURPOSE -> CASE -> PERMISSION -> SCOPE -> QUERY -> RESULTS (LEADS) -> EVIDENCE -> HUMAN VALIDATION -> AUDIT.
* **DECISION**: ADOPT_GOVERNANCE_PATTERN.
* **TUKEVISION_MAPPING**: P0-59, P0-65, P0-66, P1-69.
* **NOTE**: AI search result is a CANDIDATE_LEAD, not a fact or guilt. Each search must log investigation_id, operator_id, case_reference, purpose, scope, policy_version, overrides, etc.

### EXP-ONVIF-MEDIA-SIGNING-001
* **PROBLEM**: Need for standardized Edge AI origin verification and evidence integrity.
* **PATTERN**: Cryptographic signing of H.264/H.265 in SEI NAL units directly on edge hardware.
* **DECISION**: CONTRACT_READY / SANDBOX_BENCHMARK_READY.
* **SOURCE**: onvif/media-signing-framework (OFFICIAL_UPSTREAM).
* **LICENSE**: MIT.
* **NOTE**: Signing/validation code and examples are present in the official MIT repo. Hardware validation remains PENDING_HARDWARE. No TukeVision runtime implementation is marked without physical testing.
