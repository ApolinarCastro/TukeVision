# Radar Refresh — 2026-09-21 — Qwen Live Harness

## Resultado material

Nueva fuente relevante descubierta y verificada: `QwenLM/Qwen-Live-Harness` v1.0.0, publicada 2026-09-21.

## Validación de fuente

- `SOURCE_ID=QWEN-LIVE-HARNESS`
- `SOURCE_VERIFIED=YES` — upstream canónico `QwenLM/Qwen-Live-Harness`.
- `VERSION_OR_REF_VERIFIED=YES` — release declarada v1.0.0 (2026-09-21); upstream activo.
- `LICENSE_VERIFIED=YES` — Apache-2.0.
- `CAPABILITIES_EXTRACTED=YES` — audio/video realtime, camera/screen context, proactive visual/audio conditions, on-demand snapshots, live feed 1 FPS/720p, monitor 1 FPS/two-second chunks, task delegation, long-term memory.
- `TUKEVISION_MAPPING=YES` — referencia para P0-66 atención/proactive monitoring y P0-65 investigación selectiva; separación capture/presentation/coordinator; advertencia explícita de que sampling/inference puede fallar y no sirve como alarma safety-critical.
- `ADOPTION_BOUNDARY=YES` — NO integrar el producto ni enviar CCTV de cliente al Qwen Omni Realtime API/DashScope. Electron sigue fuera del perfil actual. Sólo estudiar patrones de orquestación y UX que puedan reimplementarse local-first.
- `REVISIT_CONDITION=YES` — reevaluar si aparece backend VLM/Omni totalmente local compatible, o si TukeVision necesita un benchmark reproducible de proactive monitoring local.
- `EXPERIENCE_RECORD=EXP-QWEN-LIVE-001`.

## Clasificación

`WATCH | ADAPTAR (PATTERN-ONLY) | REJECT_CURRENT_CLOUD_PATH`

No cambia una decisión arquitectónica existente: refuerza límites ya vigentes (`LOCAL_FIRST`, no cloud CCTV, AI result = lead, no fact, Electron rechazado para el perfil actual). Por ello `TES/DECISION_LOG.md` no se modifica.

## Cambio material

El upstream introduce una implementación pública y recién liberada de interacción multimodal realtime con cámara/pantalla, condiciones proactivas y memoria. Es material como referencia de diseño para atención selectiva, pero su camino de inferencia exige conexión a Alibaba Cloud Model Studio DashScope/Qwen Omni Realtime API. Ese requisito es incompatible con la política permanente de TukeVision para CCTV de cliente.

## Problema TukeVision afectado

- P0-66: reducción de carga/atención del operador y proactive monitoring.
- P0-65: investigación visual selectiva bajo demanda.
- Separación captura/presentación/coordinación y trazabilidad de monitores.

## Riesgo

- Exfiltración de frames/audio si se adoptara el backend cloud.
- Dependencia de servicio/región/API externa.
- Resultados no deterministas y retraso por sampling/inference; el propio upstream advierte que no es sistema de alarma safety-critical.
- Electron y requisitos de escritorio no encajan con el perfil liviano actual.

## Benchmark mínimo

No ejecutar con CCTV de cliente. Si se reevalúa el patrón, usar dataset sintético/local autorizado y comparar un monitor local equivalente:

1. condición visual conocida → detección/lead;
2. `TIME_TO_OPERATOR_ATTENTION`;
3. `FALSE_ESCALATION_RATE`;
4. `MISSED_RELEVANT_EVENTS`;
5. latencia, CPU/RAM;
6. trazabilidad exacta a frame/timestamp/evidence_id;
7. `MEDIA_EGRESS=0` obligatorio para cualquier candidato TukeVision.

## Siguiente gate

`WATCH` hasta que exista backend local compatible o una brecha P0-66 medida que justifique benchmark. No crear módulo, dependencia ni integración ahora.
