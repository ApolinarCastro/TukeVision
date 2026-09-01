# PORTABLE_EXIT_MATRIX — LOOP-0018S

**LOOP:** 0018S · **Fecha análisis:** 2026-08-16 (GMT-4) · **Modo:** SOLO LECTURA (no se ejecutó app, no se abrieron cámaras/RTSP/DVR, no se modificó ni borró nada)
**Alcance portable (LABORATORY/FORENSIC):** `C:\Users\ASUS Zenbook\Documents\TukeVision-portable`
**BASE (oficial):** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision` · **HEAD:** `cfad931`
**Fuente:** worker_93 §1 + **corrección S4 (conteo definitivo)**.
**Convención de redacción:** IP pública real del DVR = `[DVR_HOST]` (nunca en claro); IP privada real = `[IP_LAN]`; IP de documentación RFC 5737 = `[IP_TESTNET]`; canarios de prueba referidos sin reproducir el literal. **Canario de trazado RTSP: ausente.**

---

## 1.0 Resumen ejecutivo (CORREGIDO S4)

El portable contiene **exactamente 3 módulos de código únicos de alto valor** no integrados en BASE: `src/identity/` (ReID Fase 1), `src/retail/trajectory.py` (inteligencia retail LOOP-0017E) y `src/capture/quality_engine.py`. Además contiene la **UI Command Center multicanal** (`src/ui/tk_view.py` 43 KB vs 12 KB en BASE) con su controlador/estado ampliados. El resto del código portable ya está integrado en BASE (12 módulos idénticos byte a byte; `live_sources.py` hardening/reader-thread/trace YA presente en BASE — verificado). Todo el material forense (evidencia LOOP-0018 g/l, informes, backups, logs, dumps) → `ARCHIVE_FORENSIC`. La sección 1.3 lista credenciales/IPs que deben redactarse antes de cualquier migración.

**Conteo oficial (44 ítems): 13 MIGRATE / 12 ARCHIVE_FORENSIC / 19 DISCARD.** *Nota S4: la prosa original de worker_93 declaraba 11/10/23; la tabla (fuente de verdad) da 13/12/19. Corregido en este entregable y en los bloques TES derivados.*

## 1.1 Comparación estructural portable vs BASE (HECHOS)

| Dimensión | PORTABLE | BASE (HEAD cfad931) |
|---|---|---|
| Módulos `src/` | 18 dirs (13 con código) | 18 dirs (15 con código) |
| Solo en portable | `identity/` (4 .py, 14-08), `retail/trajectory.py` (14-08), `capture/quality_engine.py` (14-08) | — |
| Solo en BASE | `inference/` (4 .py, 16-08), `temporal/` (3 .py, 16-08), `capture/source_manager.py` (16-08), `observations/activity.py` (16-08) | — |
| Idénticos byte-a-byte (MD5) | alerts, business, context, detection, diagnostics, events, evidence, observability, observations(engine/models), risk, tracking, capture/{rtsp_url,video_source}, README, requirements*, start_tukevision.ps1, test_rtsp.ps1, docs/ (10), install/ (6), scripts/ (12 de 13) | — |
| Difieren (MD5) | `app/pipeline.py` (586 vs 545 líneas), `capture/live_sources.py` (755 vs 773), `ui/tk_view.py` (43 KB vs 12 KB), `ui/controller.py` (302 vs 277), `ui/state.py` (96 vs 92), `scripts/test_rtsp_connection.py` (3936 vs 3919 B) | — |
| tests/ | NO existe (los "tests" viven en `scripts/`) | `tests/` con 24 archivos |
| config/default.json | 751 B (14-08, sin secciones observation/inference/temporal) | 1649 B (16-08, con observation/inference/temporal) |
| evidence/ | loop_0018g, i, j, j_r1..r4, k, l | loop_0018m_r1, n, o, p, q, r |
| git | sin repo | HEAD `cfad931` (loop-0018r); `5d0d1162` (loop-0018q) ancestro directo |

## 1.2 Tabla de decisión (44 ítems)

| # | Artefacto portable | ¿En BASE? | ¿Único? | Valor | Decisión | Razón |
|---|---|---|---|---|---|---|
| 1 | `src/identity/` (encoder, identity_manager, matcher, `__init__`, 14-08) | NO | SÍ | **ALTO** (ReID F1) | **MIGRATE** | Módulo completo y autocontenido; sin tests dedicados en portable. Integración parcial ya existe en `app/pipeline.py` portable. ⚠️ Requiere DEC por gobernanza (DEC-0013/0019/0036) antes de activar. |
| 2 | `src/retail/trajectory.py` (14-08) | NO | SÍ | ALTO (flow IN/OUT/INSIDE, LOOP-0017E) | **MIGRATE** | Módulo único referenciado por pipeline portable (flow_entries/flow_exits/flow_currently_inside). |
| 3 | `src/capture/quality_engine.py` (14-08) | NO | SÍ | MEDIO-ALTO (métricas de calidad de frame) | **MIGRATE** | Único en portable; verificar dependencias antes de integrar. |
| 4 | `src/ui/tk_view.py` (43 KB, Command Center) | SÍ pero 12 KB (11-08, versión simple) | SÍ (versión evolucionada) | **ALTO** (grid multicanal, selector canal 1/5/7, fullscreen, panel intel/settings/status bar) | **MIGRATE (con adaptación)** | Requiere adaptación contra SourceManager de BASE (riesgo de divergencia). Limpio de credenciales (verificado). |
| 5 | `src/ui/controller.py` (302 vs 277 lín.) | SÍ (versión 16-08) | Parcial (29 líneas extra) | MEDIO | **MIGRATE (parcial)** | Extraer solo deltas (contadores people/active_tracks, snapshot de cámaras); NO sobrescribir controller BASE. |
| 6 | `src/ui/state.py` (96 vs 92 lín.) | SÍ | Parcial (4 líneas) | BAJO | **MIGRATE (parcial)** | Delta trivial; migrar junto con controller/tk_view. |
| 7 | `src/app/pipeline.py` (586 vs 545 lín.) | SÍ (16-08) | Parcial (imports retail+identity; campos flow/identity_matches) | MEDIO | **MIGRATE (parcial)** | NO sobrescribir pipeline BASE: extraer bloques retail (TrajectoryStore) e identity y re-integrarlos sobre el pipeline 16-08. |
| 8 | `src/capture/live_sources.py` (755 lín., 15-08) | SÍ (773 lín., 16-08) | NO (BASE ya integró) | — | **DISCARD** | Ya migrado vía backport LOOP-0018J/E01. Recomendación: diff fino previo. |
| 9 | 12 módulos idénticos (alerts, business, context, detection, diagnostics, events, evidence, observability, observations, risk, tracking, capture/rtsp_url+video_source) | SÍ (idénticos MD5) | NO | — | **DISCARD** | Duplicados exactos ya en BASE. |
| 10 | `src/incidents/`, `src/shared/`, `src/visualization/` (vacíos) | SÍ (vacíos) | NO | — | **DISCARD** | Dirs vacíos. |
| 11 | `__pycache__/` (todos) | — | — | — | **DISCARD** | Reconstruible. |
| 12 | `scripts/test_command_center_ui.py` (14 KB) | NO | SÍ | ALTO (14 tests CCUI-01..17) | **MIGRATE** | Único; valida la UI del #4. |
| 13 | `scripts/test_reconnect_accounting.py` (10.8 KB) | NO | SÍ | ALTO (política reconexión LOOP-0018A) | **MIGRATE** | Único; cubre comportamiento ya backporteado sin tests en BASE. |
| 14 | `scripts/test_rtsp_liveness.py` (14.9 KB) | NO | SÍ | ALTO (liveness/stall RTSP) | **MIGRATE** | Único. |
| 15 | `scripts/test_stderr_suppression.py` (13.2 KB) | NO | SÍ | ALTO (hardening stderr LOOP-0018D) | **MIGRATE** | Único. |
| 16 | `scripts/test_ui_visual.py` (9.9 KB) | NO | SÍ | MEDIO | **MIGRATE (opcional)** | Valor medio; consolidar con test_ui_controller de BASE. |
| 17 | `scripts/diagnose_rtsp_channels.py` (16 KB) | NO | SÍ | MEDIO | **MIGRATE con redacción OBLIGATORIA** | Contiene IP real del DVR (`[DVR_HOST]`) + usuario "admin" (password solo por getpass). Redactar antes de migrar. |
| 18 | `scripts/test_trace_observability.py` (9.8 KB) | SÍ (idéntico) | NO | — | **DISCARD** | Idéntico a BASE. ⚠️ La copia portable contiene un canario de prueba (fixture) — descartar sin propagar. |
| 19 | `scripts/test_rtsp_connection.py` (3936 B) | SÍ (3919 B, 15-08 19:31) | Versión distinta | BAJO | **DISCARD** | Versión BASE más nueva; portable contiene `[IP_LAN]` de ejemplo. |
| 20 | Otros 11 scripts comunes | SÍ (idénticos) | NO | — | **DISCARD** | Ya en BASE. |
| 21 | `evidence/loop_0018g` (dumps heap) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Dumps de corrupción de heap nativo (LOOP-0018G). |
| 22 | `evidence/loop_0018i` (windbg/dumps/config) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Análisis WinDbg crash nativo (LOOP-0018H/I). |
| 23 | `evidence/loop_0018j` + `j_r1..r4` (auditoría backport, JSONs 5-11 MB) | NO | SÍ | Forense + referencia | **ARCHIVE_FORENSIC** | Baselines/inventarios/hashes pre-backport (10 MB+); conservar como registro. |
| 24 | `evidence/loop_0018k` (repros E01 race) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Repro de carrera nativa + hardening lifecycle. |
| 25 | `evidence/loop_0018l` (recertificación física) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Recertificación RTSP física 16-08. |
| 26 | Informes raíz `LOOP-0018B..I_SUMMARY/CERTIFICATION/DIAGNOSTIC/DISCRIMINANT/FORENSICS.md` (8) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Contienen IP real del DVR en texto plano (URLs mayormente redactadas). Redactar antes de publicar/archivar externamente. |
| 27 | `HOTFIX_RTSP_001_REPORT/BACKPORT`, `HOTFIX_CHANNEL_SELECTOR_*`, `HOTFIX_RTSP_PATH_FIX_*` (5), `RTSP_HARDENING_MONITOR_REPORT.md` | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Registros de hotfix; uno contiene IP real y un canario de prueba. |
| 28 | `stderr.txt`, `stdout.txt` (14-08) | NO | SÍ | Forense (LOOP-0018D) | **ARCHIVE_FORENSIC** | Evidencia de supresión de stderr. |
| 29 | `hotfix_backup/`, `hotfix_backup_channel_selector/`, `hotfix_backup_trace_001/`, `loop0017_backup/` | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Snapshots pre-cambio (4 dirs, 14 archivos). |
| 30 | `logs/` (36 .log, 12-08 → 16-08) | NO | SÍ | Forense | **ARCHIVE_FORENSIC** | Contienen IP real del DVR. Evidencia runtime. Redactar antes de publicación. |
| 31 | `data/rtsp_channel_diag/`, `data/processed.mp4` (257 B stub) | NO | SÍ | Bajo | **ARCHIVE_FORENSIC** | Restos de diagnóstico de canales. |
| 32 | `analyze_cameras.py`, `camera_audit.csv` (14-08) | NO | SÍ | Bajo (sin IPs — verificado) | **ARCHIVE_FORENSIC** | Auditoría de cámaras física; sin credenciales. |
| 33 | `instrument_controller.py`, `instrument_live_sources.py`, `instrument_tk_view.py` | NO | SÍ | Consumido | **DISCARD** | Herramientas one-shot LOOP-0015-TRACE; sus marcadores YA están en BASE. |
| 34 | `precheck_trace.py` | NO | SÍ | Consumido | **DISCARD** | Contiene canario de prueba; verificación ya realizada. No migrar. |
| 35 | `check_cv2.py`, `check_ui.py` | NO | SÍ | Bajo | **DISCARD** | Chequeos triviales con rutas absolutas al portable. |
| 36 | `config/default.json` (751 B) | SÍ (1649 B, 16-08) | NO | — | **DISCARD** | Superado por config BASE. |
| 37 | `MANIFEST.json` (raíz) | SÍ (dist tiene el suyo) | NO | — | **DISCARD** | Apunta a git_head 4e530f3 (11-08), obsoleto. |
| 38 | `PROBAR_TUKEVISION.bat` | NO | SÍ | Bajo | **DISCARD** | Launcher manual con ruta absoluta; BASE usa start_tukevision.ps1. |
| 39 | `Nuevo Documento de texto.txt` (0 B) | NO | SÍ | Nulo | **DISCARD** | Archivo vacío. |
| 40 | `README.md`, `requirements.txt`, `requirements.lock.txt`, `start_tukevision.ps1`, `test_rtsp.ps1` | SÍ (idénticos) | NO | — | **DISCARD** | Duplicados. |
| 41 | `models/yolo11n.pt` (5.6 MB) | SÍ (mismo archivo) | NO | — | **DISCARD** | Ya en BASE. |
| 42 | `docs/` (10), `install/` (6) | SÍ (idénticos) | NO | — | **DISCARD** | Duplicados. |
| 43 | `.venv/`, `.pytest_cache/` | — | — | — | **DISCARD** | Reconstruible; no inventariar en detalle. |
| 44 | `.agents/` (skill ui-ux-pro-max + catálogos) | NO | SÍ | Nulo (tooling de agente) | **DISCARD** | No es artefacto del proyecto. |

**Balance CORREGIDO (S4): MIGRATE = 13 · ARCHIVE_FORENSIC = 12 · DISCARD = 19 · TOTAL = 44.** *(La prosa original 11/10/23 de worker_93 era un error de resumen; la tabla es la fuente de verdad. Los MIGRATE "con adaptación/parcial/opcional/con redacción" (filas 4,5,6,7,16,17) están contabilizados dentro de los 13.)*

## 1.3 Credenciales e IPs en portable (limpieza previa a migración) — REDACTADO

| Archivo | Hallazgo (redactado) | Clase | Acción previa a migrar |
|---|---|---|---|
| `scripts/diagnose_rtsp_channels.py` | `rtsp://[DVR_HOST]:554/cam/realmonitor` + usuario "admin" (línea 209); password SOLO runtime vía getpass | IP pública real del DVR + usuario | Redactar IP (placeholder `[DVR_HOST]`); conservar patrón. |
| `scripts/test_trace_observability.py` | `HOST = "rtsp://[DVR_HOST]:554/cam/realmonitor"` | IP pública real | Redactar IP. |
| `scripts/test_secret_leak.py` | `[DVR_HOST]`, `[IP_LAN]` (IP privada real), `[IP_TESTNET]`; contraseñas fixture falsas; canario de prueba | IPs reales + fixtures | Redactar IPs reales; no propagar canarios. |
| `scripts/test_rtsp_connection.py` | `[IP_LAN]` (IP privada real de ejemplo) + `--username admin` (ejemplo) | IP LAN real de ejemplo | Redactar. (Archivo en DISCARD, #19.) |
| `scripts/test_channel_selector.py`, `test_command_center_ui.py` | Solo `[IP_TESTNET]` (192.0.2.10, RFC 5737) + canario de canal | Seguras (documentación) | Sin redacción necesaria; limpiar canario opcional. |
| `logs/*.log` (36) | IP real del DVR presente | IP pública real | Redactar antes de publicar (ARCHIVE_FORENSIC interno OK). |
| `LOOP-0018C`, `-C-R1`, `-E`, `-F`, `-H`, `-I`, `HOTFIX_RTSP_PATH_FIX_REPORT`, `HOTFIX_RTSP_001_REPORT`, `RTSP_HARDENING_MONITOR_REPORT` | IP real del DVR en texto plano; URLs RTSP ya redactadas | IP pública real | Redactar IP antes de archivo externo; sin contraseñas (verificado). |
| `precheck_trace.py`, `HOTFIX_RTSP_PATH_FIX_REPORT.md`, `scripts/test_rtsp_path_fix.py`, `scripts/test_trace_observability.py` | Canario de verificación LOOP-0015-TRACE (fixture) | Canario de prueba | No migrar a BASE; es marcador de verificación, no secreto real. |
| `src/ui/tk_view.py`, `src/ui/controller.py`, `src/app/pipeline.py`, `src/capture/live_sources.py`, `src/capture/quality_engine.py`, `src/identity/*`, `src/retail/*`, `src/ui/state.py` | **0 hits** (verificado) | Limpios | Ninguna. |

**Conclusión credenciales:** no se encontraron contraseñas reales en texto plano (el único flujo de password es getpass en runtime). El riesgo real es la **IP pública del DVR**, presente en 4 scripts + 36 logs + 9 informes. Antes de cualquier MIGRATE a un repo público/remoto: redactar la IP real y las IPs LAN, y eliminar canarios de prueba. **El canario de trazado RTSP nunca se propaga.**

## 1.4 Reglas de ejecución

- Ningún MIGRATE se ejecuta en LOOP-0018S (ronda SOLO LECTURA). Cada migración requiere su propio loop con gates y regresión completa.
- MIGRATE de `src/identity/` (E-03) requiere además DEC humana explícita (gobernanza DEC-0013/0019/0036).
- Redacción de IPs/canarios OBLIGATORIA antes de migrar (sección 1.3).

— Fin de portable_exit_matrix.md (LOOP-0018S)
