# Radar Refresh — 2026-09-21 — MiniCPM-V 4.6

## Veredicto

`CLASSIFICATION = BENCHMARK | WATCH`

No se integra runtime ni se reemplaza OpenVINO/ByteTrack. MiniCPM-V 4.6 se registra como candidato VLM local y selectivo para P0-65 / investigación de evidencia cuando la búsqueda estructurada sea insuficiente.

## Validación de fuente

- `SOURCE_VERIFIED=YES` — upstream canónico `OpenBMB/MiniCPM-V`.
- `VERSION_OR_REF_VERIFIED=YES` — HEAD verificado `6ada8e8ef5e2979670fc94406f02b87c3c7e7ee0`, 2026-09-08; MiniCPM-V 4.6 es la versión VLM vigente documentada por upstream.
- `LICENSE_VERIFIED=YES` — Apache-2.0 en el ref verificado.
- `CAPABILITIES_EXTRACTED=YES` — 1.3B; comprensión imagen/video; >50% reducción declarada de FLOPs de encoding visual; compresión visual 4x/16x; variantes GGUF/BNB/AWQ/GPTQ; soporte llama.cpp/Ollama/vLLM/SGLang; despliegue edge móvil.
- `TUKEVISION_MAPPING=YES` — investigación local selectiva, Context Analyzer/evidence summaries y análisis de clips representativos; no inferencia VLM continua.
- `ADOPTION_BOUNDARY=YES` — LOCAL_FIRST; CCTV no sale del entorno autorizado; AI result = lead, no fact; sin biometría; DVR/NVR conserva grabación primaria; no sustituir detector/tracker sin evidencia.
- `REVISIT_CONDITION=YES` — activar benchmark cuando P0-65 requiera lenguaje natural/razonamiento visual que la búsqueda estructurada no resuelva, o cuando exista hardware objetivo con presupuesto medible.
- `EXPERIENCE_RECORD=EXP-MINICPM-V46-001`.

## Cambio material

La fuente era obligatoria en el radar operativo pero no estaba formalmente registrada en el índice canónico visible. Su perfil 1.3B, compresión visual y soporte local/edge la hacen materialmente distinta de tratar `Local VLM` como categoría genérica: permite un benchmark concreto bajo presupuesto restringido sin introducir cloud.

## Problema TukeVision afectado

P0-65 Semantic Investigation / análisis de evidencia: obtener descripción/razonamiento visual sobre frames o clips seleccionados manteniendo trazabilidad a evidencia fuente y costo acotado.

## Riesgos

- Benchmarks del upstream no equivalen a precisión CCTV ni a hardware TukeVision.
- VLM puede producir afirmaciones no soportadas; toda salida permanece `LEAD` hasta verificación contra evidencia.
- Video continuo elevaría CPU/RAM/latencia y contradice el patrón de atención selectiva.

## Benchmark mínimo

Mismo conjunto real y autorizado de evidencia representativa para MiniCPM-V 4.6 y el candidato VLM local vigente. Medir: exactitud útil para investigación, unsupported-claim rate, latencia p50/p95, RAM pico, CPU/GPU/NPU cuando aplique, tiempo a primer resultado y trazabilidad exacta `result -> evidence_id/frame_timestamp`. Requisito: `ORIGINAL_EVIDENCE_MUTATED=0` y cero media egress.

## Siguiente gate

`BENCHMARK_READY` sólo cuando exista necesidad P0-65 concreta + hardware objetivo. Promoción a `ADAPTAR/INTEGRAR` exige ventaja reproducible y preservación de Evidence First/local-first.