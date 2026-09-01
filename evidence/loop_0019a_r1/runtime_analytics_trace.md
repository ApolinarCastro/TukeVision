# LOOP-0019A-R1 — runtime analytics trace

## Cadena ejecutada

`TukeVision.bat` → `start_tukevision.ps1 -Mode Multicamera` → `scripts/run_multicamera.py` → `SourceManager` → `OperationalPipeline` → `AdvanceChain.feed()`.

`AdvanceChain.feed()` devuelve `observation`, `event`, `track`, `temporal_activity`, `correlation`, `behavior` y `evidence`.

## Evidencia real disponible

El artefacto `evidence/loop_0019a/real_run/stage_results.json` registra la etapa de cuatro cámaras con:

- 4 cámaras registradas.
- 1.442 frames considerados; 320 procesados; 173 eventos de inferencia; 0 errores de inferencia.
- 22 tracks iniciados, 151 actualizaciones y 18 finalizados.
- 4 asociaciones, 38 candidatos y 2 trayectorias.
- 173 evaluaciones de comportamiento (64 retenidas por límite); 0 risk events en esa ventana.

Esto demuestra que la analítica no se pierde en `AdvanceChain`; existe en el resultado de cada frame y en los agregados de ejecución.

## Punto exacto de pérdida

En `scripts/run_multicamera.py`, `on_result(camera_id, snapshot, result)` llama a `UiController.ingest_camera_snapshot()` con un `SimpleNamespace` que contiene únicamente `frame_index`, `frame`, `source_state` y `fps`. El parámetro `result` se descarta.

`UiController.ingest_camera_snapshot()` sólo actualiza `MultiCameraViewModel`; `TkApp._render_video()` consume ese modelo para imagen y estado. Por ello detecciones, Track ID, permanencia, zona, BehaviorSignal, riesgo y evidencia no llegan a ningún widget multicámara. En paralelo, `poll_state()` devuelve `source_path_display="MULTICAMERA"` mientras el estado legacy inicia con `source_kind="FILE"`, explicando la contradicción observada por el operador.

Clasificación R1: `EXISTS_NOT_CONNECTED` entre contrato de runtime y presentación; además `CONNECTED_NOT_RENDERED` para la información analítica. No se requiere nueva capacidad técnica.
