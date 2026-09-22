# Radar Refresh — 2026-09-22

## Hallazgo material: OpenBMB/SimpleMemVLA

- `SOURCE_VERIFIED=YES`
- `VERSION_OR_REF_VERIFIED=YES` — `404215d752704fd8d8157fa6b7ccdfafdb2bd44e` (2026-09-15)
- `LICENSE_VERIFIED=YES` — MIT
- `CAPABILITIES_EXTRACTED=YES`
- `TUKEVISION_MAPPING=YES`
- `ADOPTION_BOUNDARY=YES`
- `REVISIT_CONDITION=YES`
- `EXPERIENCE_RECORD=EXP-SIMPLEMEMVLA-001`

### Fuente y cambio material

`OpenBMB/SimpleMemVLA` es un upstream oficial de OpenBMB para memoria de video nativa en modelos Vision-Language-Action. El ref verificado añade experiencia en robot físico y el proyecto documenta un patrón de memoria sin módulo dedicado: historial visual muestreado, timestamps preservados, selección de evidencia diferida a self-attention y prefill compartido para streaming. El README reporta, como resultado upstream y no como evidencia TukeVision, una reducción de latencia de decisión de 1.02 s a 0.68 s con salidas byte-identical mediante exact streaming inference.

### Problema TukeVision afectado

P0-65 / investigación histórica selectiva y P0-66 / atención contextual pueden requerir memoria temporal más rica sin indexar cada frame ni ejecutar un VLM continuamente. El patrón complementa `EXP-LOCAL-VLM-001`, `EXP-INTELLISEEK-001` y el trabajo de video-memory ya observado en Qwen-MM-Plugins.

### Clasificación

`BENCHMARK | ADAPTAR (PATTERN-ONLY)`

No se integra SimpleMemVLA ni su stack robótico. No reemplaza detector, tracker, Entity Truth, Evidence Store ni DVR/NVR. No autoriza VLM continuo.

### Adoption boundary

- `LOCAL_FIRST` obligatorio.
- DVR/NVR continúa como grabador primario.
- Sólo evidencia/ventanas autorizadas y locales entran al benchmark.
- `AI result = lead, no fact`.
- No biometría.
- No copiar componentes externos al core sin evaluación separada de necesidad, licencia y provenance.
- Los resultados de benchmarks robóticos del upstream no se extrapolan a CCTV.

### Benchmark mínimo

Comparar sobre un conjunto local de clips/evidencia ya autorizado:

1. baseline TukeVision de selección/indexado actual;
2. ventana temporal muestreada con timestamps preservados;
3. misma pregunta de investigación y mismo VLM local;
4. medir recall de evidencia temporal, afirmaciones no soportadas, latencia p50/p95, RAM, tokens/frames procesados y trazabilidad exacta a `evidence_id` + timestamp;
5. exigir que toda respuesta conserve provenance hacia evidencia fuente.

### Riesgo

El patrón proviene de VLA/robótica, no CCTV. Ventanas temporales extensas pueden aumentar RAM/contexto y favorecer inferencias semánticas no soportadas si se pierde el vínculo a evidencia. No adoptar cifras upstream como rendimiento TukeVision.

### Siguiente gate / condición de reevaluación

Ejecutar sólo cuando P0-65 necesite contexto temporal multi-evento que la búsqueda estructurada/representative snapshots no resuelva satisfactoriamente, o cuando el benchmark local VLM sea activado. Si no supera al baseline en recall/provenance con presupuesto edge aceptable, mantener `WATCH/RESERVE`.

## Cobertura del refresh

Se releyó la verdad canónica TES desde `feature/product-evolution-v1` antes de evaluar novedades. Las fuentes obligatorias y categorías activas se contrastaron con actividad pública reciente; no se encontró otro cambio que justificara modificar una decisión TES en esta ejecución. `DECISION_LOG.md` permanece sin cambios porque este hallazgo no altera una decisión arquitectónica vigente.
