# LOOP-0019B-R1 — CORRECCIÓN DE V8/V9/V10 (EVIDENCIA-CLIP EXACTOS + STOP COHERENTE)

**EXECUTION_ID:** LOOP-0019B-R1
**EXECUTOR:** CODEX (opencode)
**MODE:** SURGICAL_OPERATOR_VERIFICATION_FIX
**GOVERNANCE:** OPERATOR_VERIFIABILITY_GATE (V1–V7 PASS, V8/V9/V10 FAIL pre-R1)
**PARENT:** LOOP-0019B
**STATUS:** STOPPED_FOR_OPERATOR_VERIFICATION

## VEREDICTO OPERADOR (entrada)

| VERIFICACIÓN | RESULTADO PRE-R1 |
|---|---|
| V1 NITIDEZ / V2 COLOR / V3 TAMAÑO / V4 LEGIBILIDAD / V5 DISTRIBUCIÓN / V6 PANEL / V7 CONTROLES | PASS |
| V8 EVIDENCIA-CLIP (abría carpetas genéricas, no el archivo exacto) | FAIL |
| V9 COHERENCIA GENERAL (estado activo retenido tras STOP) | FAIL POST-STOP |
| V10 STOP (detención funcional OK, estado UI no coherente) | FUNCTIONAL_PASS / UI_STATE_FAIL |

## CAMBIOS QUIRÚRGICOS

### 1. `src/ui/tk_view.py` — acciones exactas y STOP coherente

- `_on_open_evidence`: abre el **JPEG exacto** de la última evidencia válida
  (`evidence_ref → absolute_path → os.startfile(file)`). Sin archivo →
  `EVIDENCE_UNAVAILABLE`. Se elimina la apertura genérica de
  `data/runtime_evidence` (`startfile(base)` desaparece).
- `_on_open_clips`: prioridad **revisión seleccionada → clip_evidence_ref →
  MP4 exacto**; si hay revisión sin clip → `review_behavior_signals.bat`
  (`launch_review`); si no hay revisión → `CLIP_REVIEW_UNAVAILABLE`.
- `_render_video` / `_render_frozen_camera`: tras STOP cada cámara muestra su
  último frame congelado **marcado `CLOSED · LAST FRAME / OFFLINE`** (sin
  overlays Track/Event/Temporal/Behavior, dot gris). Sin frame → placeholder
  `CLOSED`.
- `_render_header`: `LIVE→IDLE`, **`CAMERAS: 0 / 4 ONLINE`** con runtime
  detenido (derivado de `online_camera_count(panels, running)`), `FPS: -`.
- `_render_side_panel`: STOP → cada cámara en `CLOSED · SYSTEM IDLE`
  (limpieza de estado activo; alertas/evidencia/clip históricos se conservan).
- `_update_button_states`: `Detener` deshabilitado tras STOP; `Abrir evidencia`
  enabled **solo si existe JPEG válido**; `Abrir clip/revisión` enabled **solo
  si hay MP4 válido o revisión disponible**.
- Helpers puros testeables: `resolve_evidence_path`, `online_camera_count`,
  `stopped_camera_line`, `frozen_overlay_text`, `action_button_states`.

Regla de estado: la UI deriva del estado real del runtime
(`runtime_state=STOPPED → source_state=CLOSED → camera_online_count=0 →
active_analytics_state=CLEARED`). Prohibido `STOPPED backend + OPEN UI`.

### 2. `scripts/run_multicamera.py` — ayudantes de resolución (solo lectura)

- `latest_evidence()` → ruta absoluta del JPEG exacto más reciente.
- `clip_target()` → ruta absoluta del MP4 exacto del caso de revisión
  seleccionado (último registro con `clip_available`).
- `review_available()` → hay casos QW-00 (con o sin clip).
- `launch_review()` → abre `review_behavior_signals.bat`.
- `_resolve_artifact()` / `_review_records()`: resolución segura (sin escape de
  raíz, `evidence_root` resuelto) y lectura tolerante del JSONL.

### 3. `scripts/review_behavior_signals.py` — dataset del runtime

`evidence_directories()` incluye ahora `evidence/loop_0019a_qw04_r2`, para que
`review_behavior_signals.bat` encuentre los registros del runtime sin
variables de entorno adicionales (caso de revisión resoluble).

## NO TOCADO

Pipeline, RTSP, YOLO, tracking, QW-04 backend, resolución, nitidez, color,
layout 2x2, Design System. Cambios pre-existentes ajenos (E01_COMPAT
`max_width=0` en config/live_sources/video_source/controller,
`quality_engine.py`) intactos.

## VALIDACIÓN TÉCNICA

- NUEVOS TESTS: 14/14 OK en `tests/test_loop_0019b_r1.py` (evidencia exacta,
  clip exacto, revisión sin clip, sin revisión, `0/4 ONLINE`, `CLOSED · SYSTEM
  IDLE`, `LAST FRAME / OFFLINE`, botones condicionados, apertura de carpetas
  genéricas eliminada, dataset del review tool).
- FOCUSED_TESTS: 60/60 OK (UI + QW-04 + controller + entrypoint).
- FULL_REGRESSION: 468 tests OK (454 baseline + 14 nuevos; 4 skips
  pre-existentes `test_inference_real_backend`).
- COMPILEALL: OK (`src`, `scripts`, `tests`).
- SECRET_SCAN: CLEAN (archivos del loop sin secretos; hits pre-existentes solo
  en fixtures de prueba de redacción y copias `dist/`).
- DIFF_CHECK: tocados solo `src/ui/tk_view.py`, `scripts/run_multicamera.py`,
  `scripts/review_behavior_signals.py` + `tests/test_loop_0019b_r1.py` (nuevo).
- SMOKE: TkApp real (ventana withdrawn) — RUNNING: 3/4 ONLINE, LIVE, botones
  con objetivo exacto; STOP: 0/4 ONLINE, IDLE, Detener disabled, paneles
  `CLOSED · SYSTEM IDLE`, evidencia/clip disponibles.
- NEW_REGRESSIONS: 0

## OPERADOR

`OPERATOR_ENTRYPOINT: TukeVision.bat`
`OPERATOR_VERIFICATION_READY: YES`
`OPERATOR_VERIFICATION: PENDING`

Re-evalúe V8 (Abrir evidencia → JPEG exacto; Abrir clip/revisión → MP4 exacto o
consola de revisión), V9 y V10 (STOP → IDLE, 0/4 ONLINE, CLOSED, `LAST FRAME /
OFFLINE`, SYSTEM IDLE, botones coherentes) con 4 cámaras reales. El loop cierra
solo cuando el operador confirma los tres.
