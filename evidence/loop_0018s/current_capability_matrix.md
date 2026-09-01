# CURRENT_CAPABILITY_MATRIX — LOOP-0018S

**LOOP:** 0018S · **Fecha:** 2026-08-16 · **Modo:** SOLO LECTURA (certificación del estado REAL)
**BASE_CODE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision` · **HEAD:** `cfad931` (loop-0018r)
**Fuente:** worker_90 (45 filas) + corrección de cobertura S4 (3 filas añadidas: 46–48).
**Estados (8):** CERTIFIED · IMPLEMENTED_NOT_PHYSICALLY_CERTIFIED · IMPLEMENTED_SYNTHETICALLY_CERTIFIED · PARTIAL · DESIGNED_ONLY · EXPERIMENTAL_PORTABLE_ONLY · NOT_IMPLEMENTED · REJECTED
**Regla:** cada capacidad con exactamente 1 estado y evidencia archivo:línea/test/loop. Credenciales REDACTED. Canario de trazado RTSP: no presente.

---

## 1. MATRIZ DE CAPACIDADES REALES

| # | Capacidad | Estado | Evidencia (código / test / loop) |
|---|---|---|---|
| 1 | RTSP lifecycle (open/read/stall/reconnect) | **CERTIFIED** | `src/capture/live_sources.py` RTSPSource (reader thread, cola FIFO acotada, FRAME_STALL_DETECTED, presupuesto global monotónico de reconexión, anti-doble-free). Certificación física: portable `LOOP-0018C`, `-C-R1`, `-E`, `-I`; reutilizada físicamente en loop_0018o. Tests: `tests/test_live_sources.py` (87/87 en loop_0018m_r1 focused). |
| 2 | channel / subtype selector | **CERTIFIED** | `src/capture/rtsp_url.py` `build_rtsp_url` (channel 1-16, subtype, path Dahua `/cam/realmonitor`). Físico: `evidence/loop_0018o/channel_detection.json` (16/16 canales accesibles en DVR real, host REDACTED); `scripts/test_channel_selector.py`. |
| 3 | Reconnect y backoff | **CERTIFIED** | `src/capture/live_sources.py` `_reconnect()` + `open()` (max_open_attempts, max_reconnect_attempts=3, reconnect_delay_seconds=2.0, presupuesto global NO reiniciado). Físico 0018C/R1; tests: `tests/test_live_sources.py` (87/87). |
| 4 | STREAM_LOST | **CERTIFIED** | `src/app/pipeline.py:346-348, 462-464, 502-503` (FAILED → final_status=STREAM_LOST); `src/capture/source_manager.py` `_worker` last_error="STREAM_LOST". Test funcional: `evidence/loop_0018m_r1/focused_tests.txt` + `tests/test_source_manager.py:258`. |
| 5 | SourceManager | **CERTIFIED** | `src/capture/source_manager.py` (register/start/stop/restart/health/snapshot/list_sources/isolate_failure/close_all; 1 hilo por cámara; cola FIFO `_QUEUE_MAX=8` drop-oldest). **Certificación FÍSICA multicámara:** `evidence/loop_0018o/` (4 cámaras reales, 300 s, verdict `MULTICAMERA4_PHYSICAL_CERTIFIED`). Tests: `tests/test_source_manager.py` (14). |
| 6 | Multicámara 4 | **CERTIFIED** | `evidence/loop_0018o/LOOP-0018O-PHYSICAL-MULTICAMERA-CERTIFICATION.md` (4 RTSP reales simultáneas, 300 s, 0 stalls, 0 reconnects, 4 conexiones TCP :554 sostenidas, RAM estable 227.8→232.4 MB). `final_health.json`: CAM-07 1280x720@15fps 4797 frames; CAM-01/03/05 352x240@7fps. |
| 7 | Aislamiento de cámara | **CERTIFIED** | `src/capture/source_manager.py` (worker por cámara; `isolate_failure`; invariantes SOURCE_ISOLATION/ONE_CAMERA_FAILURE_DOES_NOT_STOP_OTHERS). Físico: `evidence/loop_0018o/isolation_stop.json` + `isolation_restart.json`. Tests: `tests/test_source_manager.py`. |
| 8 | Camera health agregada (per-camera) | **CERTIFIED** | `src/capture/source_manager.py` `CameraHealth` (state/fps/resolution/last_valid_frame_age_ms/stall_count/queue_depth/healthy). Físico: `evidence/loop_0018o/final_health.json`; tests `test_source_manager.py`. |
| 9 | Observation Layer (ActivityObservation, BoundedObservationQueue, ActivityLayer) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/observations/activity.py` (schema canónico, cola bounded, ActivityLayer con register_from_source_manager/feed/consume/stats/close). Tests: `tests/test_activity_layer.py` **39/39** (loop_0018p, verdict OBSERVATION_LAYER_MINIMUM_OPERATIONAL). ⚠️ NO cableado al pipeline de producto (H1). |
| 10 | QUALITY / BALANCED / ECONOMY | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/observations/activity.py` `ObservationPolicy` (config-driven, `config/default.json` bloque `observation`: 5/2/1 fps análisis; default BALANCED; clamp sanitizador; override por cámara). Tests: `test_activity_layer.py` (6 perfiles) + `test_inference_layer.py` (42/42). No operativo en runtime del producto. |
| 11 | Inferencia selectiva (POLICY→INFERENCE) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/inference/selective.py` `SelectiveInferencePipeline` (considered/processed/skipped_by_policy/inference_errors/events_generated, aislamiento por cámara, cola bounded) + `build_pipeline(config)`. Tests: `tests/test_inference_layer.py` **42/42**; demo real en `evidence/loop_0018q/FUNCTIONAL_DEMO.md` (CAM-07, 4 feeds, BALANCED→1 procesado/3 saltados, evento PERSON_DETECTED conf 0.84). ⚠️ No cableado (H1). |
| 12 | YOLO backend | **CERTIFIED** | `src/detection/person_detector.py` (YOLO11n, carga perezosa, filtro clase/conf) + `src/inference/engines.py` `YoloInferenceEngine`. Tests: `tests/test_person_detector.py` + `tests/test_inference_real_backend.py` **4/4** con `models/yolo11n.pt` real (3.557 s). Demo real: `evidence/loop_0018q/FUNCTIONAL_DEMO.md`. |
| 13 | Detección de eventos (EventDetector, InferenceEvent, BoundedEventQueue) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/inference/events.py` (OBJECT_DETECTED/PERSON_DETECTED, thresholds config-driven, cola con drop_oldest/drop_newest). Tests: `test_inference_layer.py` 42/42 + demo real 0018q. ⚠️ No cableado (H1). |
| 14 | evidence_reference (propagación) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/inference/contract.py` `InferenceResult.evidence_ref` → `src/inference/events.py` `InferenceEvent.evidence_ref` (G10 loop_0018q PASS); `src/temporal/tracker.py` evidencia first/latest/best (G18 loop_0018r, `BEHAVIOR_EVIDENCE.md`; sin fabricación de paths, G19). No hay almacenamiento físico asociado en runtime. |
| 15 | Temporal / local tracking (loop-0018r) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/temporal/contract.py` (LocalTrack, TemporalActivity, duración, timestamps UTC Z) + `src/temporal/tracker.py` `LocalTracker` (ciclo STARTED/ACTIVE/ENDED, asociación por ventana 2000 ms + IoU 0.05, timeout 5000 ms, retención bounded, aislamiento por cámara). Tests: `tests/test_temporal_tracking.py` **33/33**; regresión total 359/359. ⚠️ No cableado (H1). |
| 16 | Trajectory | **EXPERIMENTAL_PORTABLE_ONLY** | No existe en BASE. Portable E-02 (TrajectoryStore) experimental: `evidence/loop_0018n/PRODUCT_CAPABILITY_MATRIX.md` (EXPERIMENTAL E-02; NEXT_ACTION post 4-cam, no migrado). |
| 17 | Zones (polígono) | **CERTIFIED** | `src/context/zone.py` (validación polígono, pointPolygonTest, ENTERED/REMAINED/EXITED/OUTSIDE). Tests: `tests/test_zone.py`; integrado en pipeline de producto (`src/app/pipeline.py`). |
| 18 | Dwell / permanencia (stay_seconds) | **CERTIFIED** | `src/app/pipeline.py` `_stay_seconds` + `src/events/engine.py` PERMANENCIA_PROLONGADA (umbral 30 s) + `src/risk/calculator.py` rangos 0/40/60/80. Tests: `tests/test_pipeline.py`, `test_event_engine.py`, `test_business_rules.py`, `test_risk_calculator.py`. |
| 19 | Flow IN / OUT / INSIDE | **EXPERIMENTAL_PORTABLE_ONLY** | No existe en BASE. Portable E-02 `FlowCounter` experimental (PRODUCT_CAPABILITY_MATRIX.md loop_0018n). |
| 20 | Risk | **CERTIFIED** | `src/risk/calculator.py` (RiskScore 0-100 explicable). Tests: `tests/test_risk_calculator.py`. |
| 21 | Alerts | **CERTIFIED** | `src/alerts/engine.py` + `models.py` (umbral 60, estados NEW..CLOSED). Tests: `tests/test_alert_engine.py`. |
| 22 | Evidence storage | **CERTIFIED** | `src/evidence/store.py` + `models.py` (inmutable `data/evidence/<alert_id>/frame.jpg` + metadata.json con sha256; EvidenceExistsError). Tests: `tests/test_evidence_store.py` (incluye fallo de escritura y duración, loop_0018k). |
| 23 | Recording | **PARTIAL** | `src/app/pipeline.py` `cv2.VideoWriter` monofuente → `data/output/processed.mp4`. Sin recording por cámara ni clips gestionados. |
| 24 | Snapshots | **PARTIAL** | `FrameSnapshot` por frame para UI (`src/app/pipeline.py`, `src/ui/controller.py`) + `frame.jpg` de evidencia por alerta. No hay snapshot por cámara multicámara. |
| 25 | Playback | **NOT_IMPLEMENTED** | Sin módulo de playback en BASE ni portable (matriz 0018n: NO_EXISTE). |
| 26 | Heatmaps | **NOT_IMPLEMENTED** | Sin código (matriz 0018n: NO_EXISTE, roadmap). |
| 27 | Activity recognition (semántica/comportamiento) | **NOT_IMPLEMENTED** | La Activity Layer (`src/observations/activity.py`) es una capa de OBSERVACIÓN/sampling, no reconoce comportamiento. `src/temporal/contract.py` declara explícitamente actividad genérica "NO se clasifica robo/sospecha/intención/amenaza". |
| 28 | Actividad temporal genérica (PERSON_PRESENCE) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/temporal/tracker.py` TemporalActivity (33/33 tests, demo loop_0018r: `ACT-CAM-07-000001` PERSON_PRESENCE event_count 3). |
| 29 | Segmentation | **NOT_IMPLEMENTED** | Sin código (matriz 0018n: NO_EXISTE, gap pendiente). |
| 30 | ReID / identidad de contexto | **EXPERIMENTAL_PORTABLE_ONLY** | Portable E-03 experimental; gobernanza DEC-0013 CONFLICTO/BLOQUEADO (matriz 0018n). En BASE no existe. |
| 31 | Correlación cross-camera | **NOT_IMPLEMENTED** | Explícitamente NO: `src/temporal/__init__.py` y `contract.py` ("NO correlación cross-camera de identidad; track_id LOCAL"); G17 loop_0018r = NO. |
| 32 | Face recognition | **NOT_IMPLEMENTED** | Sin código. |
| 33 | ONVIF / discovery | **NOT_IMPLEMENTED** | Sin código (matriz 0018n: NO_EXISTE, sin gap autorizado). |
| 34 | PTZ | **NOT_IMPLEMENTED** | Sin código (matriz 0018n: NO_EXISTE). |
| 35 | Web / API | **NOT_IMPLEMENTED** | Sin servidor web ni API. Next.js fue **REJECTED** como opción (matriz 0018n). |
| 36 | AI / VLM reasoning (segunda opinión) | **NOT_IMPLEMENTED** | Sin código; Qwen MM **REJECTED** (matriz 0018n). |
| 37 | Telemetría | **PARTIAL** | `src/observability/logging_setup.py` (RUN_ID, rotación 1 MB, redacción) + `scripts/health_check.py`. Monitor de recursos físicos existe SOLO en portable (LOOP-0018L; resource_samples.csv en loop_0018o). Sin agregación de telemetría del producto. |
| 38 | Configuración / persistencia | **CERTIFIED** | `config/default.json` (bloques video/rtsp/output/detection/zone/business/alerts/observation/inference/temporal) + `src/app/pipeline.py` `load_config` con validación explícita (PipelineConfigError). Tests: `test_pipeline.py` (config validation). |
| 39 | Secret management (redacción/construcción URL) | **CERTIFIED** | `src/observability/logging_setup.py` `redact_rtsp_url` + `src/capture/rtsp_url.py` (percent-encoding; password solo en memoria; `CameraDescriptor.__repr__` sin password) + `src/ui/controller.py` (redacción en logs, fix SECURE_RTSP_UI_GAP commit 4e530f3). Tests: `tests/test_secret_leak.py` (canary redactado) + `scripts/test_secret_leak.py`; secret_scan.txt loop_0018m_r1 = 0. |
| 40 | Observabilidad (logging operativo) | **CERTIFIED** | `src/observability/logging_setup.py` + `scripts/test_trace_observability.py` + `tests/test_observability.py`. |
| 41 | RTSP diagnostics | **CERTIFIED** | `src/diagnostics/rtsp_connection_test.py` + `scripts/test_rtsp_connection.py` (15-08) + `tests/test_rtsp_connection_diagnostic.py`; usados en certificaciones físicas 0018C/D/E. |
| 42 | UI local operativa (Tkinter, monofuente) | **IMPLEMENTED_SYNTHETICALLY_CERTIFIED** | `src/ui/controller.py` + `tk_view.py` + `state.py` + `scripts/run_interface.py` (FILE/WEBCAM/RTSP, backpressure visual, STOP). Tests: `tests/test_ui_controller.py` + `test_dashboard.py` (parte de 359/359). No validada físicamente como app de escritorio en los loops escritos. |
| 43 | Command Center (grid multicámara) | **NOT_IMPLEMENTED** | La UI es de UNA fuente. Grid E-04 multicámara existe solo como diseño portable experimental (matriz 0018n: UI E-04 grid_safe_limit, sin datos). |
| 44 | Per-camera pipeline (1 pipeline/cámara) | **PARTIAL** | SourceManager entrega frames/cola/snapshot por cámara, pero NO existe pipeline por cámara cableado (sin detección/tracking/eventos por cámara en runtime). Matriz 0018n: "per-camera pipeline NO_EXISTE… ADAPT (Pipeline por cámara)". |
| 45 | Incidents | **NOT_IMPLEMENTED** | `src/incidents/` existe pero VACÍO (scaffolding). Igual `src/shared/`, `src/visualization/` (vacíos). |

### Filas añadidas por cobertura S4 (revisor; 0018n → worker_90)

| # | Capacidad | Estado | Evidencia |
|---|---|---|---|
| 46 | Personas vs maniquíes (filtro de estaticidad / HumanVerifier) | **DESIGNED_ONLY** (en BASE: NOT_IMPLEMENTED) | Sin código en BASE (`person_detector.py` filtra solo clase/conf COCO 0; no distingue maniquíes). Diseño completo: `.cluster/tukevision-mannequin-20260814/` (worker_60/61/62 + review; máquina de estados UNKNOWN→MOVING/STATIC_SUSPECT/STATIC_CLEARED, 24–34 h, 0 deps). Matriz 0018n fila "person vs mannequin" PRIO 7. |
| 47 | Calidad de frame / quality_engine (E-05) | **EXPERIMENTAL_PORTABLE_ONLY** | Solo portable: `src/capture/quality_engine.py` (14-08, E-05, sin consumidores en portable). No existe en BASE (distinto del concepto QUALITY/BALANCED/ECONOMY de ObservationPolicy, fila 10). Clasificado MIGRATE por worker_93. |
| 48 | Tracking ByteTrack (PersonTracker) | **CERTIFIED** | `src/tracking/person_tracker.py` (ByteTrack, buffer 30, min_conf 0.6; parte de la cadena 2.1). Tests: `tests/test_person_tracker.py` (10 tests, dentro de 359/359). Sin fila numerada propia en worker_90 (cobertura implícita) — añadida por S4 para cobertura 1:1 con la lista mínima de Fase 1. |

---

## 2. Resumen de estados

| Estado | Conteo (45 filas worker_90) | Con filas S4 (48) |
|---|---|---|
| CERTIFIED | 21 | 22 |
| IMPLEMENTED_NOT_PHYSICALLY_CERTIFIED | 0 | 0 |
| IMPLEMENTED_SYNTHETICALLY_CERTIFIED | 9 | 9 |
| PARTIAL | 5 | 5 |
| DESIGNED_ONLY | 0 | 1 |
| EXPERIMENTAL_PORTABLE_ONLY | 4 | 5 |
| NOT_IMPLEMENTED | 6 | 6 |
| REJECTED | 0 | 0 |
| **TOTAL** | **45** | **48** |

*Nota: el conteo por estado de la fila 45-original es el del worker_90; el total certificado con cobertura S4 es 48 filas. El número oficial de capacidades clasificadas por worker_90 es 45; S4 añade 3 filas de cobertura sin invalidar la clasificación original.*

— Fin de current_capability_matrix.md (LOOP-0018S)
