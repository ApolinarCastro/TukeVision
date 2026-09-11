# PHASE-2 CHECKPOINT — CLASIFICACIÓN DEL WORKTREE

**Ejecución:** PHASE-2-CERTIFICATION-CLOSE (MACRO-TUKEVISION-V3) · **Fecha:** 2026-08-28
**Base:** HEAD previo `06d0e6a` (branch `product/loop-0018r-temporal-tracking`) · **Cambios inventariados:** 194

## Suite de tests (pre-commit)

`python -m unittest discover -s tests` → **Ran 779 tests — OK (skipped=4) — 104.8s**

## Clasificación

| Categoría | Count | Decisión de commit |
|---|---|---|
| `src/**` (PERTENECE_A_V3) | 33 | COMMIT |
| `tests/**` (PERTENECE_A_V3) | 38 | COMMIT |
| `scripts/**` (PERTENECE_A_V3 — launcher.py, soak monitors, demos, run_multicamera) | 26 | COMMIT |
| `config/**` (PERTENECE_A_V3 — multistore con `credentials_ref: ENV_*`) | 3 | COMMIT |
| `docs/**` (PERTENECE_A_V3 — handoffs MACRO_CX/OC-04 + esta clasificación) | 6 | COMMIT |
| `TukeVision.bat` (PERTENECE_A_V3 — launcher con credential dialog) | 1 | COMMIT |
| `evidence/**` (EVIDENCE) | 84 | NO COMMIT (queda en disco; RUN-462B04 preservado con manifiesto + hashes SHA-256) |
| `.tukevision_patch_backups/` (TEMPORAL) | 1 | NO COMMIT |
| `quick_stability.py`, `test_catalog.py`, `test_rtsp_direct.py`, `run_test.ps1` (raíz — TEMPORAL/scratch) | 4 | NO COMMIT (duplican convención `tests/`; se conservan en disco) |

## Verificación de seguridad

- Sin secretos en candidatos: los hits de "password" son lógica de redacción, canaries de test
  (`SECRET_CANARY_8F21`) y fixtures dummy; `config/*.json` usa `credentials_ref: ENV_*` sin plaintext.
- Exclusiones aplicadas: `*.bak.py`, `*.mp4`, `*.zip`, `*.log`, `evidence/`, backups, scratch de raíz.

## RUN-462B04

Registrado como `PHYSICAL_EVIDENCE_PRE_CHECKPOINT`:
`evidence/RUN-462B04/PHYSICAL_EVIDENCE_PRE_CHECKPOINT_MANIFEST.md` (hashes SHA-256 de los 4 JSON;
clips ya rotados por retención — observación registrada). NO se reinterpreta como run reproducible
sobre versión limpia; el run de certificación se ejecutará desde este checkpoint.
