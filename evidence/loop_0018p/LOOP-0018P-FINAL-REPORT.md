# LOOP-0018P — REPORTE FINAL: ACTIVITY / OBSERVATION LAYER MÍNIMA

## Verdicto

`OBSERVATION_LAYER_MINIMUM_OPERATIONAL`

## Resumen

Primera capacidad operacional de observación del producto sobre el multicámara
físico certificado (LOOP-0018O). Se implementó, con reutilización y el menor
cambio posible, una Activity/Observation Layer mínima, desacoplada de la
captura, config-driven, determinista, auditable y sin nuevas dependencias.

Principio rector operativo: `CAPTURE -> OBSERVATION -> POLICY` (mínima).
INFERENCE/EVENT/EVIDENCE quedan preparados por contrato (`producer` callable,
`evidence_ref`) sin adelantar su implementación.

## Qué se implementó (todo en `src/observations/activity.py`)

1. `ActivityObservation` — observación canónica inmutable por cámara:
   identidad lógica, timestamp UTC (Z), categoría, estado, payload acotado
   (JSON <= 4096 B), confianza opcional, origen y evidence_ref opcional.
   Serializable, sin credenciales ni objetos OpenCV.
2. `BoundedObservationQueue` — cola FIFO acotada por cámara con política de
   overflow explícita (drop_oldest/drop_newest).
3. `ObservationPolicy` — CONFIG-DRIVEN con QUALITY/BALANCED/ECONOMY;
   default seguro BALANCED (no inferencia continua 15fps x 4); fail-safe.
4. `ActivityLayer` — registro de fuentes lógicas, ingestión determinista,
   sampling por política, encolado acotado, consulta/consumo, aislamiento de
   productores defectuosos y shutdown limpio. Composición con SourceManager.

## Capacidad funcional demostrada (tests sintéticos deterministas)

4 fuentes lógicas registradas -> generación independiente de observaciones ->
identificación inequívoca de cámara -> timestamps UTC válidos -> cola acotada
-> consulta/consumo -> aislamiento entre cámaras -> aplicación verificable de
QUALITY/BALANCED/ECONOMY -> shutdown limpio.

## Reutilización (REUSE BEFORE NEW DEVELOPMENT)

- E-05 quality_engine: REUSE_WITH_ADAPTATION (perfil + fallback seguro).
- E-02 trajectory: solo concepto de retención acotada (NOT_APPLICABLE cuerpo).
- E-04 UI: NOT_APPLICABLE (sin GUI en este loop).
- SourceManager (BASE): composición (ALREADY_EXISTS_IN_BASE).
- `redact_rtsp_url` (BASE): REUSE_AS_IS.
- `config/default.json` (BASE): extendido con bloque `observation`.

Detalle: `evidence/loop_0018p/E02_E04_E05_APPLICABILITY.md` y
`SOURCE_TO_TARGET_MAP.md`.

## Resultados

- Tests focalizados: 39/39 OK (deterministas).
- Regresión BASE: 280/280 OK (241 baseline + 39 nuevos), 3 ejecuciones.
- compileall: EXIT=0. Secret leak: 0.
- NEW_DEPENDENCIES=0. E-01 modificado: NO. SourceManager reimplementado: NO.
- Git diff: 8 archivos, +1412 (solo alcance LOOP-0018P).

## Restricción de CPU respetada

YOLO11n ~54.5 ms/frame (LOOP-0018N). La política por defecto (BALANCED) limita
el análisis a ~2fps por cámara; no se ejecuta YOLO en esta capa. El productor
por defecto es determinista y sin inferencia; la detección selectiva se
conecta en el siguiente PRODUCT ADVANCE mediante el contrato `producer`.

## Próximo PRODUCT ADVANCE (preparado, NO iniciado)

Conectar INFERENCE selectiva / event detection sobre Observation+Policy,
reutilizando extensiones existentes (E-02 trajectory / E-05) antes de
desarrollar nuevas. Ver TES/BACKLOG.