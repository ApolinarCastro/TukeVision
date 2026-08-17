# LOOP-0018Y real-world behavior validation report

## Outcome

Authorized real CCTV validation completed under frozen config SHA256 `6A5742B8ED43FD77A8955507734073D9EA1D629CBE5665C409792FDE8CEC06A8`. Stages A/B/C and the 1,800-second main window completed with all requested cameras healthy, zero stalls, zero inference/temporal/harness errors and no configuration changes.

The product generated substantial features/signals but zero RiskEvents. Absence of a RiskEvent is not proof of correct or incorrect real-world semantics. With nothing to review, usefulness/benign/ambiguity rates are N/A. Result: `VALIDATION_ACTIVITY_INSUFFICIENT` at the RiskEvent/human-review level.

## Main window

| Measure | Result |
|---|---:|
| Duration | 1,800 s |
| Cameras | 4 |
| Frames received | 64,461 |
| Frames selected by ActivityLayer | 6,759 |
| Selective inferences | 10,847 |
| Inference selection rate | 16.8279% of received frames |
| Events | 4,909 |
| Unique tracks / temporal activities | 408 / 408 |
| Unique trajectories observed by harness | 54 |
| Behavior features / signals | 14,898 / 4,205 |
| RiskEvents | 0 |
| Evidence artifacts written (before bounded eviction) | 6,759 |
| Retained authorized-camera evidence | 128 |
| Retained evidence without linked event | 87 |
| Broken refs / hash mismatch / duplicate hashes | 0 / 0 / 0 |

The inference policy is an independent selection gate from ActivityLayer; therefore inference count is not expected to equal observation count.

## Resources

- 358 interval samples.
- Process CPU average/peak: 683.706% / 751.3% in psutil multicore notation, equivalent to approximately 31.08% / 34.15% of 22 logical processors.
- RAM first sample/average/peak: 637.012 / 565.533 / 643.660 MiB.
- Threads: 190–194.
- Inference latency average: 61.549 ms across the four-camera main window.
- Queue-depth aggregate remained bounded at 32 in interval samples.
- Resource headroom: `MODERATE` (process-only measurement; no unsupported system-wide claim).

## Isolation and governance

All four camera health records remained independent and healthy with zero stalls. Tracks and evidence use canonical camera IDs. No natural camera failure/reconnect occurred, so reconnect and failure isolation are `NOT_EXERCISED`, not PASS. No accusatory runtime output was captured. Risk remains a review hypothesis and correlation remains temporal/topological, not identity.

## Review limitation and next decision

`behavior_events.jsonl` is empty because the validation harness wrote full records only for RiskEvents and none occurred. Aggregate BehaviorSignals existed, but per-signal rule/evidence records are unavailable for human review. This is recorded as GAP-001 rather than repaired or hidden.

Next Product Advance: `EXTENDED_REAL_WORLD_VALIDATION`, preceded by a bounded signal-level review export so the next authorized window can evaluate existing signals without changing rules/models. No external technology is justified.
