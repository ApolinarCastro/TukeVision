# LOOP-0018M-R1 — PRECOMMIT INVENTORY

**EXECUTION_ID:** LOOP-0018M-R1
**Fecha:** 2026-08-16
**BASE_PATH:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`

## Estado Git

- **Branch:** `backport/loop-0018j`
- **HEAD pre-commit:** `cce37452f7fee2fbb00ece232cf25341010fcd99` (esperado `cce3745` → COINCIDE)
- **Staged:** ninguno
- **Untracked:** 1 (backup)

## Archivos modificados

| Archivo | Hash SHA-256 | Clasificación |
|---|---|---|
| `config/default.json` | `4B1A1E5AE141974F02F56DEE6AD492B5FED2A4957FD40D8049440C70264B455F` | E01_AUTHORIZED |
| `src/app/pipeline.py` | `9B93EAB0D5D7B489CB541466F7DC333B4E2225EFA72520A6F64AAB2336461F42` | E01_AUTHORIZED |
| `src/capture/live_sources.py` | `EEA67E3D3252D2E43C15645BC13E9C5D05872C869CF4B83A1A839F709A00295C` | E01_AUTHORIZED |
| `src/ui/controller.py` | `CAE5D822718943A4F0811204DEBD38403B0A444A86C9565FB25534F8D4C1F6D4` | E01_AUTHORIZED |

## Untracked

| Archivo | Hash SHA-256 | Clasificación |
|---|---|---|
| `src/capture/live_sources.BASE_preE01.bak.py` | `99D9DD9B673AE64E3619C499417724662C25D68ED29494C156D125F974C9F575` | BACKUP — GIT_TRACKED=NO, COMMIT_INCLUDED=NO |

## Verificaciones

- `E01_AUTHORIZED`: 4 archivos funcionales (todos los esperados por el alcance §4).
- `BACKUP`: 1 archivo, fuera de staging, NO se commitea.
- `UNRELATED`: 0
- `E02_E05`: 0
- `UNKNOWN`: 0
- Ningún archivo staged antes de FASE G.
- `OPENCV_MODIFIED`: NO
- `FFMPEG_MODIFIED`: NO