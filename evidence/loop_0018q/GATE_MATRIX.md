# LOOP-0018Q — Gate matrix

Fecha: 2026-08-16
Branch: `product/loop-0018q-selective-inference-events`
Checkpoint base: `c7432313536d931bea703692714a09138654b3e7`

| Gate | Descripción | Resultado |
|---|---|---|
| G1 | Identidad de BASE verificada (checkpoint `c743231…`) | PASS |
| G2 | Reuso obligatorio de piezas certificadas (ObservationPolicy, PersonDetector, redact) | PASS |
| G3 | Clasificación E-02..E-05 (mapa de reuso) | PASS (100% clasificado) |
| G4 | REUSE BEFORE NEW DEVELOPMENT en la capa | PASS (ver REUSE_MAP.md) |
| G5 | Schema `InferenceResult`/`InferenceDetection` inmutable y serializable | PASS |
| G6 | Identidad por >= 4 cámaras lógicas | PASS |
| G7 | Timestamps UTC Z y serialización JSON | PASS |
| G8 | Thresholds config-driven (nunca hardcode en lógica) | PASS |
| G9 | `InferenceResult -> Event` con event_id, timestamp, inference_ref | PASS |
| G10 | `evidence_ref` opcional propagado al evento | PASS |
| G11 | NO inferencia continua 15fps x 4 por defecto (BALANCED ~2fps) | PASS |
| G12 | Aislamiento de fallos del backend por cámara | PASS |
| G13 | Cola de eventos bounded por cámara (overflow explícito) | PASS |
| G14 | NEW_DEPENDENCIES = 0 | PASS |
| G15 | Tests focalizados deterministas: 42/42 | PASS |
| G16 | Prueba funcional acotada con backend real (4/4, separada) | PASS |
| G17 | Config inválida -> fail-safe o error explícito (nunca silencio) | PASS |
| G18 | Secret leak = 0 | PASS |
| G19 | Determinismo: mismas entradas -> mismas salidas | PASS |
| G20 | Git diff limitado a alcance LOOP-0018Q | PASS |
| G21 | Obsidian/TES actualizado (PROJECT_STATUS, DEVELOPMENT_LOG, BACKLOG, DEC) | PASS |
| G22 | Regresión completa >= 280 + nuevos, 0 regresiones: 326/326 | PASS |
| G23 | compileall EXIT=0 | PASS |
| G24 | E-01 NO modificado (git-hash `6a9ae7e…`); SourceManager NO reimplementado (`29e0274…`); Observation Layer NO reescrita | PASS |
| G25 | Evidencia guardada en `evidence/loop_0018q/` | PASS |
| G26 | Hashes finales registrados (inmutabilidad del commit) | PASS (pre-commit) |
| G27 | Commit local únicamente (NO merge, NO push) | PREVISTO |

## Hashes finales (G26 pre-commit)

| Archivo | git-hash |
|---|---|
| `src/inference/__init__.py` | `193ee3cc6bdfcfcde27e39bc6bc958b2aaad12eb` |
| `src/inference/contract.py` | `3fa0d4ef62beeca6d9b3f8dfa941576e213b6e7b` |
| `src/inference/engines.py` | `5457a777c035965ed016a9aca919154a7ecf41d5` |
| `src/inference/events.py` | `8a2594d2838a647cf5d8dec7f8e40614f364a4dc` |
| `src/inference/selective.py` | `855f20bd421289b442d66941365d7dec5ba09241` |
| `tests/test_inference_layer.py` | `65f8d879600aeca61e392318a5b66ace4cdde027` |
| `tests/test_inference_real_backend.py` | `e8df793e662d4914c8f9416ce3bb615b117786c3` |
| `config/default.json` | `7dde0c226cdc2ed91e35713875f14aa8cf092f9d` |