# Radar Refresh — 2026-09-25 — Jev / TypeSafe AI System One Models

## Materiality verdict

**MATERIAL_CHANGE = YES** — nueva categoría relevante para la futura capa de decisión de eventos. No modifica runtime, tests, dependencias, configuración ni Gate 0C.

## Classification

`WATCH / EXPERIMENTAL` — priority `MEDIUM-HIGH`.

## Why it matters

TukeVision ya separa hechos, inferencias y evidencia, y evoluciona hacia Observation → Track → Behavior/Correlation → Situation → Evidence/Investigation. Jev introduce una categoría distinta: modelos especializados en decisiones tipadas y probabilísticas que podrían actuar como router entre evidencia ya obtenida y el siguiente paso autorizado.

## Hypothesis

```text
RTSP / CCTV
→ Detection
→ Tracking
→ Event Candidates
→ Deterministic Correlation
→ Jev Event Decision Layer
→ Policy Engine
→ Investigation / Multimodal Model / Human Review
→ Evidence
```

Jev propone; Policy Engine valida; TukeVision ejecuta sólo acciones autorizadas; Evidence confirma/refuta.

## Verified upstream state

- TypeSafe launch: 2026-09-15.
- Jev = first public System One Model.
- API: `POST /v1/systemone`, model discovery via `GET /v1/models`.
- Python SDK public, latest release observed `v0.7.1` (2026-09-21).
- JS/TS SDK public, latest release observed `v0.6.0` (2026-09-15).
- Vercel AI Gateway and Cloudflare Workers AI integrations publicly available.
- Input is currently text/structured state; not a replacement for video/vision/audio models.
- TypeSafe speed/cost/calibration numbers are upstream claims until own benchmark.

## Future lab only

When authorized after sufficient product maturity: `/experiments/jev_event_lab/`, fully isolated from core.

Compare:
A deterministic rules; B Jev; C LLM; D multimodal; E hybrid.

Minimum metrics:
event classification accuracy; FP; FN; UNKNOWN accuracy; routing accuracy; multicamera routing accuracy; confidence calibration; latency p50/p95; cost/1,000 events; multimodal calls avoided; operator interventions; incorrect automatic escalations.

## Risks

Incorrect high-confidence decisions; calibration drift; temporal context loss; multicamera correlation error; FP/FN; vendor dependence; API/price changes; privacy; external latency; availability.

## Adoption gate

Do not promote until own data show measurable operational benefit, no increase in critical errors, reproducible/auditable decisions, evidence traceability, Policy Engine enforcement and advantage over simpler rules/models.

Promotion path only:

`WATCH → LAB → BENCHMARK → CANDIDATE → PRODUCTION`.
