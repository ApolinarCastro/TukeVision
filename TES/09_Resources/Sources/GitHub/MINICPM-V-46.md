# SOURCE — OpenBMB/MiniCPM-V 4.6

`SOURCE_ID=MINICPM-V46`

- `CANONICAL_UPSTREAM=https://github.com/OpenBMB/MiniCPM-V`
- `LAST_VERIFIED_REF=6ada8e8ef5e2979670fc94406f02b87c3c7e7ee0`
- `LAST_VERIFIED_AT=2026-09-21`
- `REF_DATE=2026-09-08`
- `LICENSE=Apache-2.0`
- `SOURCE_VERIFIED=YES`
- `VERSION_OR_REF_VERIFIED=YES`
- `LICENSE_VERIFIED=YES`
- `CAPABILITIES_EXTRACTED=YES`
- `TUKEVISION_MAPPING=YES`
- `ADOPTION_BOUNDARY=YES`
- `REVISIT_CONDITION=YES`
- `EXPERIENCE_RECORD=EXP-MINICPM-V46-001`
- `TES_CLASSIFICATION=BENCHMARK | WATCH`

## Capacidad relevante

MiniCPM-V 4.6 es un VLM edge de 1.3B orientado a imagen/video. Upstream declara reducción >50% del cómputo de encoding visual mediante LLaVA-UHD v4, compresión visual configurable 4x/16x, variantes cuantizadas y soporte de inferencia local mediante llama.cpp, Ollama, vLLM y SGLang.

## Mapeo TukeVision

Candidato concreto para P0-65 Semantic Investigation y análisis selectivo de evidencia cuando consultas estructuradas no basten. No usar como analítica continua ni como sustituto automático del detector/tracker.

## Frontera de adopción

LOCAL_FIRST; cero CCTV de cliente a servicios externos; Evidence First; resultado VLM = lead, no fact; sin biometría; DVR/NVR sigue siendo grabador primario; provenance desde cada salida hasta `evidence_id` y timestamp.

## Riesgo

Los resultados publicados por upstream no prueban precisión CCTV ni rendimiento sobre el hardware objetivo de TukeVision. Riesgo adicional de hallucination/unsupported claims y consumo si se usa sobre video continuo.

## Benchmark mínimo

Frames/clips representativos y autorizados; comparar calidad útil, unsupported-claim rate, latencia p50/p95, RAM pico y carga de cómputo, manteniendo `ORIGINAL_EVIDENCE_MUTATED=0`, `MEDIA_EGRESS=0` y trazabilidad completa.

## Revisit condition

Reevaluar cuando P0-65 tenga una brecha demostrada que búsqueda estructurada no resuelva o cuando exista hardware objetivo para benchmark reproducible.