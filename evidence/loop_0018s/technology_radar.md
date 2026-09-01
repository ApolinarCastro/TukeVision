# TECHNOLOGY_RADAR — LOOP-0018S

**LOOP:** 0018S · **Fecha:** 2026-08-16 · **Modo:** SOLO LECTURA (inventario; sin adopción)
**Fuente:** worker_92 Entregable 1 (verificado S4: 34 filas; decisión 0 PENDING).
**Convención:** [HECHO] = archivos/logs/informes verificados; [INFERENCIA] = interpretación razonada. Credenciales redactadas. Canario de trazado RTSP: ausente (no se imprime el literal).
**Nota S4:** el conteo correcto de decisiones del radar es **7 ALREADY_COVERED / 4 PATTERN_REUSE_ONLY / 10 EXTENSION_CANDIDATE / 10 DEFER / 3 REJECT = 34** (la síntesis original rotulaba 9 EXTENSION_CANDIDATE pero enumeraba 10; corregido).

---

## 1. Contexto de decisión: qué es "BASE" hoy (16-08-2026) [HECHO]

- **Núcleo certificado (SPEC-0001 + E-01 COMPAT, commit `ccacb3d`)**: pipeline unicámara FUENTE→CAPTURA→DETECCIÓN→TRACKING→OBSERVACIÓN→EVENTO→REGLA→RIESGO→ALERTA→EVIDENCIA→REVISIÓN HUMANA.
- **Stack activo**: Python 3.12, Ultralytics 8.4.115 + YOLO11n (CPU, clase persona, 640px, 54.5 ms/frame medido LOOP-0018N), trackers 2.5.0.post0 (ByteTrack), Supervision 0.29.1 (solo `sv.Detections`), OpenCV 5.0.0.93, Tkinter 8.6, JSON local.
- **Multicámara 4 física CERTIFICADA** (LOOP-0018O, `MULTICAMERA4_PHYSICAL_CERTIFIED`): SourceManager, aislamiento por cámara, colas acotadas, 0 stalls en 300 s, 0 dependencias nuevas.
- **Observation Layer mínima** (LOOP-0018P, DEC-0034): observación canónica inmutable + política QUALITY/BALANCED/ECONOMY.
- **Inferencia selectiva + eventos** (LOOP-0018Q, DEC-0035): contrato `InferenceEngine` (Deterministic/Yolo), `InferenceEvent` canónico trazable.
- **Tracking temporal LOCAL** (LOOP-0018R, DEC-0036): `track_id` = identidad temporal y local por cámara; prohibida correlación cross-cámara y biometría (DEC-0013/0019).
- **Regresión BASE**: 359/359 OK; `NEW_DEPENDENCIES=0` en loops 0018N–R.
- **Riesgo nativo abierto [HECHO]**: double free `0xc0000374` en `opencv_videoio_ffmpeg500_64.dll` (v2024.11.0.0) en el path de reconexión RTSP — 3/3 dumps, call-site SIN RESOLVER (LOOP-0018G/H; LOOP-0018I no lo reprodujo bajo instrumentación).
- **Portable** = laboratorio; E-02 (trajectory/FlowCounter), E-03 (ReID), E-04 (grid UI), E-05 (quality_engine) solo EXPERIMENTAL.

**Reglas de gobierno aplicadas [HECHO]**: regla 22 ("toda herramienta nueva debe resolver una necesidad aprobada que las actuales no cubran"), `TECHNOLOGY_STACK_MVP.md` (lista "no se instalarán"), DEC-0023/0028/0029, DEC-0013/0019/0036 (privacidad/identidad), DEC-0034/35/36 (producto mínimo).

---

## 2. Inventario de tecnologías/experiencias externas (34) — estado del estudio

| # | Tecnología | Qué se estudió | Dónde está documentado | Aporte potencial | Estado del estudio |
|---|---|---|---|---|---|
| 1 | OpenCV 5.0.0.93 | Captura, zona poligonal, anotación, evidencia, conversión UI; comportamiento RTSP (open-timeout OK, read-timeout rompe open, `read()` bloquea, `release()` desbloquea); double free `0xc0000374` | `TES/09_Resources/TECHNOLOGY_AND_REFERENCE_REGISTRY.md`; `src/capture/*`, `src/context/zone.py`, `src/evidence/store.py`, `src/app/pipeline.py`, `src/ui/tk_view.py`; `TukeVision-portable/LOOP-0018B/D/E/G/H/I*.md` | Núcleo activo y certificado; mitigar el riesgo nativo de reconexión | **ACTIVE — CERTIFICADO** (SPEC-0001, E-01); riesgo SIN RESOLVER |
| 2 | Ultralytics 8.4.115 + YOLO11n | Detección de personas (clase 0, conf 0.35, imgsz 640, CPU); 54.5 ms/frame; `model.embed()` 256-d (9.9–20.3 ms/crop) para ReID E-03; backend real de inferencia selectiva | `TES/09_Resources/...`; `TES/04_Decisions/DEC-0023`; `src/detection/person_detector.py`, `src/inference/engines.py`; `evidence/loop_0018n/resource_budget.md` | Detección activa; extensiones: filtro maniquíes, detección de productos, backbone apariencia (E-03, bloqueado) | **ACTIVE — CERTIFICADO** (DEC-0023); AGPL-3.0 aceptada |
| 3 | ByteTrack (trackers 2.5.0.post0) | Ciclo de vida de `track_id` (efímero, buffer 30 frames ≈ 2–4 s, sin apariencia); causa raíz del doble conteo; 1 tracker por cámara | `TES/09_Resources/...`; `src/tracking/person_tracker.py`; `.cluster/tukevision-reid-20260814/worker_30_tracking.md`; `TES/04_Decisions/DEC-0036` | Ya activo; el gap (re-identificación) se cubre sin biometría (src/temporal/) + ventanas de re-entrada | **ACTIVE — CERTIFICADO** |
| 4 | Supervision 0.29.1 | Uso real: solo `sv.Detections`; zonas/anotación = OpenCV; sin ReID/embedding en el paquete | `TES/09_Resources/...`; `src/tracking/person_tracker.py`; `.cluster/tukevision-reid-20260814/worker_31_reid.md` | Ninguno adicional; mantener uso mínimo | **ACTIVE (uso parcial) — CERTIFICADO** |
| 5 | SmartPSS Lite (Dahua) — ingeniería inversa | Perfil Qt5, SDK DCM/PlaySDK, decodificador fork de FFmpeg, mapa de componentes, configs, 31 archivos verificados (63/63 cadenas) | `C:\Program Files\SmartPSSLite` (solo lectura); `.cluster/smartpsslite-review-20260812/`; `.cluster/tukevision-re-smartpss-20260815/`; `TukeVision-portable/LOOP-0018F-SMARTPSS-B1-DISCRIMINANT.md` | Catálogo de ~30 mejoras sin SDK de marca; experimento B1: SmartPSS no causa el crash | **ESTUDIO COMPLETO — RE_COMPLETADA** (2026-08-12/15); cero código de marca |
| 6 | Patrones de red RTSP (Dahua/SmartPSS) | URL canónica `/cam/realmonitor?channel=N&subtype=S`; puertos 554/37777/37810/34567/1900/3702; drivers TCP/UDP/multicast; auto-switch; backoff no-retry-401; keep-alive; FIFO acotada; keyframe-first; DNS multi-IP | `.cluster/tukevision-re-smartpss-20260815/worker_80_red.md` + review.md | P0: TCP explícito + fallback UDP, backoff+jitter + no-retry-auth, auto-switch, búfer acotado; P1: discovery, health; P2: DNS caché, rtsps | **ESTUDIO COMPLETO**; TukeVision cubre parte (channel/subtype, reconexión E1–E4, watchdog stall) |
| 7 | Patrones de configuración/persistencia (SmartPSS) | Árbol Región→Grupo→Dispositivo→Canal (XML `V_1_13_0`), SafeBackupFile atómico, escenas, WndSplit `combine`, SQLite cifrada, backup zip | `.cluster/tukevision-re-smartpss-20260815/worker_81_config.md` + review.md | P0: perfil de cámara (`cameras.json`), DPAPI, `config_schema_version` + migración, atómica; P1: escenas, backup, índice SQLite | **ESTUDIO COMPLETO**; BASE: `default.json` estático sin versión |
| 8 | Patrones VMS video/UI (SmartPSS) | ~50 features: multivista 1–64, PTZ, playback, dewarp, Smart OSD capas, snapshot, grabación local, instant replay | `.cluster/tukevision-re-smartpss-20260815/worker_82_video.md` + review.md | ~90 % factible con OpenCV+FFmpeg+Tk+Pillow; P0: multivista, snapshot, OSD capas, grabación | **ESTUDIO COMPLETO**; features P0/P1 documentadas |
| 9 | Lecciones de seguridad (SmartPSS) | FTP en claro, AES-CBC con clave/IV hardcodeados, cert caducado + clave privada inline, passwords en logs, OpenSSL 1.0.2t EOL | `.cluster/tukevision-re-smartpss-20260815/worker_83_seguridad.md` + review.md; `.cluster/smartpsslite-review-20260812/review.md` | TukeVision ya es superior; P1: ampliar redacción, validación URLs, no-fuga en excepciones | **ESTUDIO COMPLETO**; P1/P2 pendientes |
| 10 | FFmpeg | Estado UNKNOWN (sin dependencia directa; backend = wrapper `opencv_videoio_ffmpeg500_64.dll`); comportamiento empírico; fork en SmartPSS valida el enfoque | `TES/09_Resources/...`; `TukeVision-portable/LOOP-0018B.md`; `evidence/loop_0018h/` | Uso directo solo si se aprueban grabación h264 / exportación de clips | **UNKNOWN → ESTUDIO EMPÍRICO PARCIAL** |
| 11 | ONVIF (WS-Discovery + PTZ + Recording) | Puertos 3702/1900; `OnvifAbility`; PTZ vía `python-onvif-zeep` propuesto; capability matrix: NO_EXISTE, PRIO 7, "Sin gap autorizado" | `.cluster/tukevision-re-smartpss-20260815/worker_80_red.md` §1.1/P1-5, `worker_82_video.md` §2.2; `evidence/loop_0018n/PRODUCT_CAPABILITY_MATRIX.md` | Descubrimiento + PTZ (diferenciador VMS); estándar abierto | **ESTUDIO PARCIAL — DISEÑADO** |
| 12 | NVIDIA DeepStream | Modelo "Video→Observación→Evento→Contexto→Decisión→Acción"; excluido del MVP | `TES/06_Research/NVIDIA - Context Aware Video AI.md`; `TES/09_Resources/...` (FUTURE); `TES/03_Architecture/TECHNOLOGY_STACK_MVP.md` | Solo conceptual: separación observación/decisión ya ADOPTADA | **RESEARCH_ONLY / FUTURE** — trigger NO cumplido |
| 13 | Mosaic / Mosaico | Principio de definiciones únicas de negocio; `CONSISTENT_WITH_REFERENCE` con DEC-0004 | `TES/06_Research/Mosaic - Definiciones unicas de negocio.md`; `TES/04_Decisions/DEC-0004` | Ninguno técnico; ya cubierto | **ARCHITECTURAL_REFERENCE** |
| 14 | n8n | Automatización/notificación post-alerta; sin caso aprobado | `TES/06_Research/n8n - Automatizacion futura.md`; `TES/09_Resources/...` (RESEARCH_ONLY) | Canales de notificación externa futuros | **RESEARCH_ONLY** — trigger: necesidad aprobada |
| 15 | RuView (WiFi sensing) | Presencia/movimiento por WiFi (ESP32); limitaciones hardware/calibración | `TES/06_Research/RuView - detección mediante WiFi.md`; `TES/06_Research/Fuentes de observación.md` | Puntos ciegos/bodegas; modelo fuente→observación ya soporta (DEC-0015) | **RESEARCH_ONLY** — trigger: zona sin cámara |
| 16 | PyResearch (retail/surveillance) | Demos CNN de actividades/flujo (videos, sin integración verificable); taxonomía ENTER/EXIT/DWELL/LOITER/APPROACH/WATCH/TOUCH/RETURN | `evidence/loop_0018n/EXTERNAL_REFERENCE_GAP_MATRIX.md` §2; `PRODUCT_CAPABILITY_MATRIX.md` | Concepto de Activity Layer post-tracking (no el código) | **REFERENCIA — ESTUDIO PARCIAL** |
| 17 | CNN / activity recognition | Actividad sobre video post-tracking; ACTIVITY_LAYER_SPEC diseñada (DWELL, LOITERING, APPROACH/WATCH/TOUCH/RETURN, MOVE_BETWEEN_ZONES); prohibido etiquetar THEFT | `evidence/loop_0018n/ACTIVITY_LAYER_SPEC.md`; `PRODUCT_CAPABILITY_MATRIX.md` (PRIO 4); `TES/02_Product/OBSERVABLES.md` | Taxonomía derivada de trayectoria+geometría (determinista), sin intención | **DISEÑADO** (spec completa, G7 PASS), NO implementado |
| 18 | People flow (conteo IN/OUT/INSIDE) | FlowCounter E-02 (portable); causa raíz del doble conteo (trajectory.py:67-71); dedup exige identidad (bloqueada) o ventanas | `.cluster/tukevision-reid-20260814/worker_30_tracking.md`; `evidence/loop_0018n/PRODUCT_CAPABILITY_MATRIX.md` (PRIO 3, REUSE E-02); `TES/07_Backlog/NICOPOLY_USE_CASES.md` (UC-006) | Conteo real por zona; dedup por ventana temporal sin biometría | **EXPERIMENTAL (E-02, solo portable)** — PRIO 3 |
| 19 | Trajectory analytics | TrackTrajectory E-02 indexada por track_id+camera_id; poda 300 pts (≈20 s) | `.cluster/tukevision-reid-20260814/worker_30_tracking.md`; `PRODUCT_CAPABILITY_MATRIX.md` (PRIO 3, REUSE E-02) | Historia de posiciones; base de heatmaps, LOITERING, APPROACH | **EXPERIMENTAL (E-02, solo portable)** — PRIO 3 |
| 20 | Instance segmentation | "segmentation selectiva" (PRIO 7, NO_EXISTE, "Pendiente gap", CUSTOM); sin estudio dedicado | `evidence/loop_0018n/PRODUCT_CAPABILITY_MATRIX.md` | Separar persona de entorno/producto; coste CPU alto | **SIN ESTUDIO** — solo fila de capability matrix |
| 21 | Heatmaps | Derivadas de trayectorias; PRIO 6, CUSTOM diseñado | `evidence/loop_0018n/PRODUCT_CAPABILITY_MATRIX.md` (PRIO 6) | Visualización de concentración (UC-005 futuro) | **DISEÑADO** (conceptual) |
| 22 | ReID (OSNet/torchreid/FastReID/TransReID/deep_sort/histograma/YOLO-embed) | Benchmark local: YOLO11n 94.7 ms/frame, embed 9.9–20.3 ms, hist 0.4 ms, coseno N=200→2.3 ms; torchreid incompatible numpy 2.x; diseño IdentityManager F1–F4 (104–136 h); **BLOQUEADO por DEC-0013/0019/0036** | `.cluster/tukevision-reid-20260814/`; `EXTERNAL_REFERENCE_GAP_MATRIX.md` §ReID (BLOQUEA); `PRODUCT_CAPABILITY_MATRIX.md` (PRIO 8) | Dedup por persona y correlación cross-cámara; **conflicto de gobernanza: embeddings = datos biométricos** | **ESTUDIO COMPLETO + DISEÑO COMPLETO**; implementación BLOQUEADA |
| 23 | Personas vs maniquíes (HumanVerifier) | YOLO no distingue; filtro de estaticidad (static_from_birth + dwell ≥90 s + probation), máquina de estados UNKNOWN→MOVING/STATIC_SUSPECT/STATIC_CLEARED; <1–5 ms/frame, 0 deps; fases A 10–14 h / B 6–8 h / C 8–12 h | `.cluster/tukevision-mannequin-20260814/`; `PRODUCT_CAPABILITY_MATRIX.md` (PRIO 7) | Elimina falsos conteos y falsas alertas de permanencia | **ESTUDIO COMPLETO + DISEÑO COMPLETO** (24–34 h); sin implementación |
| 24 | Faceplugin / Warden | Reconocimiento facial open source; **REJECTED por gobernanza** (DEC-0013) | `EXTERNAL_REFERENCE_GAP_MATRIX.md` §8; `TES/04_Decisions/DEC-0013` | NINGUNO aplicable | **REJECTED** (gobernanza; LOOP-0018N G4) |
| 25 | CactusCompute Hybrid | Computación híbrida edge+cloud; valida separación determinista vs razonamiento (AI_POLICY) | `EXTERNAL_REFERENCE_GAP_MATRIX.md` §9 | Solo patrón conceptual | **REFERENCIA CONCEPTUAL** — ESTUDIO PARCIAL |
| 26 | Qwen-MM-Plugins | Modelos multimodales para "AI second opinion"; Qwen REJECTED (DEC-0023) | `EXTERNAL_REFERENCE_GAP_MATRIX.md` §10; `AI_POLICY.md`; `TES/04_Decisions/DEC-0023`; `TES/03_Architecture/ARCHITECTURE.md` #14 | El gap (IA post-evento) es real y diseñado; la resolución NO es Qwen | **REJECTED** (política local) — gap queda como spec |
| 27 | Arquitecturas event/evidence | Modelo ADOPTADO; DEC-0002/0005/0006/0007; AI_POLICY; evidencia por REFERENCIA (0018Q/R) | `TES/03_Architecture/EVENTS.md`, `ARCHITECTURE.md`; `TES/04_Decisions/DEC-0002,0005,0006,0007,0010,0011,0012`; `evidence/loop_0018n/AI_POLICY.md`; `src/events/`, `src/evidence/`, `src/inference/events.py` | Ya implementado y certificado (motores propios) | **ACTIVE — CERTIFICADO** |
| 28 | Patrones web/API/VMS (presentación) | Web/API: NO_EXISTE, Next.js REJECTED, "Sin gap demostrado" (PRIO 7); VMS UI estudiado (fila 8) | `PRODUCT_CAPABILITY_MATRIX.md` (PRIO 7); `TES/09_Resources/...` (Next.js REJECTED); `.cluster/tukevision-re-smartpss-20260815/worker_83_seguridad.md` | API/web solo con necesidad aprobada; UI Tk local suficiente para el piloto | **SIN ESTUDIO DE REQUISITOS** — Next.js REJECTED |
| 29 | Almacén seguro de credenciales (DPAPI / keyring) | DPAPI vía ctypes (worker_81 P0-2), keyring (worker_83 P2-4); lección SmartPSS (clave+IV en binario = inútil); política actual: no persistir | `.cluster/tukevision-re-smartpss-20260815/worker_81_config.md` §4, `worker_83_seguridad.md` §4; `docs/SECRETS_AND_LOCAL_CONFIG.md` | Perfiles de cámara reutilizables sin texto plano; opcional | **DISEÑADO** (P0 config / P2 seguridad) |
| 30 | SQLite (stdlib) — índice de evidencia / catálogo | `data/evidence/index.db` propuesto; galería de identidad BLOQUEADA; stdlib, 0 deps; WAL | `.cluster/tukevision-re-smartpss-20260815/worker_81_config.md` (P1-8); `.cluster/tukevision-reid-20260814/worker_32_arquitectura.md` §6 | Índice de evidencia consultable; catálogo de cámaras | **DISEÑADO** (P1/P2); sin implementación |
| 31 | openpyxl / reportes | Exportación xlsx desde índice (P2-11 worker_81); SmartPSS usa plantilla MHTML | `.cluster/tukevision-re-smartpss-20260815/worker_81_config.md` §4 | Reportes operativos (pendiente necesidad; rompería lock) | **DISEÑADO** — P2, sin caso aprobado |
| 32 | Infraestructura rechazada (Docker, PostgreSQL, Redis, MinIO, Ollama, Hermes, AutoClaw, Next.js, nube) | Evaluadas y EXCLUIDAS del MVP | `TES/03_Architecture/TECHNOLOGY_STACK_MVP.md`; `TES/09_Resources/...` (REJECTED); `TES/04_Decisions/DEC-0023` | Ninguno hoy | **REJECTED** (DEC-0023) |
| 33 | Tooling forense nativo (WinDbg, PageHeap, AppVerifier, gflags, WER) | Aislamiento del double free → `opencv_videoio_ffmpeg500_64.dll`; dumps preservados; PageHeap/AppVerifier limpios (R3) | `TukeVision-portable/LOOP-0018H-WINDBG-NATIVE-CRASH-ANALYSIS.md`; `evidence/loop_0018i/` | Capacidad de diagnóstico para el call-site pendiente | **ACTIVE (dev tooling)** — no tecnología de producto |
| 34 | Extensiones internas E-02/E-03/E-04/E-05 + src/temporal | E-02 trajectory/FlowCounter, E-03 ReID (bloqueada), E-04 grid UI (`grid_safe_limit()=1`), E-05 quality_engine (sin consumidores); src/temporal/ certificado (33 tests) | `evidence/loop_0018j/certified_change_map.md`, `loop_0018n/E02_E05_APPLICABILITY_MATRIX.md`, `loop_0018r/REUSE_MAP_E02.md`; `TES/07_Backlog/BACKLOG.md` | Base interna reutilizable: conteo único (E-02), auto-switch (E-05), grid (E-04), correlación temporal | **EXPERIMENTAL (portable) / CERTIFICADO (src/temporal)** |

---

## 3. Síntesis de decisiones (conteo CORREGIDO S4)

- **ALREADY_COVERED (7):** OpenCV, Ultralytics/YOLO (personas), ByteTrack, Supervision, Mosaic, arquitecturas event/evidence, tooling forense (WinDbg).
- **PATTERN_REUSE_ONLY (4):** SmartPSS RE (estudio), PyResearch, CNN/activity recognition (hoy), CactusCompute Hybrid.
- **EXTENSION_CANDIDATE (10):** patrones de red RTSP (P1), config/persistencia (P1), VMS video/UI (P1), lecciones de seguridad (P1), people flow (P1), personas vs maniquíes (P1), trajectory analytics (P2), DPAPI/keyring (P2), SQLite índice (P2), extensiones E-02/E-04/E-05 (P1/P2).
- **DEFER (10):** FFmpeg, ONVIF/PTZ, DeepStream, n8n, RuView, instance segmentation, heatmaps, ReID, web/API, openpyxl/reportes.
- **REJECT (3):** Faceplugin/Warden, Qwen-MM-Plugins, infraestructura rechazada (Docker/PG/Redis/MinIO/Ollama/Hermes/AutoClaw/Next.js/nube).
- **PENDING sin razón: 0.** [HECHO: worker_92, verificado S4]

## 4. Gaps reales del BASE que las decisiones cierran (resumen ejecutivo)

1. **Doble conteo de personas (reportado por el usuario)** → people flow (E-02 + ventana temporal, no biométrico) P1; ReID DEFER por gobernanza.
2. **Maniquíes cuentan y generan falsas alertas de permanencia** → HumanVerifier P1 (24–34 h, 0 deps).
3. **RTSP frágil en reconexión + riesgo nativo abierto (double free)** → patrones de red P1 + cierre forense (WinDbg/PageHeap) como prerrequisito.
4. **GRID decorativo, sin snapshot/grabación/OSD capas** → patrones VMS P1.
5. **Config sin versión, sin catálogo de cámaras, sin backup** → patrones config P1.
6. **Higiene de secretos (huecos de redacción/validación)** → lecciones de seguridad P1.
7. Lo demás queda con trigger explícito o rechazo por gobernanza.

## 5. Notas de trazabilidad

- **[HECHO]** Estados del BASE citados provienen de LOOP-0018N/O/P/Q/R y DEC-0033..36.
- **[HECHO]** Doble free aislado a `opencv_videoio_ffmpeg500_64.dll` (3/3 dumps, LOOP-0018H); call-site SIN RESOLVER.
- **[HECHO]** SmartPSS RE verificada por revisor adversarial (31 archivos, 63 cadenas); credenciales redactadas; canario ausente.
- **[INFERENCIA]** Prioridades P0–P3: mapeo del consolidador sobre prioridades de las fuentes; cuando discrepaban se unificó al nivel superior (P1 único).
- **[INFERENCIA]** UC-001 sigue BLOCKED por insumos operacionales; ninguna extensión debería priorizarse por encima de desbloquear el piloto con el núcleo certificado.
- **Fuera de alcance:** estudios `ml-sync-20260811` y `ml-audit-20260814` = proyecto "Visibility Auditor" (scraper Mercado Libre), no TukeVision.

— Fin de technology_radar.md (LOOP-0018S)
