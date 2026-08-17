# OFFICIAL BUILD MANIFEST (C3) — LOOP-0018T

**Fecha:** 2026-08-16 · **Fase:** 5 (C3)

| Campo | Valor |
|---|---|
| BUILD_SOURCE_HEAD | cfad93163b9fe1b992e87026b0adbb437c518cee |
| BUILD_PYTHON | Python 3.12.10 (.venv BASE, regenerado en C2) |
| BUILD_RUNTIME | BASE `.venv` (cv2 5.0.0, torch 2.13.0+cpu, ultralytics 8.4.115, supervision 0.29.1, trackers 2.5.0.post0) |
| BUILD_COMMAND | `powershell.exe -ExecutionPolicy Bypass -File install\package.ps1` |
| BUILD_TIMESTAMP | 2026-08-16 |
| BUILD_OUTPUT | `dist\TukeVision\` + `dist\TukeVision-portable.zip` |
| PACKAGE_VERSION | 0.1.0 |
| SPEC_CERTIFIED_BASE | cf876a9 |
| PYTHON_REQUIRED | 3.12.x |
| MODEL_FILENAME | models/yolo11n.pt |
| MODEL_SHA256 | 0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1 |
| REQUIREMENTS_SHA256 | 8E5D54E761F1293AEB3A46F48842B72FC69DCED9057529346DC7F7735CDD433F |
| REQUIREMENTS | ultralytics==8.4.115, supervision==0.29.1, trackers==2.5.0.post0, opencv-python==5.0.0.93 (+ lock) |

## Validación del build

- `install\verify_package.ps1` → **VERIFY_STATUS: OK** (modelo, requirements, archivos críticos, exclusiones).
- `tests\test_portable_package.py` → **14/14 PASS**.
- `tests\test_advance_chain.py` (C1) → **11/11 PASS**.
- Regresión completa con runtime BASE → **370/370 PASS**.
- `git_head` en MANIFEST = **cfad931** (HEAD actual) — se corrige el estado OUTDATED (H2/LOOP-0018S, git_head previo 4e530f3).
- El paquete incluye `src\inference\`, `src\temporal\`, `src\capture\source_manager.py`, `src\observations\activity.py`, `src\app\advance_chain.py`.
- `live_sources.py` del paquete = versión E-01 (git blob 6a9ae7e..., idéntico al fuente).

## Notas de trazabilidad

- PORTABLE_PYTHON_USED_FOR_BUILD = **NO** (build con `.venv` BASE).
- No se referenció ninguna ruta portable en el proceso de build.
- El zip `TukeVision-portable.zip` es el artefacto oficial de distribución
  (nombre heredado del flujo portable, NO una referencia al runtime portable).

— Fin de official_build_manifest.md (LOOP-0018T)