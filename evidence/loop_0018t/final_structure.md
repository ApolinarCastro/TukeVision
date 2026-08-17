# FINAL CANONICAL STRUCTURE — LOOP-0018T

**Fecha:** 2026-08-16 · Estado de la estructura canónica tras C1-C4.

## 1. BASE (oficial, runtime) — `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`

```
.venv/        runtime regenerado (Python 3.12.10, C2)
config/       default.json con observation/inference/temporal (C1)
dist/         TukeVision\ + TukeVision-portable.zip (C3, MANIFEST cfad931)
docs/  install/  scripts/  models/  logs/  data/  tests/  src/  evidence/
src/          18 dirs (15 con código); incluye inference/, temporal/,
              capture/source_manager.py, observations/activity.py,
              app/advance_chain.py (C1), capture/live_sources.py (E-01)
evidence/     loop_0018m_r1, n, o, p, q, r, s, t
```

HEAD: `cfad931` · Regresión 370/370 · PORTABLE_PYTHON_USED=NO.

## 2. TES (gobernanza) — `C:\Users\ASUS Zenbook\Documents\TukeVision\TES`

Obsidian vault con 00_Dashboard, 01_Vision, 02_Product, 03_Architecture,
03_Business, 04_Decisions, 05_Specs, 06_Research, 07_Backlog, 08_Journal,
09_Resources. Actualización LOOP-0018T en FASE 14.

## 3. archive (preservación) — `C:\Users\ASUS Zenbook\Documents\TukeVision\archive`

```
archive\forensic\rtsp_double_free_0018\
  loop_0018g   (dumps heap, logs)
  loop_0018i   (config, dumps, logs, windbg)
  loop_0018j   loop_0018j_r1..r4   (baselines backport)
  loop_0018k   (repros E01 race)
  loop_0018l   (recertificación física)
  FORENSIC_ARCHIVE_MANIFEST.json  (110/110 SHA-256 MATCH)
```
Núcleo forense del double free **independiente del portable** (C4).

## 4. Despliegues de prueba (NO canónicos)

- `TukeVision_RTSP_TestInstall`, `TukeVision_TestInstall` → SAFE_TO_DELETE_CANDIDATE (FASE 12).
- `TukeVision-portable` (LABORATORY/FORENSIC) → preservado; no es runtime (PHASE 11: NO borrar).

## 5. Declaración de estructura

- **Canonical structure estable y reproducible** (BASE + TES + archive).
- **BASE_RUNTIME_INDEPENDENT_FROM_PORTABLE = YES**.
- **FORENSIC_EVIDENCE_INDEPENDENT_FROM_PORTABLE = YES**.
- No se crearon directorios huérfanos; la distribución del paquete (dist) es
  el único artefacto de despliegue oficial.

— Fin de final_structure.md (LOOP-0018T)