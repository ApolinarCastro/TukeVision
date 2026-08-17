# UNIQUE ARTIFACT SCAN FINAL — LOOP-0018U

**Fecha:** 2026-08-16 · **Dirigida** (no auditoría general) · **Origen:** `TukeVision-portable`
**Base de comparación:** BASE `TukeVision` + `archive` (legacy + forensic)

## Resultado

| Categoría | Hallazgos únicos | Clasificación |
|---|---|---|
| `src/` (`.py`) | 0 sin cobertura (todos en BASE o legacy) | — |
| `src/identity/` | 4 archivos únicos | **PRESERVED_DISABLED** (legacy; gobernanza DEC-0013/19/36) |
| `src/retail/trajectory.py`, `src/capture/quality_engine.py`, `src/ui/{tk_view,controller,state}.py`, `src/app/pipeline.py` | 7 únicos | **PRESERVED_IN_LEGACY** (legacy/portable_migrate_0018u) |
| `scripts/` | 5 únicos (test_*) + diagnose_rtsp_channels | **PRESERVED_IN_LEGACY** |
| `config/` | default.json difiere | **SUPERSEDED** (config BASE 16-08 es la autoritativa) |
| `models/` | 0 | **PRESERVED_IN_BASE** (yolo11n.pt idéntico) |
| `docs/` | 0 | **PRESERVED_IN_BASE** (10 idénticos) |
| `install/` | 0 | **PRESERVED_IN_BASE** (6 idénticos) |
| `requirements*.txt`, README, start_tukevision.ps1, test_rtsp.ps1 | 0 | **PRESERVED_IN_BASE** (9/9 hash idéntico) |
| Informes forenses raíz (LOOP-0018B..I, HOTFIX_*, RTSP_HARDENING, stderr/stdout, analyze_cameras, camera_audit, logs, hotfix_backup*, loop0017_backup, processed.mp4) | 73 únicos | **PRESERVED_IN_ARCHIVE** (supplemental, 73/73 MATCH) |
| Evidencia forense núcleo (evidence/loop_0018g..l) | 110 | **PRESERVED_IN_ARCHIVE** (C4, 110/110 MATCH) |
| `instrument_*.py` (3) | consumidos | **DISCARD_CERTIFIED** (marcadores observabilidad integrados en BASE: redact_rtsp_url) |
| `precheck_trace.py`, `check_cv2.py`, `check_ui.py` | consumidos/triviales | **DISCARD_CERTIFIED** |
| `MANIFEST.json` raíz, `PROBAR_TUKEVISION.bat`, `Nuevo Documento de texto.txt` (0 B), `skills-lock.json`, `.agents/` | obsoletos/tooling | **DISCARD_CERTIFIED** |
| `.venv`, `.pytest_cache`, `__pycache__`, `data/temp` | reconstruibles | **DISCARD_CERTIFIED** (excluidos de valor) |

## Veredicto

> **PORTABLE_UNIQUE_BLOCKERS = 0.**
> Todo valor único del portable está preservado en BASE, archive/legacy o
> archive/forensic con hash MATCH. Ningún archivo único sin destino.

— Fin de unique_artifact_scan.md (LOOP-0018U)