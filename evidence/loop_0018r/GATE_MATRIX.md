# LOOP-0018R — Gate matrix

Fecha: 2026-08-16
Branch: `product/loop-0018r-temporal-tracking`
Checkpoint base: `5d0d1162f2320c9e53da46e2f10244d64698024d`

| Gate | Descripción | Resultado |
|---|---|---|
| G1 | BASE_PRE = `5d0d116` (sin divergencia) | PASS |
| G2 | E-01 intacto (`6a9ae7e…`) | PASS |
| G3 | SourceManager no reimplementado (`29e0274…`) | PASS |
| G4 | Observation Layer no reimplementada (`114b6a…` = HEAD 5d0d116) | PASS |
| G5 | Selective Inference/Event pipeline no reimplementado (hashes LOOP-0018Q) | PASS |
| G6 | E-02 evaluado bajo REUSE BEFORE NEW DEVELOPMENT | PASS (ver REUSE_MAP_E02.md) |
| G7 | Contrato LocalTrack operativo | PASS |
| G8 | Ciclo STARTED/ACTIVE/ENDED | PASS |
| G9 | Asociación temporal determinista | PASS |
| G10 | Asociación espacial mínima (IoU) | PASS |
| G11 | Dos objetos simultáneos separados | PASS |
| G12 | Timeout cierra track | PASS |
| G13 | Evento posterior al timeout crea nuevo track | PASS |
| G14 | TemporalActivity operativa | PASS |
| G15 | Duración/event_count correctos | PASS |
| G16 | Cuatro cámaras lógicas aisladas | PASS |
| G17 | No correlación cross-camera de identidad | PASS (NO) |
| G18 | Operational evidence acotada (first/latest/best) | PASS |
| G19 | Evidence references no inventadas | PASS |
| G20 | Retention bounded (event refs) | PASS |
| G21 | Active tracks bounded | PASS |
| G22 | Completed history bounded | PASS |
| G23 | Error isolation | PASS |
| G24 | Métricas operativas | PASS |
| G25 | Config config-driven | PASS |
| G26 | Continuous 15fps x 4 default = NO | PASS (BALANCED) |
| G27 | New dependencies = 0 | PASS |
| G28 | OpenCV/FFmpeg/Torch/Ultralytics no modificados | PASS |
| G29 | Secrets = 0 | PASS |
| G30 | Tests focalizados deterministas | PASS (33/33) |
| G31 | Full regression >= 326 + nuevos | PASS (359/359) |
| G32 | New regressions = 0 | PASS |
| G33 | compileall | PASS |
| G34 | Evidencia histórica intacta | PASS |
| G35 | TES consistente | PASS |
| G36 | Git diff limitado al alcance | PASS |
| G37 | Commit local únicamente (tras G1-G36) | PREVISTO |
| G38 | merge = NO | NO |
| G39 | push = NO | NO |

## Hashes finales (pre-commit)

| Archivo | git-hash |
|---|---|
| `src/temporal/__init__.py` | (registrado al commit) |
| `src/temporal/contract.py` | (registrado al commit) |
| `src/temporal/tracker.py` | (registrado al commit) |
| `tests/test_temporal_tracking.py` | (registrado al commit) |
| `config/default.json` | (registrado al commit) |