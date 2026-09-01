# RUN-462B04 — PHYSICAL_EVIDENCE_PRE_CHECKPOINT

**Registro:** 2026-08-28 ~14:45 (GMT-4) · **Por:** AUTOCLAW (cierre controlado de Fase 2, MACRO-TUKEVISION-V3)

## Estado de registro

`RUN-462B04 = PHYSICAL_EVIDENCE_PRE_CHECKPOINT`

Evidencia física de estabilidad previa al checkpoint de certificación. NO se reinterpreta como run reproducible sobre versión limpia; la versión ejecutada fue `06d0e6a-dirty` (worktree sin commit).

## Identidad

- run_id: RUN-462B04 · pid: 2248 (proceso finalizado al momento del registro)
- started_at: 2026-08-28T10:55:45 · duración observada: ~76 min (4.565 s, 4.089 muestras @1s)
- version: 06d0e6a-dirty · cámaras: 15 (cam_01..cam_15)
- base commit: 06d0e6a449a8af6eb9ce8610409632a1f9897a3b (branch product/loop-0018r-temporal-tracking)

## Hashes SHA-256 (verificados al registro)

| Archivo | SHA-256 | Tamaño |
|---|---|---|
| identity.json | `6ED7E88233C4574B64683FB90053BAD8DFC6C47EA6329DB00A628EE22F401898` | 385 B |
| live_status.json | `C89224D3F040F31F27D247A0237B381FC73FB023461ED2789A2FBC728FC26ECF` | 13.117 B |
| runtime_trace.json | `07C20156631E4FEDDBDD9FE67CC4C0F345D7E80BDD622536E236C96101F395D6` | 5.443 B |
| resource_telemetry.json | `81349CC878AD63ECF6B2260B564C81B227C622B79BE11E04AE3881B02D0A8261` | 2.952.924 B |

## Clips (histórico)

- En el inventario de las 12:54 existían ~250 pares CLP-*.json + CLP-*.mp4.
- Al registrar este manifiesto (14:45): 0 clips presentes — rotados por la retención acotada del runtime. Los hashes de clips NO pudieron tomarse post-hoc (observación registrada).

## Resultado físico (resumen)

- CPU proceso: avg 817% / max 886% de ~2.200% (22 hilos) ≈ 37-40%
- RSS: 287 → máx 627 → 440 MB (acotado, sin fuga monótona)
- Liveness a 76 min: 15/15 ONLINE, capture OPEN, reconnect_count=0, stale=false, frame_age <1 s
- Cadena cognitiva por cámara: FRAME_RECEIVED ~10.100-10.600 · UI_RENDERED 3.300-4.700 · EVIDENCE_RETURNED ~1.200-1.400 · DETECTIONS/TRACKS/TEMPORAL/BEHAVIOR >0

## Autorización

Búsqueda dirigida (Journal, Dashboard, Backlog): sin constancia de autorización formal para esta corrida. Hallazgo registrado: la corrida fue física y real, pero su gate no puede certificarse sin registro. El RUN de certificación formal se ejecutará desde el checkpoint limpio.
