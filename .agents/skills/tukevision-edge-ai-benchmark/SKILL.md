---
name: tukevision-edge-ai-benchmark
description: Evaluate TukeVision detectors, trackers, VLMs, embeddings, inference runtimes, cascades, accelerators, and hardware portability with finite evidence-based benchmarks. Use before adopting/replacing OpenVINO, ByteTrack, a VLM, ONNX/runtime layer, Edge Impulse pattern, GPU/NPU backend, or perception architecture.
---

# TukeVision Edge AI Benchmark

## Principle

Do not adopt models or runtimes by novelty, leaderboard rank, or vendor claims. Compare against the current TukeVision baseline on the same workload and hardware.

## Preserve current baseline

Unless a measured gap exists:
- OpenVINO remains the primary edge inference baseline;
- ByteTrack/current tracker remains in place;
- detector/tracker/VLM layers are not replaced;
- no continuous VLM over all cameras;
- no cloud dependency for customer CCTV.

## Benchmark contract

Define:
- problem/gap;
- current baseline;
- candidate;
- exact dataset/video;
- exact hardware;
- fixed configuration;
- PASS/FAIL thresholds;
- rollback.

Measure at minimum when relevant:
- CPU/RAM/VRAM;
- FPS/throughput/goodput;
- p50/p95 latency;
- dropped/stale frames;
- recovery time;
- detection precision/recall or task-specific accuracy;
- ID switches/track recovery;
- VLM/semantic quality;
- cost per event/1k decisions;
- storage/network impact.

Tie technical metrics to operator/business outcomes when possible.

## Selective intelligence

Prefer:
`cheap continuous detector -> tracker -> temporal/situation gate -> evidence selector -> expensive model only when justified`.

For VLM:
- event-triggered first;
- minimal representative evidence;
- benchmark small vs large model cascade when needed;
- `UNKNOWN` and abstention are allowed.

## Model/runtime selection

Consider build-vs-buy, on-device deployment, licenses, hardware support, maintainability, and observability.

Public benchmarks are discovery evidence, not adoption evidence.

## Acceptance

Promote only when the candidate:
- solves a demonstrated gap;
- exceeds baseline on declared metrics;
- does not violate privacy/governance;
- stays within resource budget;
- preserves rollback and traceability.
