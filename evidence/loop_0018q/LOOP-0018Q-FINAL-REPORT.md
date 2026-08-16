# LOOP-0018Q — REPORTE FINAL: INFERENCE SELECTIVA + EVENT DETECTION MÍNIMA

## Veredicto

`SELECTIVE_INFERENCE_EVENT_PIPELINE_OPERATIONAL`

## Resumen

Tercera capacidad operacional del producto sobre el multicámara físico
certificado (LOOP-0018O) y la Observation Layer operativa (LOOP-0018P).
Se conectó la inferencia selectiva sobre `Observation+Policy` con el menor
cambio posible, reutilizando las piezas certificadas y sin nuevas dependencias.
La inferencia se ejecuta SOLO cuando la política lo autoriza (frame budgeting
real) y los resultados se convierten en eventos canónicos trazables con evidencia
por referencia.

Principio rector operativo:
`CAMERA/SOURCE -> OBSERVATION -> POLICY -> SELECTIVE INFERENCE -> EVENT -> EVIDENCE_REFERENCE`

## Qué se implementó (nuevo `src/inference/`)

1. `contract.py` — `InferenceDetection`, `InferenceResult` (inmutable, serializable,
   sin credenciales ni objetos OpenCV, metadata acotada <= 4096 B, UTC Z),
   `InferenceEngine` ABC + errores tipados.
2. `engines.py` — `DeterministicInferenceEngine` (sintético determinista, reloj
   inyectable) y `YoloInferenceEngine` (REUTILIZA PersonDetector del BASE por
   composición, carga perezosa, traducción de errores); `build_engine` config-driven.
3. `events.py` — `InferenceEvent` canónico trazable (event_id/camera_id/timestamp/
   event_type/confidence/producer/model/observation_ref/inference_ref/evidence_ref),
   `EventDetector` CONFIG-DRIVEN (threshold por tipo; regla específica gana),
   `BoundedEventQueue` con overflow explícito.
4. `selective.py` — `SelectiveInferencePipeline` compone ObservationPolicy
   REUTILIZADA + motor + detector + cola acotada; métricas por cámara/total;
   aislamiento del backend; close limpio; `build_pipeline` config-driven.
5. Tests: `test_inference_layer.py` (42 deterministas) +
   `test_inference_real_backend.py` (4 funcionales con YOLO real, separados).
6. `config/default.json`: bloque `inference` (+14 líneas, solo eso).

## Capacidad funcional demostrada

4 cámaras lógicas -> política QUALITY/BALANCED/ECONOMY decide el frame budgeting ->
inferencia selectiva (sintética determinista Y real YOLO) -> evento canónico
trazable con event_id/timestamp/inference_ref -> cola bounded por cámara ->
aislamiento de fallos -> shutdown limpio. Backend real verificado: 2 personas en
`data/temp/zidane.jpg`, evento PERSON_DETECTED generado.

## Reutilización (REUSE BEFORE NEW DEVELOPMENT)

- ObservationPolicy (LOOP-0018P): REUSE_AS_IS (importada, sin duplicar).
- PersonDetector (BASE): REUSE via composición en YOLO.
- E-05 (perfil+fallback) y E-02 (retención acotada): ya adaptados en LOOP-0018P,
  consumidos, no reescritos. E-04: NOT_APPLICABLE.
- `redact_rtsp_url` (BASE): REUSE_AS_IS en toda serialización.

Detalle: `evidence/loop_0018q/REUSE_MAP.md`.

## Resultados

- Tests focalizados deterministas: 42/42 OK.
- Prueba funcional backend real: 4/4 OK (3.6 s; yolo11n.pt + zidane.jpg).
- Regresión BASE: 326/326 OK (280 baseline + 46 nuevos; 0 regresiones).
- compileall: EXIT=0. Secret leak: 0.
- NEW_DEPENDENCIES=0. E-01 modificado: NO (`6a9ae7e…`). SourceManager
  reimplementado: NO (`29e0274…`). Observation Layer reescrita: NO.
- Git diff: limitado a alcance; config = solo bloque `inference`.

## Restricción de CPU respetada (G11)

YOLO11n ~54.5 ms/frame (LOOP-0018N). Default BALANCED ~2fps por cámara;
NO inferencia continua 15fps x 4. El pipeline consulta la política antes de
invocar el backend.

## Próximo PRODUCT ADVANCE (preparado, NO iniciado)

Correlación temporal / tracking / evidencia sobre eventos selectivos, reutilizando
E-02 trajectory (retención acotada) por cámara. Ver TES/BACKLOG (LOOP-0018R).

## Estado

- LOOP-0018Q CLOSED (a revisión humana). E-01 intacto; SourceManager y Observation
  Layer sin cambios.
- DEC-0035 aprobada (TES/04_Decisions).
- Evidencia completa en `evidence/loop_0018q/`.