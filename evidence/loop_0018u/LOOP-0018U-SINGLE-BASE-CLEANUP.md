# LOOP-0018U — FINAL ROOT CLEANUP + SINGLE-BASE TRANSITION

**EXECUTION_ID:** LOOP-0018U · **MODE:** CONTROLLED_CLEANUP · **Fecha:** 2026-08-16
**Parent:** LOOP-0018T · **Branch:** `product/loop-0018r-temporal-tracking`

## 1. Resumen

Eliminación controlada de las 3 estructuras redundantes autorizadas tras
preservación íntegra de su valor único y certificación del BASE antes y después
del borrado. Resultado: **base única operativa**, `ONE_CODEBASE=YES`, TES y
archive intactos, ejecutable oficial certificado.

## 2. Preservación (antes del borrado)

- **MIGRATE 13/13** → `archive\legacy\portable_migrate_0018u\` (16 archivos,
  hash 16/16 MATCH; rutas de origen, trazabilidad; 0 imports desde producción;
  **ReID = PRESERVED_DISABLED** por gobernanza DEC-0013/19/36). DEC-0039.
- **ARCHIVE_FORENSIC 12/12** → núcleo `archive\forensic\rtsp_double_free_0018\`
  (110/110 MATCH) + suplemento `rtsp_double_free_0018_supplemental\` (73/73
  MATCH: informes LOOP-0018B..I, HOTFIX_*, RTSP_HARDENING, stderr/stdout, logs,
  hotfix_backup*, loop0017_backup, analyze_cameras, camera_audit, processed.mp4).
- **DISCARD 19/19** → confirmados (duplicados en BASE, consumidos, obsoletos o
  reconstruibles; no requeridos por runtime/build/tests/config/model/TES/
  evidence/ingesta futura).

## 3. Eliminación (autorizada, ruta exacta, una a la vez)

1. `TukeVision_RTSP_TestInstall` → DELETED (ausente confirmado)
2. `TukeVision_TestInstall` → DELETED (ausente confirmado)
3. `TukeVision-portable` → DELETED (ausente confirmado)

BASE/TES/archive verificados intactos tras cada eliminación. Sin locks, sin
forzar, sin comodines amplios.

## 4. Certificación post-delete

- Regresión: **370/370 PASS** (25.1s) — sin regresiones nuevas.
- Compileall exit 0 · Import smoke PASS · Secret leak 0.
- Executable startup + clean shutdown PASS (STOPPED_BY_USER); zip SHA256
  `E4DC8CA8…` sin cambio.
- PORTABLE_RUNTIME_REFERENCES = 0 (2 hits = nombre del artefacto
  `TukeVision-portable.zip` en package.ps1, no path).

## 5. Estructura final

```
C:\Users\ASUS Zenbook\Documents\TukeVision\
├── TukeVision\   (BASE AUTORITATIVO, runtime único)
├── TES\          (gobernanza/Obsidian)
└── archive\      (preservación: forensic + legacy)
```

## 6. Registros canónicos

- ONE_CODEBASE = **YES**
- BASE_RUNTIME = **AUTHORITATIVE**
- PORTABLE_REMOVED = **YES** · RTSP_TESTINSTALL_REMOVED = **YES** ·
  TESTINSTALL_REMOVED = **YES**
- FORENSIC_ARCHIVE = **PRESERVED**
- OFFICIAL_EXECUTABLE = **CERTIFIED**
- BASE_CHECKPOINT = **22dc73e**
- PRODUCT_PHASE = **PRODUCT_ADVANCE**

## 7. Restricciones respetadas

No se agregó capacidad funcional (G35); 0 dependencias nuevas (G36); sin tocar
OpenCV/FFmpeg/Torch/Ultralytics (G37); sin merge (G38); sin push (G39);
evidencia completa (G40). No se abrió P1 ni nueva arquitectura ni radar.

---

# SALIDA OBLIGATORIA

- EXECUTION_ID: LOOP-0018U
- MODE: CONTROLLED_CLEANUP
- BASE_PATH: `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
- BASE_HEAD_PRE: `22dc73e8bf107e2c7b57bcad6aa3b4c468a77e4a`
- BASE_HEAD_POST: `22dc73e8bf107e2c7b57bcad6aa3b4c468a77e4a`
- BASE_RUNTIME: Python 3.12.10 (.venv BASE, operativo)
- OFFICIAL_EXECUTABLE: `dist/TukeVision-portable.zip` (4.93 MB, SHA256 `E4DC8CA8BC355D2BDFC23EF77BC1398551DA5EA1167C9A17313D7CAF997FB2C3`)
- PREDELETE_REGRESSION: **370/370 PASS**
- POSTDELETE_REGRESSION: **370/370 PASS**
- NEW_REGRESSIONS: **0**
- COMPILEALL: **PASS** (exit 0)
- SECRET_LEAK: **0**
- MIGRATE_RECONCILED: **13/13**
- ARCHIVE_FORENSIC_RECONCILED: **12/12**
- DISCARD_RECONCILED: **19/19**
- PORTABLE_UNIQUE_BLOCKERS: **0**
- PORTABLE_SAFE_DELETE: **YES**
- PORTABLE_REMOVED: **YES**
- RTSP_TESTINSTALL_SAFE_DELETE: **YES**
- RTSP_TESTINSTALL_REMOVED: **YES**
- TESTINSTALL_SAFE_DELETE: **YES**
- TESTINSTALL_REMOVED: **YES**
- FORENSIC_ARCHIVE_PATH: `archive\forensic\rtsp_double_free_0018\` (+ supplemental)
- FORENSIC_ARCHIVE_INTACT: **YES**
- BASE_OPERATES_WITHOUT_PORTABLE: **YES**
- PORTABLE_RUNTIME_REFERENCES: **0**
- FINAL_ROOT_STRUCTURE: **TukeVision + TES + archive** (canonical)
- ONE_CODEBASE: **YES**
- TES_UPDATED: **YES** (PROJECT_STATUS, DEVELOPMENT_LOG, BACKLOG, DECISIONS/DEC-0039)
- FUNCTIONAL_CODE_MODIFIED: **NO**
- NEW_DEPENDENCIES: **0**
- MERGE_EXECUTED: **NO**
- PUSH_EXECUTED: **NO**
- **FINAL_VERDICT: `SINGLE_BASE_STRUCTURE_CERTIFIED`**
- LOOP_STATUS: **STOPPED**

— Fin de LOOP-0018U-SINGLE-BASE-CLEANUP.md