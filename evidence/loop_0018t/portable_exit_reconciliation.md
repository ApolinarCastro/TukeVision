# PORTABLE EXIT RECONCILIATION — LOOP-0018T

**Fecha:** 2026-08-16 · **Base:** `C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision`
**Portable:** `C:\Users\ASUS Zenbook\Documents\TukeVision-portable` (LABORATORY/FORENSIC)
**Matriz de referencia:** `evidence/loop_0018s/portable_exit_matrix.md` (44 ítems: 13 MIGRATE / 12 ARCHIVE_FORENSIC / 19 DISCARD)

## 1. Estado de los 44 ítems (conciliación)

### MIGRATE = 13 — NO ejecutados en este loop (requieren loops propios + DEC)

| # matriz | Ítem | Estado en LOOP-0018T |
|---|---|---|
| 1 | src/identity/ (ReID F1) | **PENDIENTE** — requiere DEC gobernanza (DEC-0013/0019/0036) |
| 2 | src/retail/trajectory.py | **PENDIENTE** — loop de migración propio |
| 3 | src/capture/quality_engine.py | **PENDIENTE** |
| 4 | src/ui/tk_view.py (Command Center) | **PENDIENTE** — requiere adaptación vs SourceManager BASE |
| 5 | src/ui/controller.py (deltas) | **PENDIENTE** — extraer solo deltas |
| 6 | src/ui/state.py (delta) | **PENDIENTE** |
| 7 | src/app/pipeline.py (bloques retail/identity) | **PENDIENTE** |
| 12 | scripts/test_command_center_ui.py | **PENDIENTE** |
| 13 | scripts/test_reconnect_accounting.py | **PENDIENTE** |
| 14 | scripts/test_rtsp_liveness.py | **PENDIENTE** |
| 15 | scripts/test_stderr_suppression.py | **PENDIENTE** |
| 16 | scripts/test_ui_visual.py | **PENDIENTE (opcional)** |
| 17 | scripts/diagnose_rtsp_channels.py | **PENDIENTE** — redacción IP obligatoria |

> Regla (matriz §1.4): ninguna migración se ejecuta sin su propio loop + regresión.
> LOOP-0018T no migra; solo reconcilia y deja el material preservado en portable.

### ARCHIVE_FORENSIC = 12 — núcleo double-free archivado en C4; resto preservado en portable

| # matriz | Ítem | Estado en LOOP-0018T |
|---|---|---|
| 21 | evidence/loop_0018g (dumps heap) | **ARCHIVADO (C4)** ✓ 110/110 hashes |
| 22 | evidence/loop_0018i (windbg/dumps) | **ARCHIVADO (C4)** ✓ |
| 23 | evidence/loop_0018j + j_r1..r4 | **ARCHIVADO (C4)** ✓ |
| 24 | evidence/loop_0018k (repros E01) | **ARCHIVADO (C4)** ✓ |
| 25 | evidence/loop_0018l (recert física) | **ARCHIVADO (C4)** ✓ |
| 26 | Informes raíz LOOP-0018B..I (8) | Preservado en portable (no del scope C4; archivo futuro opcional) |
| 27 | HOTFIX_* reports (6) | Preservado en portable |
| 28 | stderr.txt / stdout.txt | Preservado en portable |
| 29 | hotfix_backup* / loop0017_backup (4) | Preservado en portable |
| 30 | logs/ (36-37) | Preservado en portable (IP DVR redactable antes de publicar) |
| 31 | data/rtsp_channel_diag + processed.mp4 stub | Preservado en portable |
| 32 | analyze_cameras.py + camera_audit.csv | Preservado en portable |

### DISCARD = 19 — sin acción (nada se borra)

Ítems 8,9,10,11,18,19,20,33,34,35,36,37,38,39,40,41,42,43,44 = duplicados ya en BASE,
consumidos, obsoletos o reconstruibles. **No se borra nada del portable.**

## 2. Verificación física

- Portable: 36 archivos raíz, 19 scripts, 10 docs, 6 install, 37 logs, 4 hotfix backups, 18 .md raíz.
- Evidencia forense C4: **110 archivos** copiados a
  `archive\forensic\rtsp_double_free_0018\` con **100% hash SHA-256 MATCH**.
- FORENSIC_EVIDENCE_INDEPENDENT_FROM_PORTABLE = **YES** (el núcleo forense del
  double free sobrevive sin el portable).

## 3. Veredicto de eliminación (SOLO recomendación — NO se ejecuta)

| Item | Determinación |
|---|---|
| PORTABLE_SAFE_DELETE | **NO** — quedan 13 ítems MIGRATE y 7 ítems forenses sin archivar en el portable; su eliminación requiere autorización destructiva humana explícita. |
| MIGRATE_ITEMS_RECONCILED | 13 (todos PENDIENTE, preservados) |
| ARCHIVE_FORENSIC_ITEMS_RECONCILED | 12 (5 núcleo double-free archivados en C4; 7 preservados en portable) |
| DISCARD_ITEMS_RECONCILED | 19 (sin acción) |

— Fin de portable_exit_reconciliation.md (LOOP-0018T)