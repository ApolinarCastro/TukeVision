# LOOP-0019B — RECUPERACIÓN VISUAL PORTABLE → BASE

**EXECUTION_ID:** LOOP-0019B
**EXECUTOR:** CODEX (opencode)
**MODE:** SURGICAL_REUSE_AND_PRODUCT_UI_RECOVERY
**GOVERNANCE:** DEC-0042 + OPERATOR_VERIFIABILITY_GATE
**BASELINE_G1_G10:** `04abddfc1b6c72a78a045e62049c0dbc936d88c8`
**QW04_TECHNICAL_BASELINE:** `0f214ca169358a0980e1324650d046e53f625557`
**STATUS:** STOPPED_FOR_OPERATOR_VERIFICATION

## PORTABLE SOURCE

`archive/legacy/portable_migrate_0018u/src/ui/tk_view.py` (Command Center,
LOOP-0017B, preserved 16/16 hash-match per LEGACY_MANIFEST.md).

Patrones probados reutilizados:
- `fit_display_size` (aspect-ratio, sin deformación).
- `bgr_frame_to_rgb` (punto único de conversión de color).
- `build_display_image` (BGR→RGB→LANCZOS, escala SOLO copia de presentación).
- Canvas dinámico (llena el área disponible; el video no fuerza el layout).
- Design System oscuro (COLORS, tipografía, jerarquía visual).
- Overlays legibles sin tapar la escena; información secundaria fuera del video.

## MATRIZ PORTABLE vs BASE

| CAPACIDAD | PORTABLE | BASE ACTUAL (pre-0019B) | MEJOR | ACCIÓN |
|---|---|---|---|---|
| Calidad imagen | Canvas dinámico, LANCZOS | Panel fijo 420x245, INTER_AREA | PORTABLE | ADAPT |
| Color | `bgr_frame_to_rgb` único punto | `cv2.cvtColor` único punto | EQUIVALENTE | KEEP (unificado en `bgr_frame_to_rgb`) |
| Escalado | Llenado de área, aspect intacto, cap 1.0 | Letterbox 420x245 downscale-only | PORTABLE (dinámico) | ADAPT |
| Panel cámara | Canvas llena el área | LabelFrame fijo 420x245 | PORTABLE | ADAPT |
| Layout | Header + body + status bar, 1280x720 | Header + 2x2 + lateral, 1120x680 | PORTABLE estructura | ADAPT (2x2 cámaras grandes + lateral + inferior) |
| Información | Intel panel consolidado, overlay mínimo | Texto técnico de 3 líneas encima de cada cámara | PORTABLE | ADAPT (`camera_summary_line` lateral, overlay mínimo) |
| Controles | Detener/evidencia + settings colapsable | Iniciar/Detener/evidencia + selector fuente | HYBRID | ADAPT (Detener + Abrir evidencia + Abrir clip/revisión) |
| Evidencia | Abre `data/evidence` | Abre `evidence_root` real | BASE | KEEP |

## TRAZA DE CALIDAD VISUAL

| ETAPA | ANTES | DESPUÉS |
|---|---|---|
| SOURCE_RESOLUTION | 1280x720 (reportada por operador) | 1280x720 (sin cambios) |
| DECODE_RESOLUTION | 1280x720 (max_width=0, E01_COMPAT) | 1280x720 (sin cambios) |
| ANALYTICS_RESOLUTION | Frame fuente 1280x720 (YOLO internamente a 640) | 1280x720 (sin cambios) |
| UI_FRAME_RESOLUTION | 1280x720 (panel.frame) | 1280x720 (sin cambios) |
| DISPLAY_PANEL_RESOLUTION | Fijo 420x245 → ~420x236 efectivo (16:9) | Dinámico: ~474x266 en ventana 1280x720, crece al maximizar (ej. ~1000x560 por celda en 4K). LANCZOS, aspect intacto, sin upscale |

Pérdida de detalle corregida: el límite artificial `420x245` desapareció; el
panel ahora es el 100% del área real del widget (Canvas) y reescala con la
ventana. Interpolación: INTER_AREA (ANTES) → LANCZOS (DESPUÉS), más nítida.

`FAKE_UPSCALE_USED: NO` — `fit_display_size` capa la escala en 1.0; si el área
supera la fuente, la imagen se muestra a resolución nativa centrada.

## REUTILIZACIÓN QUIRÚRGICA

`src/ui/tk_view.py` (reescrito): reutiliza los helpers probados del portable
manteniendo íntegros los contratos testeados (`fit_frame_to_panel`,
`select_panel_frame`, `annotate_frame`, `panel_status_text`,
`multicamera_control_state`, `TkApp`).

`scripts/run_multicamera.py`: se elimina el valor inventado
`"resolution": "panel 420x245"` → resolución real por cámara; se expone
`clips_available` (solo lectura desde `qw04.summary()`) y `review_target`.

NO se reabrió el backend certificado (pipeline/RTSP/YOLO/tracking intactos).
QW-04: `PRESERVED` (ruta de integración sin cambios).

## VALIDACIÓN TÉCNICA

- FOCUSED_TESTS: 60/60 OK (multicamera_entrypoint, multicamera_view,
  tk_multicamera_renderer, ui_controller, runtime_qw04_integration,
  operational_pipeline, advance_chain).
- FULL_REGRESSION: 454 tests OK (4 skipped pre-existentes:
  `test_inference_real_backend`, requiere modelo/imagen real).
- COMPILEALL: OK.
- SECRET_SCAN: CLEAN (solo flujo getpass pre-existente; cero secretos nuevos).
- DIFF_CHECK: solo `src/ui/tk_view.py` y `scripts/run_multicamera.py` tocados
  por este loop (además de cambios pre-existentes de E01_COMPAT ajenos a 0019B).
- SMOKE: TkApp multicámara 4/4 paneles renderizan; panel lateral y cabecera
  correctos; modo single-source sigue operativo.
- NEW_REGRESSIONS: 0

## OPERADOR

`OPERATOR_ENTRYPOINT: TukeVision.bat`
`OPERATOR_VERIFICATION_READY: YES`
`OPERATOR_VERIFICATION: PENDING`

V1 NITIDEZ / V2 COLOR / V3 TAMAÑO DE VIDEO / V4 LEGIBILIDAD YOLO-TRACK /
V5 DISTRIBUCIÓN 2x2 / V6 PANEL LATERAL / V7 CONTROLES / V8 EVIDENCIA-CLIP /
V9 COHERENCIA GENERAL / V10 STOP — evalúe directamente con `TukeVision.bat`
(4 cámaras reales). El loop solo cierra cuando el operador confirma que BASE
recuperó o superó la calidad visual y la experiencia del portable.