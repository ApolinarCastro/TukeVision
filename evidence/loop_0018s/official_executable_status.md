# OFFICIAL_EXECUTABLE_STATUS — LOOP-0018S

**LOOP:** 0018S · **Fecha:** 2026-08-16 · **Modo:** SOLO LECTURA (inspección; sin rebuild)
**BASE:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision` · **HEAD:** `cfad931` (loop-0018r, 16-08 18:55)
**Fuente:** worker_93 §2 + worker_90 §3 (verificado S4: MANIFEST git_head `4e530f3`, dist sin inference/temporal/source_manager/activity).

---

## 1. ¿Existe build/ejecutable en `dist/`? (HECHOS)

**SÍ existe un paquete, pero NO es un ejecutable compilado** (no hay .exe/.msi; no se usó PyInstaller/cx_Freeze — no hay artefactos de esos toolchains):

| Artefacto | Tamaño | Fecha | Contenido |
|---|---|---|---|
| `dist/TukeVision/` (directorio build) | 80 archivos · ~10.98 MB | 15-08-2026 19:32:08 | App Python portable completa: `src/` (código), `config/default.json` (637 B, 02-08), `docs/` (10), `install/` (6 ps1/md), `scripts/` (13), `models/yolo11n.pt` (5.6 MB), `MANIFEST.json`, `start_tukevision.ps1`, `test_rtsp.ps1`, README, requirements |
| `dist/TukeVision-portable.zip` | 5,119,403 B | 15-08-2026 19:32:10 | 82 entradas; mismo contenido que `TukeVision/` (verificado vía zip API) |

`dist/MANIFEST.json`: `build_date: 2026-08-15`, **`git_head: 4e530f3b…` (commit del 11-08)**, `spec_certified_base: cf876a9`, python 3.12.x.

## 2. Módulos presentes/ausentes en el build (HECHOS)

Módulos `src/` en el build: alerts, app, business, capture, context, detection, diagnostics, events, evidence, incidents, observability, observations, risk, shared, tracking, ui, visualization.

**AUSENTES del build:** `inference/`, `temporal/`, `observations/activity.py`, `capture/source_manager.py`, `identity/`, `retail/`, `capture/quality_engine.py` (verificado en el dir y dentro del zip). Tampoco contiene `tests/`.

Versiones embebidas (fechas dentro del build): `pipeline.py` 09-08 (20,819 B — sin manejo STREAM_LOST), `live_sources.py` 11-08 (13,214 B — versión PRE-E01, idéntica al backup `live_sources.BASE_preE01.bak.py`), `tk_view.py` 11-08 (12,383 B — UI simple), `controller.py` 15-08 19:29 (10,248 B), `scripts/test_rtsp_connection.py` 15-08 19:31.

## 3. Comparación contra HEAD y PRODUCT ADVANCE (HECHOS vs INFERENCIA)

- **HECHO:** HEAD real del repo BASE = `cfad931` (loop-0018r, 2026-08-16 18:55:13). El commit indicado en la task (`5d0d1162`, loop-0018q, 16-08 17:34) existe y es el padre inmediato del HEAD.
- **HECHO:** PRODUCT ADVANCE presente en HEAD (todos con fecha 16-08): `src/inference/` (contract, engines, events, selective), `src/temporal/` (contract, tracker), `src/observations/activity.py`, `src/capture/source_manager.py`, `config/default.json` con secciones `observation`/`inference`/`temporal`, y tests `test_inference_layer.py`, `test_inference_real_backend.py`, `test_temporal_tracking.py`, `test_source_manager.py`, `test_activity_layer.py`, `test_pipeline_equivalence.py`, `test_pipeline_snapshot.py`, `test_portable_package.py`.
- **HECHO:** el build de dist (15-08 19:32, manifest git_head 4e530f3 del 11-08) NO contiene ninguno de esos módulos ni los tests asociados.
- **HECHO:** el build es anterior a E01_COMPAT (`cce3745`/`ccacb3d`, 15-08 19:33 / 16-08) y a todo el PRODUCT ADVANCE (16-08).
- **INFERENCIA (baja incertidumbre):** el build se generó la tarde del 15-08 a partir de un snapshot previo al PRODUCT ADVANCE y previo a la UI Command Center portable; los únicos componentes de esa fecha son `controller.py` y `test_rtsp_connection.py` (15-08 19:29-19:31).
- **HECHO adicional:** `dist/` está en `.gitignore` del repo; el git status del HEAD muestra solo 2 ítems sin commitear (`evidence/loop_0018m_r1/`, `src/capture/live_sources.BASE_preE01.bak.py`) — el build nunca fue versionado.

## 4. Clasificación

> **OUTDATED** — `dist/` existe y es un paquete portable funcional (zip + carpeta), pero su contenido corresponde a un snapshot del **15-08-2026 (git_head `4e530f3`, 11-08)**, **anterior a PRODUCT ADVANCE** (inference, temporal, activity, source_manager — todos del 16-08) y anterior a los módulos únicos de portable (identity/retail/quality_engine/Command Center UI). Por lo tanto **NO incluye las capacidades actuales del HEAD** (`cfad931`) y **no es CERTIFIED**.

**Para certificar (acción futura, NO de este LOOP):** rebuild desde HEAD (cfad931 o el HEAD aprobado) incluyendo `src/inference/`, `src/temporal/`, `src/observations/activity.py`, `src/capture/source_manager.py`, tests asociados, config actualizada y MANIFEST.json con `git_head` correcto; decidir explícitamente si se incorporan también identity/retail/quality_engine/Command-Center (ver `portable_exit_matrix.md`) antes de empaquetar. Verificación final con `verify_package.ps1` + secret scan post-build (0 leaks).

## 5. Anexo — Estado git BASE (HECHO)

- HEAD: `cfad93163b9fe1b992e87026b0adbb437c518cee` — loop-0018r (16-08 18:55)
- `5d0d1162f2320c9e53da46e2f10244d64698024d` — loop-0018q (16-08 17:34), ancestro directo
- Backports recientes ya aplicados en BASE: `cce3745` (backport contrato RTSP + LOOP-0018J), `ccacb3d` (consolidación E01), `fa5b14f` (SourceManager multicamera4), `4e530f3` (fix máscara password UI)

— Fin de official_executable_status.md (LOOP-0018S)
