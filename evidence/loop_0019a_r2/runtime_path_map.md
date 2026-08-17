# LOOP-0019A-R2 — mapa del runtime real

## Precheck congelado

- HEAD: `b8ebcae309a2a080919889df87f2965c78f32ce5`
- Rama: `product/loop-0018r-temporal-tracking`
- Baseline: `423 tests`, `PASS`, `4 skipped` por backend real opcional.
- Entry point único del gate: `TukeVision.bat`.
- QW-04 y nuevas capacidades: congelados.

## Camino ejecutado

`TukeVision.bat`
→ `start_tukevision.ps1 -Mode Multicamera`
→ `.venv/Scripts/python.exe scripts/run_multicamera.py`
→ `MulticameraRuntime`
→ un único `SourceManager`
→ un único `OperationalPipeline`
→ `AdvanceChain.feed`
→ `ActivityLayer`
→ `SelectiveInferencePipeline` (`backend=yolo`)
→ `InferenceEvent`
→ `LocalTracker`
→ `TemporalActivity`
→ `Correlator`
→ `BehaviorEngine`
→ `PersistentEvidenceStore` (`data/runtime_evidence`)
→ callback `on_result`
→ `UiController.ingest_camera_snapshot`
→ `MultiCameraViewModel`
→ `TkApp`.

## Demostración de la divergencia

El resultado de `AdvanceChain.feed` contiene `observation`, `event`, `track`,
`temporal_activity`, `correlation`, `behavior` y `evidence`. El evento conserva
el conteo real en `event.metadata["detections"]`.

La adaptación R1 consulta erróneamente `event.detections`, campo que no existe,
por lo que siempre presenta `Det: 0`. Además, el modelo latest-wins reemplaza
Track/Temporal/Behavior/Evidence por valores vacíos en cada frame no seleccionado
o sin evento; la UI normalmente sólo alcanza a renderizar el frame vacío posterior.

`LAST_CONFIRMED_WORKING_STAGE = EVIDENCE_RETURNED`

`FIRST_BROKEN_STAGE = UI_MODEL_RECEIVED`

`ROOT_CAUSE = contrato de presentación mal adaptado + estado analítico efímero sobrescrito`

## Evidencia histórica concordante

`evidence/loop_0019a/real_run/stage_results.json` registra para la etapa de
cuatro cámaras 173 eventos, 22 tracks, 151 actualizaciones de track, 173
evaluaciones de comportamiento, 4 asociaciones y 2 trayectorias, con cero
errores de inferencia. Esto falsifica la hipótesis de un fallo general de YOLO,
tracking o BehaviorEngine.
