# LOOP-0019A-R2 Addendum V1 — precheck

## Estado congelado

- HEAD de entrada: `450fad511669948a6669633d6b71263cbf08fc53`
- Rama: `product/loop-0018r-temporal-tracking`
- Verificación humana: G1 PASS; G2–G9 PARTIAL/FAIL; G10 listo para verificar.
- QW-04 y capacidades nuevas: congelados.
- Cambios ajenos/preexistentes del worktree se preservan.

## Causa visual demostrable antes de editar

1. `YoloInferenceEngine` produce coordenadas reales por detección.
2. `EventDetector` reduce el resultado a conteo y no propaga coordenadas.
3. `AdvanceChain` llama `LocalTracker.ingest(event)` sin el `bbox` ya soportado
   por el tracker; por ello `LocalTrack.last_bbox` queda vacío en el runtime real.
4. La UI sólo dibuja texto fuera del video; no existe overlay de detección/track.
5. El launcher usa main stream (`subtype=0`) sólo en canal 7 y substream
   (`subtype=1`) en los otros tres, explicando la calidad inconsistente.

Clasificación: capacidades existentes pero conexiones de representación
incompletas. La reparación autorizada es propagar metadata bounded, conectar el
argumento `bbox` ya existente y renderizarla sin alterar YOLO, tracking,
thresholds, reglas conductuales o evidencia.

## Journey y aceptación

Como operador, quiero ver sobre cada panel las cajas YOLO reales y el Track ID
real asociado, junto con el frame analítico y resolución de origen, para poder
verificar qué detecta y sigue TukeVision sin inferirlo desde contadores laterales.

- Coordenadas vienen exclusivamente del resultado YOLO.
- El evento conserva como máximo 16 cajas; el conteo total permanece exacto.
- El tracker recibe la caja canónica ya soportada.
- La UI nunca inventa cajas, IDs, BehaviorSignal, riesgo ni evidencia.
- Los cuatro canales solicitan el mismo stream principal para calidad coherente.
