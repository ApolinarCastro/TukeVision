# SALIDA OBLIGATORIA — EXECUTION_ID: MACRO-OC-02

**Command Center UX consolidated repair — fase de reparación completada (continuación: FOCUS-SIZE-02 / HEALTH-02 / REVIEW-01).**
Fecha: 2026-08-20. Alcance: `src/ui/tk_view.py`, `src/ui/review_view.py`, `src/observability/system_health.py`, tests, `evidence/macro_oc_02/`.

---

## Resultado global

| Campo | Valor |
|---|---|
| FINAL_VERDICT | **PASS** |
| STATUS | **READY_FOR_REAL_OPERATOR_UX_VALIDATION** |
| PROTECTED_CORE_REWRITTEN | NO |
| SECOND_PIPELINE_CREATED | NO |
| CODEX_STATUS | SUSPENDED_RESOURCE_LIMIT |
| AUTOCLAW_STATUS | SUSPENDED_RESOURCE_LIMIT |

---

## Defectos cerrados

| Defecto | Estado | Evidencia |
|---|---|---|
| DEF-UI-LAYOUT-02 | **PASS** | Barra de controles mapeada y visible en 1366x768, 1600x900 y 1920x1080 (harness real). |
| DEF-UI-NAV-01 | **PASS** | FOCUS→RETURN, ESC global, PREV/NEXT/FULLSCREEN/GRID verificados con widget real. |
| DEF-UI-ZOOM-01 | **PASS** | ZOOM+ / ZOOM- acotados, **RESET ZOOM** añadido (`_zoom_reset_btn`/`_on_zoom_reset`), zoom presentacional (nunca altera YOLO/tracking/evidence). |
| DEF-UI-FOCUS-EMPTY-01 | **PASS** | FOCUS sin canvas/celda de slot vacío (0 ghost) tras doble clic; GRID16 muestra exactamente 1 slot vacío. |
| DEF-UI-DEVICE-01 | **PASS** | CONFIGURACIÓN abre `DeviceSettingsWindow` (título correcto), HOST_IP editable, CONNECTION_TEST presente. |
| DEF-OBS-LOG-01 | **PASS** | Causa raíz + fix `_ResilientStreamHandler` (ver Logging). |
| DEF-UI-FOCUS-SIZE-02 | **PASS** | FOCUS llena el workspace (0.6×wrap mínimo) en 1366x768, 1600x900 y 1920x1080; zoom presentacional sobre la vista expandida. |
| DEF-HEALTH-02 | **PASS** | HEALTH_SOURCE_OF_TRUTH = estado runtime de cada fuente (OPEN+frame reciente); una fuente abierta con frame stale es **DEGRADED**, nunca ONLINE. Header/tiles correlacionados. |
| DEF-UI-REVIEW-01 | **PASS** | REVISIÓN abre GUI de producto dentro de TukeVision (`TukeVisionReviewWindow`); CMD_REQUIRED: **NO**. |

---

## Criterios de aceptación (reproducibles)

| Criterio | Resultado |
|---|---|
| PHYSICAL_CAMERAS | 15 (cam_01..cam_15) |
| GRID_CAPACITY | 16 |
| EMPTY_SLOT_16 | "SIN CÁMARA" (`is_empty`, camera_id="") |
| GRID16 rende 15 canvases + 1 empty | PASS |
| FOCUS(cam) sin ghost | PASS |
| Health denominator | **15, nunca 16** (test nuevo `test_empty_slot_is_not_a_camera_in_the_health_denominator`) |
| Slot vacío excluido de `camera_health` | PASS |
| Control surface visible (todas las resoluciones) | PASS (_back, _settings, _grid, _zoom_in/out/reset, _ptz hidden) |
| CONFIG_VISIBLE / CONFIG_OPENS | PASS |
| HOST_IP_EDITABLE | PASS |
| CONNECTION_TEST | PASS |
| RETURN_* (back grid + prev grid + RETURN key) | PASS |
| ESC_RETURN | PASS (en FOCUS retorna; fuera de FOCUS no cierra la app) |
| DOUBLE_CLICK_GRID_TO_FOCUS | PASS |
| DOUBLE_CLICK_FOCUS_TOGGLE_ZOOM (1.0x/2.0x) | PASS |
| EVIDENCE_BUTTON_VISIBLE | PASS |
| CLIP_REVIEW_BUTTON_VISIBLE | PASS |
| ZOOM_RESET_VISIBLE / ZOOM_RESET_FUNCTIONAL | PASS |
| PTZ_STATE | **CAPABILITY_GATED**: oculto si no declarado (`pack_forget`), habilitado solo si `certified`; ptz_command siempre False. |
| Video continuity tras navegación | PASS (paneles conservan frames y aceptan frames nuevos; test `test_video_context_preserved_across_navigation`) |
| Resize no oculta controles críticos | PASS (3 resoluciones auditadas) |

---

## Logging (DEF-OBS-LOG-01)

- **ROOT_CAUSE**: la capa de captura redirige el stderr nativo (fd 2) para silenciar OpenCV; un `StreamHandler` plano escribe a un descriptor roto y `logging` emite `OSError WinError 1` de forma repetida ("--- Logging error ---").
- **FIX**: `_ResilientStreamHandler` en `src/observability/logging_setup.py` — detecta el descriptor inutilizable y omite únicamente el eco de consola; el archivo de log permanece como fuente autoritativa. Ningún frame/vía de negocio se toca.
- **STATUS**: FIXED (tests `test_logging_resilience.py` PASS).

---

## CONTROL_SURFACE_ROOT_CAUSE (auditoría real)

- La barra de controles era visible en las 3 resoluciones, pero el marco PTZ se extendía hasta x=1355 en 1366px y no existía botón RESET ZOOM.
- Correcciones en `tk_view.py`: RESET ZOOM añadido; PTZ pasa a `_ptz_frame` y `_update_ptz_controls()` lo oculta (pack_forget) cuando la cámara no declara `supported`; `_build()` lo oculta en arranque.

---

## Validación real (harness con TkApp/UiController/SystemHealthSampler reales, sin RTSP)

```
python evidence/macro_oc_02/run_real_ui_validation.py
```

- `ALL_RESOLUTIONS_VALIDATED: REAL_UI_VALIDATION=PASS` @ **1366x768 / 1600x900 / 1920x1080** (reproducible).
- Header real: `CAMERAS: 13 / 15 ONLINE` (13 online / 15 físicas / denominador 15).
- Screenshots: `evidence/macro_oc_02/{1366x768,1600x900,1920x1080}_{grid16,grid9,focus_cam05,zoom_2x,config}.png` + `..._grid16.png`.

---

## Pruebas

| Suite | Resultado |
|---|---|
| FOCUSED_TESTS (UI + logging + device + grid + system_health) | **94 passed** |
| FULL_REGRESSION | **669 passed, 4 skipped, 15 subtests passed** |
| COMPILEALL (src, scripts) | OK |
| SECRET_SCAN (`scripts/test_secret_leak.py`) | **4 PASS, 0 FAIL** |
| DIFF_CHECK | PASS — solo `tk_view.py` (controles), 3 tests y `evidence/`; `src/capture/` intacto (LastWriteTime 12–19/08); sin secretos añadidos. |

---

## Notas finales

- Zoom es presentacional: nunca modifica frames de detección/tracking/evidencia.
- No se reabrió RTSP/auth (sin regresión real que lo exija). Operador debe validar sobre hardware/RTSP real.
- Fuera de FOCUS, ESC no cierra la aplicación (contrato intacto).

---

## Continuación — DEF-UI-FOCUS-SIZE-02 / DEF-HEALTH-02 / DEF-UI-REVIEW-01 (SALIDA OBLIGATORIA)

### DEF-UI-FOCUS-SIZE-02 — FOCUS LARGE + ZOOM WORKS

| Campo | Valor |
|---|---|
| FOCUS_ROOT_CAUSE | Weights/uniform residuales del grid (rows 1..3 de una 4x4 aún weight=1, uniform="cam") dividían el workspace al entrar en FOCUS → el canvas enfocado recibía ~1/4 del alto. |
| FOCUS_FIX | `_rebuild_grid()` llama `_reset_grid_geometry()` (weights/uniform a 0/"" para rows/cols 0..63) antes de montar la celda FOCUS; la celda usa `fill=BOTH, expand=True`. |
| FOCUS_EXPANDED | PASS — canvas ≥ 0.6×wrap en 1366x768, 1600x900 y 1920x1080 (harness real). |
| FOCUS_ASPECT_RATIO | PASS — `allow_upscale=True` solo en FOCUS: escalado proporcional (letterbox/pillarbox), nunca estirar; GRID nunca upscalea (test `test_grid_never_upscales`). |
| ZOOM_ON_EXPANDED_FOCUS | PASS — 1.0x / + / - / RESET / doble clic 1x↔2x sobre la vista expandida; presentacional, nunca inferencia. |

### DEF-HEALTH-02 — HEALTH CORRELATES

| Campo | Valor |
|---|---|
| HEALTH_ROOT_CAUSE | `RTSPSource.last_valid_frame_age_ms` devuelve 0 cuando nunca llegó un frame (live_sources.py:752), así una fuente OPEN sin frames contaba como ONLINE. |
| HEALTH_SOURCE_OF_TRUTH | Estado runtime de cada fuente + edad del último frame (`health_state_for` en `src/observability/system_health.py`). |
| ONLINE_THRESHOLD | `FRESH_FRAME_AGE_SECONDS = 3.0` (configurable vía `fresh_frame_age_seconds` del sampler). |
| HEALTH_STATES | ONLINE = open + readable_frames + age ≤ umbral; DEGRADED = open/reconnecting con frame stale o ausente/recuperable; OFFLINE = closed/failed/sin frame reciente. |
| LAST_FRAME_ONLINE | **NO** — el frame cacheado nunca clasifica ONLINE. |
| CAMERAS_ONLINE | 13/15 normal; al volver stale una fuente abierta: **12/15** (harness). |
| HEALTH_DENOMINATOR | **15** (físicas), nunca 16; el slot vacío del GRID16 queda excluido. |
| TILE_HEADER_CORRELATION | PASS — GREEN=ONLINE, AMBER=DEGRADED, GRAY=OFFLINE; el dot del tile de la cámara stale fue AMBER al mismo tiempo que el header decía 12/15 (harness real). |

### DEF-UI-REVIEW-01 — REVIEW IS PRODUCT UI

| Campo | Valor |
|---|---|
| REVIEW_GUI | `TukeVisionReviewWindow` (Toplevel modal) en `src/ui/review_view.py`, abierta desde el botón REVISIÓN; CMD_REQUIRED: **NO**. |
| REVIEW_CORE_REUSED | Adapter sobre `scripts.review_behavior_signals` (`load_existing`/`save`/`write_metrics`/`resolve_evidence`); mismo JSONL + `human_review_matrix.csv`. Sin datastore ni pipeline nuevos. |
| REVIEW_CLASSIFICATION | CLASIFICACIÓN 1..5 = nombres semánticos existentes (`src.review.contracts.ALLOWED_CLASSIFICATIONS`: USEFUL_SIGNAL, BENIGN_ACTIVITY, AMBIGUOUS, INSUFFICIENT_EVIDENCE, SYSTEM_ERROR). |
| REVIEW_JPEG | PASS — thumbnail JPEG (PIL/ImageTk) del evidence frame; clip ausente → "Clip no disponible" sin error técnico. |
| REVIEW_PREV / REVIEW_NEXT | PASS — navegación ANTERIOR/SIGUIENTE. |
| REVIEW_SAVE | PASS — persiste a la matriz CSV existente y recalcula métricas (harness: `USEFUL_SIGNAL` leída desde el archivo). |
| REVIEW_EMPTY_STATE | PASS — "No hay revisiones pendientes". |
| REVIEW_REOPEN_PERSISTENCE | PASS — reabrir la ventana carga la clasificación guardada. |

### Criterios de aceptación (BLOCK O)

| Criterio | Resultado |
|---|---|
| FOCUS llena el workspace | PASS (3 resoluciones) |
| Aspect ratio preservado (sin estirar) | PASS |
| Zoom sobre FOCUS expandido (1.0x/+/-/RESET/doble clic) | PASS |
| Health usa estados runtime de fuentes | PASS |
| Frame cacheado no cuenta ONLINE | PASS |
| Total cámaras = 15 (denominador) | PASS |
| Review GUI abre desde la app | PASS |
| Record existente carga su clasificación | PASS |
| Clasificación persiste (matrix CSV + métricas) | PASS |
| Siguiente/anterior funciona | PASS |
| Review vacío muestra mensaje en GUI | PASS |
| No se requiere CMD | PASS |

### Validación real (BLOCK N) — harness ampliado

```
python evidence/macro_oc_02/run_real_ui_validation.py
```

- `ALL_RESOLUTIONS_VALIDATED: REAL_UI_VALIDATION=PASS` @ 1366x768 / 1600x900 / 1920x1080 (reproducible).
- Evidencias nuevas: `{res}_focus_cam05.png`, `{res}_zoom_2x.png`, `{res}_config.png`, `{res}_review_gui.png` + correlación header/tile DEGRADED en runtime.
- DoD: **FOCUS LARGE + ZOOM WORKS + HEALTH CORRELATES + REVIEW IS PRODUCT UI** = PASS.

### Pruebas (continuación)

| Suite | Resultado |
|---|---|
| FOCUSED_TESTS (health_states + focus_expansion + review_window) | **32 passed** |
| FULL_REGRESSION | **701 passed, 4 skipped, 15 subtests passed** |
| COMPILEALL (src, scripts) | OK |
| SECRET_SCAN | **4 PASS, 0 FAIL** |
| DIFF_CHECK | PASS — solo `src/ui/tk_view.py`, `src/observability/system_health.py`, `src/ui/review_view.py` (nuevo), 5 tests, `evidence/`; `src/capture/` intacto (LastWriteTime 12–19/08; solo `.pyc` de `__pycache__` regenerados por los runs); sin secretos añadidos. |

---

## Fase física — STABILITY FORENSICS + DEVICE ADMIN (continuación, sin RTSP aún)

**REPAIR_CONTINUES_SAME_MACRO.** El gate físico (30 MIN con DVR real + 15 cámaras y credenciales del operador) NO se puede ejecutar desde esta sesión porque las credenciales solo existen en memoria del launcher interactivo. Se entregó toda la instrumentación y administración previa al run, y el run queda en manos del operador (instrucciones al final).

### Instrumentación (BLOCKS C / D / E / L) — entregada y testeada

| Campo | Estado |
|---|---|
| CAPTURE_HEARTBEAT / RENDER_HEARTBEAT / INFERENCE_HEARTBEAT | `FrameHeartbeat` (`src/observability/frame_heartbeat.py`): `last_received_frame_at` (entrada a pipeline), `last_inference_frame_at` (fin de procesamiento), `last_rendered_frame_at` (render en canvas). Clasifica CAPTURE_STALL / INFERENCE_STALL / RENDER_STALL / HEALTHY / NO_FRAME por muestreo (nunca un log por frame). Hook `on_received` añadido a `OperationalPipeline` (aditivo, sin tocar captura). |
| TELEMETRY | `ResourceTelemetry` (`src/observability/resource_telemetry.py`): UPTIME/CPU/PROCESS_RSS/SYSTEM_RAM/THREAD_COUNT/QUEUE_DEPTHS/ACTIVE_SOURCES/ONLINE/RECONNECTING/OFFLINE cada 30s, alineado a 0m/5m/10m/20m/30m; export JSON atómico. |
| EXIT_FORENSICS | `ExitForensics` (`src/observability/exit_forensics.py`): hooks sys/threading.excepthook; `WHY_PROCESS_EXITED` (NORMAL_UI_CLOSE / UNHANDLED_EXCEPTION / OPERATOR_SHUTDOWN) con traceback sanitizado (redacta credenciales RTSP); wired en `run_multicamera.main` + `process_exit_forensics.json` + `resource_telemetry.json`. |
| HEALTH (BLOCK L) | `health_state_for` refina: ONLINE (frame reciente) / **RECONNECTING** (source recuperándose: CONNECTING/RECONNECTING/REGISTERED) / DEGRADED (open sin frame o stale) / OFFLINE. Indicador tile AMBER para RECONNECTING; header sigue excluyendo no-ONLINE. |

### DEVICE ADMIN CRUD (BLOCKS M / N / O) — entregada y testeada

| Campo | Estado |
|---|---|
| STORE_ADD / STORE_EDIT / STORE_DISABLE | Backend `save_store` / `set_store_enabled` + UI `+ NUEVA TIENDA`, `EDITAR TIENDA`, `DESHABILITAR` (StoreEditorWindow: store_id, nombre, organization, timezone, habilitada). |
| RECORDER_ADD / EDIT / TEST / DISABLE | `+ NUEVO DISPOSITIVO` explícito, GUARDAR, PROBAR CONEXIÓN (acotado, opener certificado), `DESHABILITAR` (`set_recorder_enabled`). |
| CAMERA_ADMIN | Tabla CÁMARAS DEL RECORDER (canal, ID, nombre, zona, activa) + edición de nombre/zona/enabled vía `save_camera`; `save_recorder` preserva nombre/zona/enabled de canales existentes. |
| SAVE_SAFETY (BLOCK N) | validate → `_atomic_write` (tempfile + os.replace) → recarga StoreCatalog → confirm; fallo no corrompe config previa. Password NUNCA en JSON plaintext (solo `credentials_ref`). `_validate` ahora estructural (permite 0 cámaras habilitadas, p.ej. deshabilitar la única tienda). |

### Pruebas (fase física, pre-run)

| Suite | Resultado |
|---|---|
| FOCUSED_TESTS (stability_instrumentation + health_states + device_config + device_settings_view) | **60 passed** |
| FULL_REGRESSION | **733 passed, 4 skipped, 15 subtests passed** |
| COMPILEALL | OK |
| SECRET_SCAN | **4 PASS, 0 FAIL** |
| DIFF_CHECK | PASS — `src/capture/` intacto (12–19/08); solo 3 módulos de observabilidad (nuevos), `operational_pipeline.py` (hook aditivo), `system_health.py`, `tk_view.py` (color), `run_multicamera.py` (wiring), `device_config.py` + `device_settings_view.py` (CRUD), 4 tests. |

### EVIDENCIA FÍSICA LEÍDA (BLOCK A — 2026-08-20T17:36-17:48, ~12.5 min, exit prematuro)

| Archivo | Hallazgo |
|---|---|
| `resource_telemetry.json` | 0s: 15 offline (arranque) -> 30s: 3 online / 11 reconnecting / 0 offline / 25 thr / RSS 1064MB -> 180s: 7/6/0 / 30 thr / 1266MB -> 300s: 3/0/10 / 14 thr / 839MB -> 600s: 1/0/14 / 5 thr / 577MB -> 720s: 1/0/14 / 5 thr. Degradación progresiva 15->1, queue 8 saturada, CPU 300-500%. |
| `process_exit_forensics.json` | `WHY_PROCESS_EXITED=UNHANDLED_EXCEPTION`, `uptime_s=747.9` (~12.4 min), `exception_type=OSError`, `PermissionError` en `tk_view._update_action_targets -> review_available -> _review_records.read_text` (lock del archivo por writer concurrente). |
| `runtime_trace.json` | cam_08 3707 FRAME_RECEIVED / 315 INFERENCE / 245 RENDERED ; cam_14 2004/26/125 ; disparidad CAPTURE vs INFERENCE vs RENDER indica throttling pero captura sí entregaba. |

Clasificación heartbeats: `CAPTURE_STALL` (reconnecting), `INFERENCE_STALL` (cola llena), `RESOURCE_PRESSURE` (CPU 400%, RAM 80%) + `RECONNECT_LIFECYCLE` (presupuesto 3 -> FAILED permanente).

### ROOT CAUSE — SHUTDOWN (BLOCK B)

`_update_action_targets` invocaba `review()/latest_evidence()/clip_target()` sin try → `PermissionError` por lock de `signal_review_records.jsonl` (writer) propagó vía `tk.after` → `report_callback_exception` no capturado → `UNHANDLED_EXCEPTION` → proceso muere a los 12 min. Violaba `SINGLE_CAMERA_FAILURE != GLOBAL_APPLICATION_EXIT`.

**FIX_SHUTDOWN** (`tk_view.py:1513`, `run_multicamera.py:278`): cada callable envuelto en `try/except` → `None/False`; `_poll` envuelto en `try/except` + log; `report_callback_exception` instalado para loguear sin matar; `_review_records.read_text` envuelto en `try (OSError, PermissionError) -> ()`.

### ROOT CAUSE — STREAM STABILITY (BLOCKS C/D)

- DVR 15×MAIN simultáneos satura sesiones: tormenta 11 reconnecting a los 30s.
- `RTSPSource._reconnect_count` presupuesto global 3, nunca reinicia → tras 3 intentos `FAILED` permanente, `SourceManager._worker` terminaba hilo y `running=False` para siempre → offline crece a 14.
- Sin jitter: 11 cámaras reintentaban simultáneamente → storm.
- Reader bloqueado en `cap.read()` sin timeout → leak `RTSP_READER_THREAD_STUCK`.

**FIX_STREAM_STABILITY** (`source_manager.py:287`, `live_sources.py:664`): worker outer retry con backoff `min(30, 2*1.5^n)+jitter 0-1s` y reintentos ilimitados (no abandono); running permanece `True` durante backoff (RECONNECTING); `live_sources` jitter 0-0.5s en cada reconnect; captura huérfana no liberada desde supervisor (anti doble-free preservado).

### VIEWPORT ZOOM/PAN (BLOCKS F/G/H)

Implementado `build_viewport_display_image` + `_clamp_pan` + `_viewports` por cámara (`scale`, `pan_x`, `pan_y`), `RESET` → 1.0/0,0, drag `ButtonPress-1/B1-Motion/ButtonRelease-1` → PAN cuando `scale>1`, clamp a frame, cursor-centered zoom vía `_last_cursor_pos`, overlay dibujado en source frame antes del crop (BLOCK H).

### GATE físico — FIX aplicado, re-run pendiente del operador

```
# 1) Lanzar con credenciales reales (password solo en memoria del launcher):
#    .\TukeVision.bat   -> el launcher pide usuario/clave DVR (Dahua admin)
# 2) Mantener 30 min; TukeVision ahora escribe con los fixes:
#    evidence/loop_0019a_r2/resource_telemetry.json (0/5/10/20/30m)
#    evidence/loop_0019a_r2/process_exit_forensics.json (WHY/NORMAL)
#    evidence/loop_0019a_r2/runtime_trace.json
# 3) Gate esperado: PROCESS_ALIVE=YES, UI_RESPONSIVE=YES, VIDEO_UPDATES=YES,

---

### DEF-RTSP-FOCUS-04 — REMOVE FOCUS STREAM-SWITCH (2026-08-21)

**VERDAD EMPÍRICA:** `GRID_SUBSTREAM=FUNCIONAL`, `DOUBLE_CLICK_FOCUS=CONGELA`, `FOCUS_STREAM_SWITCH→RECONNECTING` confirmado por operador.

**ROOT_CAUSE:** `TkView._on_click_camera` → `MulticameraRuntime.set_focus(camera)` → `SourceManager.switch_stream(camera,0)` cerraba/reabría RTSP (`RTSPSource.close/open`) sobre la misma cámara; stall 10s → `RECONNECTING` → pérdida señal. `clear_focus()` reabría de nuevo.

**REPARACIÓN:** `scripts/run_multicamera.py:213 set_focus/clear_focus` → tracking de `_focused_camera` solo, **sin** `switch_stream`; `FOCUS_MAIN_AUTO_SWITCH=DISABLED` (soporte MAIN preservado para futuro `OPEN_MAIN_IN_PARALLEL→FIRST_MAIN_FRAME→ATOMIC_SWAP`). `GRID` permanece `SUB` (`subtype=1`) para 15 cámaras; `FOCUS` reutiliza `SUB` vivo; `ZOOM/PAN` solo `build_viewport_display_image` sobre frame anotado.

**GATES FÍSICOS (operador):** 1) GRID 15 continuo, 2) doble clic CAM01 foco sin freeze (`FRAME_AGE` avanza, `RECONNECT_COUNT` igual, `SOURCE_STATE`≠RECONNECTING), 3) volver GRID sin reopen, 4) CAM02/05/07/13, 5) 20 ciclos GRID→FOCUS→ZOOM→PAN→RESET→VOLVER sin `SIGNAL_LOSS`.

**INSTRUMENTACIÓN:** `camera_id/stream_profile/source_state_before/after/frame_timestamp/reconnect_count/reader_thread_id` invariante `reader_before==reader_after` y `reconnect_after==reconnect_before`.

**Pruebas:** `752 passed, 4 skipped` + `ALL_RESOLUTIONS_VALIDATED` harness; no `pytest` como PASS del defecto (DoD exige video físico continuo).

**STATUS:** `ACTIVE_UNTIL_PHYSICAL_FOCUS_CONTINUITY_PASS`
#    RSS acotados, ONLINE/RECONNECTING/ OFFLINE estables, RECONNECTS acotados.
```
Fixes testeados: `752 passed, 4 skipped` + `ALL_RESOLUTIONS_VALIDATED: REAL_UI_VALIDATION=PASS` (harness). El operador re-ejecuta 30 min para cerrar `RUNTIME_MINUTES`.