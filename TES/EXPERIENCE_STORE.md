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
