# PORTABLE RECONCILIATION — LOOP-0018U

**Fecha:** 2026-08-16 · **Modo:** CONTROLLED_CLEANUP (verificación final, no re-auditoría)
**Fuentes de verdad:** `evidence/loop_0018s/portable_exit_matrix.md` (44 ítems),
`evidence/loop_0018t/` (estado C1-C4), verificación física 2026-08-16.

## 1. MIGRATE = 13 → RECONCILIADOS (PRESERVED_IN_LEGACY)

Decisión operador (2026-08-16): preservar fuera del runtime BASE en
`archive\legacy\portable_migrate_0018u\` con rutas de origen, hashes y
trazabilidad. Sin importar/cablear/ejecutar. ReID = PRESERVED_DISABLED
(gobernanza DEC-0013/19/36). Incorporación futura vía Technology Ingestion /
PRODUCT ADVANCE uno por uno.

| # matriz | Ítem | Estado | Destino preservación |
|---|---|---|---|
| 1 | src/identity/ | **PRESERVED_DISABLED** | legacy/portable_migrate_0018u/src/identity/ |
| 2 | src/retail/trajectory.py | **PRESERVED_IN_LEGACY** | legacy/.../src/retail/trajectory.py |
| 3 | src/capture/quality_engine.py | **PRESERVED_IN_LEGACY** | legacy/.../src/capture/quality_engine.py |
| 4 | src/ui/tk_view.py | **PRESERVED_IN_LEGACY** | legacy/.../src/ui/tk_view.py |
| 5 | src/ui/controller.py | **PRESERVED_IN_LEGACY** | legacy/.../src/ui/controller.py |
| 6 | src/ui/state.py | **PRESERVED_IN_LEGACY** | legacy/.../src/ui/state.py |
| 7 | src/app/pipeline.py | **PRESERVED_IN_LEGACY** | legacy/.../src/app/pipeline.py |
| 12 | scripts/test_command_center_ui.py | **PRESERVED_IN_LEGACY** | legacy/.../scripts/ |
| 13 | scripts/test_reconnect_accounting.py | **PRESERVED_IN_LEGACY** | legacy/.../scripts/ |
| 14 | scripts/test_rtsp_liveness.py | **PRESERVED_IN_LEGACY** | legacy/.../scripts/ |
| 15 | scripts/test_stderr_suppression.py | **PRESERVED_IN_LEGACY** | legacy/.../scripts/ |
| 16 | scripts/test_ui_visual.py | **PRESERVED_IN_LEGACY** | legacy/.../scripts/ |
| 17 | scripts/diagnose_rtsp_channels.py | **PRESERVED_IN_LEGACY** (⚠️ redacción IP antes de publicar) | legacy/.../scripts/ |

- Copia hash-a-hash: **16/16 archivos SHA-256 MATCH** (FAIL=0).
- Imports/referencias desde producción BASE: **0**.
- **13/13 MIGRATE_RECONCILED.**

## 2. ARCHIVE_FORENSIC = 12 → RECONCILIADOS (PRESERVED_IN_ARCHIVE)

| # matriz | Ítem | Destino | Verificación |
|---|---|---|---|
| 21 | evidence/loop_0018g | archive\forensic\rtsp_double_free_0018\loop_0018g | 110/110 MATCH |
| 22 | evidence/loop_0018i | ...\loop_0018i | 110/110 MATCH |
| 23 | evidence/loop_0018j + r1..r4 | ...\loop_0018j(_r1..r4) | 110/110 MATCH |
| 24 | evidence/loop_0018k | ...\loop_0018k | 110/110 MATCH |
| 25 | evidence/loop_0018l | ...\loop_0018l | 110/110 MATCH |
| 26 | Informes raíz LOOP-0018B..I (8) | archive\forensic\rtsp_double_free_0018_supplemental\ | 73/73 MATCH |
| 27 | HOTFIX_* reports (6) | supplemental | 73/73 MATCH |
| 28 | stderr.txt / stdout.txt | supplemental | 73/73 MATCH |
| 29 | hotfix_backup* / loop0017_backup (4) | supplemental | 73/73 MATCH |
| 30 | logs/ (37) | supplemental\logs | 73/73 MATCH |
| 31 | data/rtsp_channel_diag + processed.mp4 stub | processed.mp4 en supplemental\data\output (rtsp_channel_diag YA inexistente en portable) | 73/73 MATCH |
| 32 | analyze_cameras.py + camera_audit.csv | supplemental | 73/73 MATCH |

- Núcleo forense C4: `FORENSIC_ARCHIVE_MANIFEST.json` 110/110 (source+destination).
- Suplemento: `FORENSIC_SUPPLEMENTAL_MANIFEST.json` 73/73 (source+destination).
- **12/12 ARCHIVE_FORENSIC_RECONCILED.**

## 3. DISCARD = 19 → CONFIRMADOS

Ítems 8,9,10,11,18,19,20,33,34,35,36,37,38,39,40,41,42,43,44: duplicados ya en
BASE (idénticos byte-a-byte), consumidos (instrumentación one-shot), obsoletos
(config/MANIFEST antiguos, launchers con ruta absoluta), reconstruibles
(__pycache__, .venv) o tooling de agente. **Ninguno requerido por runtime,
build, tests, config, model, TES, evidence ni migración futura certificada.**
- **19/19 DISCARD_RECONCILED.**

## 4. Veredicto

> MIGRATE 13/13 · ARCHIVE_FORENSIC 12/12 · DISCARD 19/19 · **44/44 RECONCILED.**
> Ningún ítem queda únicamente en portable. PORTABLE_SAFE_DELETE habilitado
> tras FASE 2 (unique blockers=0).

— Fin de portable_reconciliation.md (LOOP-0018U)