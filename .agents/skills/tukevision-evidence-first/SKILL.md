---
name: tukevision-evidence-first
description: Apply TukeVision Evidence First rules to facts, media, provenance, investigations, integrity, audit trails, certification, and AI-derived claims. Use when handling evidence bundles, hashes, timestamps, provenance, semantic search results, ONVIF media signing, operator investigations, or PASS/certification claims.
---

# TukeVision Evidence First

## Epistemic contract

Always preserve:
- `FACT != INFERENCE`
- `INFERENCE != EVIDENCE`
- `AI RESULT = CANDIDATE_LEAD`
- `NO_EVIDENCE != NEGATIVE_EVIDENCE`
- `UNKNOWN` is valid.

## Evidence chain

Prefer:
`SOURCE -> OBSERVATION -> DETECTION/TRACK -> EVENT/SITUATION -> EVIDENCE BUNDLE -> INFERENCE -> OPERATOR/ACTION -> OUTCOME`.

A factual claim must point to the smallest available supporting evidence.

## Evidence bundle minimum

When relevant, require:
- source/camera ID;
- observed time and created time;
- pre/key/post frame or equivalent minimal media;
- ROI when useful;
- generation/runtime/model identity;
- confidence separated from provenance;
- hashes/integrity metadata;
- freshness/health;
- links to track/event/situation.

Do not duplicate full video when a minimal bundle is sufficient.

## Integrity and hostile input

Treat media and metadata as untrusted input.

For signed/tampered media validation:
- valid input verifies;
- tampered input fails closed;
- malformed/undefined tags fail safely;
- verifier process remains alive;
- emit deterministic failure/evidence state;
- `PROCESS_CRASH=0`.

Physical signing support remains unverified unless validated with actual capable hardware.

## Investigation controls

Semantic or AI search results are leads only. Require:
`purpose -> case -> permission -> scope -> query -> candidate leads -> source evidence -> human validation -> audit`.

Normal operation should favor privacy-preserving views; sensitive reveal requires authorization and audit.

## Certification rule

Synthetic fixtures can validate logic, not physical runtime truth.

A generated expected-value script cannot certify a physical camera, stream, device, UI state, or real-world event.
