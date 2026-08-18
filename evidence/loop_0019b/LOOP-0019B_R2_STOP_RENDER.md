# LOOP-0019B-R2 — UNIFORM STOP STATE FOR ALL CAMERA PANELS

**EXECUTION_ID:** LOOP-0019B-R2
**EXECUTOR:** CODEX (opencode)
**MODE:** SURGICAL_UI_FIX
**SCOPE:** STOP_RENDER_ONLY
**GOVERNANCE:** DEC-0042 + OPERATOR_VERIFIABILITY_GATE
**PARENT:** LOOP-0019B (+ R1)
**STATUS:** STOPPED_FOR_OPERATOR_VERIFICATION

## ROOT CAUSE OBSERVADA

Tras STOP: `IDLE` PASS, `0/4 ONLINE` PASS, panel lateral `CLOSED / SYSTEM
IDLE` PASS, CAM-001/CAM-003 OFFLINE, pero CAM-002/CAM-004 conservaban punto
verde sin `CLOSED · LAST FRAME / OFFLINE`.

`STOP_RENDER_NOT_APPLIED_UNIFORMLY_TO_ALL_CAMERA_PANELS`

Causa raíz en el código: `self._stopped_rendered` era una **bandera global**
que `_render_frozen_camera` ponía en `True` tras renderizar la PRIMERA cámara
(CAM-001). Las siguientes (CAM-002, CAM-004) tenían `size`/`frame_index` sin
cambio tras el STOP, y la guarda `if not changed and self._stopped_rendered:
return` las omitía: el canvas conservaba el overlay verde del último render
RUNNING. CAM-003 (sin frame) tomaba la rama placeholder `CLOSED` y por eso
parecía correcta.

## CORRECCIÓN

Centralizada en `apply_stopped_state(panel)`: una única transición para
CAM-001..CAM-004 que deriva SOLO del estado global/runtime `STOPPED` (gris /
CLOSED / online=False / Track, Event, Temporal, Behavior y overlays activos
cleared; último frame permitido como referencia con banda obligatoria
`CLOSED · LAST FRAME / OFFLINE`). La apariencia OFFLINE ya no depende del
último metadata/frame retenido.

`_stopped_rendered` pasa de bandera global a **dict por cámara**
(`{camera_id: False}`) y `frozen_render_required(rendered, camera_id, ...)`
decide por cámara: en el primer pase STOP los cuatro paneles se redibujan
aunque tamaño/índice no cambien, eliminando el sesgo de orden.

## NO TOCADO

RTSP, SourceManager, YOLO, tracking, Behavior, QW-04, layout, resolución,
color, evidencia/clip, renderer único. V1–V8 aprobados sin cambios. Cambios
pre-existentes ajenos (E01_COMPAT) intactos.

## VALIDACIÓN TÉCNICA

- NUEVOS TESTS: 8/8 OK en `tests/test_loop_0019b_r2.py` (4 cámaras con
  metadata distinta → uniformes; frame analítico; frame vivo; detección
  previa → cleared; sin detección; force-render por cámara sin bandera global;
  skip solo de cámaras ya renderizadas; transición centralizada).
- FOCUSED_TESTS: 68/68 OK (UI + QW-04 + controller + entrypoint + r1 + r2).
- FULL_REGRESSION: 476 tests OK (468 baseline + 8 nuevos; 4 skips
  pre-existentes `test_inference_real_backend`).
- COMPILEALL: OK.
- SECRET_SCAN: CLEAN.
- DIFF_CHECK: solo `src/ui/tk_view.py` (sobre cambios de 0019B/R1) +
  `tests/test_loop_0019b_r2.py` (nuevo); resto intacto.
- SMOKE: TkApp real (ventana mapeada) — RUNNING: LIVE, 3/4 ONLINE, botones con
  objetivo exacto; STOP: IDLE, 0/4 ONLINE, Detener disabled, las 4 cámaras sin
  LIVE/OPEN; CAM-001/002/004 (con frame) `CLOSED · LAST FRAME / OFFLINE`,
  CAM-003 (sin frame) placeholder `CLOSED`.
- NEW_REGRESSIONS: 0

## VALIDACIÓN REAL (operador)

`OPERATOR_ENTRYPOINT: TukeVision.bat` — con 4 cámaras: 1) LIVE normal;
2) pulsar `Detener`; 3) dejar pantalla final. Esperado simultáneo:

`IDLE` · `CAMERAS: 0 / 4 ONLINE` · CAM-001..004 `GREY + CLOSED · LAST FRAME /
OFFLINE` · Panel lateral `CLOSED · SYSTEM IDLE` · `Detener` disabled.

`OPERATOR_VERIFICATION_READY: YES`
`OPERATOR_VERIFICATION: PENDING`
`LOOP_STATUS: STOPPED_FOR_OPERATOR_VERIFICATION`