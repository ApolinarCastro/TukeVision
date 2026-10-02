# Radar Refresh — 2026-10-02 — NVIDIA Body Pose / Eye Contact / Relighting / VSR

## Materiality

**MATERIAL_CHANGE=YES**

The NVIDIA 3D Body Pose NIM is materially relevant to the planned behavior/normality/loss-prevention layer because it consumes tracked person boxes and returns structured articulated-body pose tied to the existing tracking ID.

VSR, Relighting and Eye Contact are transformative video technologies. They are materially relevant mainly because they require an explicit evidence boundary: derived pixels must never silently become canonical CCTV evidence.

## Decisions

- 3D Body Pose → ACTIVE_EVALUATION / HIGH
- VSR → BENCHMARK / DERIVED_VIEW_ONLY
- Relighting → REJECT_CORE / RESERVE_DERIVED_VIEW
- Eye Contact → REJECT_CORE / RESERVE_REFERENCE

## Current blocker

Gate 0C physical verification remains the first execution checkpoint. No product implementation is authorized by this refresh.

## Future benchmark

Body Pose:
1. existing detector+tracker only;
2. lightweight 2D-pose alternative;
3. NVIDIA 3D Body Pose;
4. compare action/gesture signal quality, FP/FN, UNKNOWN, latency, GPU memory, throughput vs body count and operator usefulness.

Derived video:
1. original source always retained;
2. derived enhancement labeled;
3. measure whether human review improves;
4. reject any path that obscures provenance or adds unsupported detail.
