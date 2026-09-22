# SOURCE — OpenBMB/SimpleMemVLA

- `SOURCE_ID=OPENBMB-SIMPLEMEMVLA`
- `SOURCE_TYPE=OFFICIAL_GITHUB_RESEARCH_UPSTREAM`
- `CANONICAL_UPSTREAM=https://github.com/OpenBMB/SimpleMemVLA`
- `FORGE=GITHUB`
- `LAST_VERIFIED_REF=404215d752704fd8d8157fa6b7ccdfafdb2bd44e`
- `LAST_VERIFIED_AT=2026-09-22`
- `LICENSE=MIT`
- `TES_DECISION=BENCHMARK | ADAPTAR (PATTERN-ONLY)`
- `DIRECT_PRODUCT_INTEGRATION=NO`
- `EXPERIENCE_RECORD=EXP-SIMPLEMEMVLA-001`

## Capability extracted

Native timestamped video history as model context; decision-time evidence selection through the model's native attention; shared-prefix prefill / exact streaming inference; no dedicated retrieval/compression/recurrent memory module required by the proposed pattern.

## TukeVision mapping

P0-65 Semantic Investigation; P0-66 selective attention/context; local VLM investigation over bounded evidence windows. Candidate pattern for retaining temporal context while preserving explicit timestamps and provenance.

## Adoption boundary

Pattern-only research. TukeVision remains local-first, Evidence First and provider-neutral. DVR/NVR remains primary recorder. No continuous VLM, no biometric inference, no customer CCTV to external services, and AI output remains a lead requiring evidence/human validation.

## Revisit condition

Activate a benchmark only when structured search/representative snapshots cannot answer a real temporal investigation need or when the local-VLM benchmark gate is explicitly opened.

## Minimum benchmark

Same local evidence set and same VLM: compare current selector/index baseline against timestamped sampled-history context. Measure evidence recall, unsupported claims, p50/p95 latency, RAM/context cost, and exact provenance back to `evidence_id` and timestamps.

## Risk

Research is designed for VLA/robotics. Upstream robot success rates and latency claims are not CCTV evidence and must not be extrapolated to TukeVision.
