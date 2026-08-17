# LOOP-0018Y validation protocol

## Frozen-window rule

The fingerprinted baseline configuration is immutable for Stage A (one camera), Stage B (two cameras), Stage C (four cameras), and the main window. Findings are recorded before any correction. No threshold, rule, model, topology, frame budget or dependency change is permitted during validation.

## Authorized-source gate

Only currently authorized real CCTV/video may be used. Credentials enter through the existing interactive `getpass`/memory path and must never be persisted or printed. Evidence uses canonical camera IDs and `[DVR_HOST]`, never a credential-bearing URL. Historical access is not proof of current authorization.

## Stages

1. Stage A: one camera; validate structural chain and resource baseline.
2. Stage B: two cameras; validate independent state and incremental load.
3. Stage C: four cameras; validate camera isolation, correlation metadata and aggregate resources.
4. Main window: target 30 minutes (prefer 60 only if operational conditions allow). Insufficient natural activity is a valid outcome.

No failure or suspicious behavior is induced. A natural failure that does not occur is `NOT_EXERCISED`, not PASS.

## Collection

Interval telemetry goes to `runtime_metrics.csv`; behavior outputs go to `behavior_events.jsonl`. PersistentEvidence remains bounded. Reviewed RiskEvents must trace from risk → signals → features → trajectory/track → event/inference → evidence reference → file → SHA256.

The human-review vocabulary is limited to `USEFUL_SIGNAL`, `BENIGN_ACTIVITY`, `INSUFFICIENT_EVIDENCE`, `AMBIGUOUS`, `SYSTEM_ERROR`, and `NOT_REVIEWED`. Utility rates are reported only from reviewed samples; no accuracy/precision/recall claims are made without explicit ground truth.

## Sampling and decision

Review all events when few exist; otherwise use a deterministic representative sample ordered by risk ID and stratified by rule/camera where possible. Diagnose rule contribution and missing information only after the main window closes. Match P0/P1 empirical gaps to the existing TES radar without installing or integrating technology. Select exactly one next Product Advance from the loop decision table.
