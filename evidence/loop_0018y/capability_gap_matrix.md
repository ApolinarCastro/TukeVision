# LOOP-0018Y capability gap matrix

| GAP_ID | GAP_TYPE | OBSERVED_COUNT | AFFECTED_EVENTS | EVIDENCE | CURRENT_CAPABILITY | MISSING_INFORMATION | POTENTIAL_EXTENSION_POINT | IMPACT | PRIORITY | RECOMMENDATION |
|---|---|---:|---|---|---|---|---|---|---|---|
| GAP-001 | DATA_GAP | 4,205 signals | all signal emissions | stage results + runtime metrics; empty `behavior_events.jsonl` | aggregate signal counters | per-signal rule, feature and evidence record for review | validation/review export after `BehaviorResult` | human utility cannot be measured | P1 | bounded signal-level review capture; no model change |
| GAP-002 | RULE_GAP | 0 RiskEvents from 4,205 signals | 4,909 event evaluations | main chain summary | deterministic single-rule signals | whether current rule combinations are intentionally conservative or operationally too weak | risk aggregation diagnostics | no review-event sample | P1 | extended real-world validation with signal capture; tune only in a later correction loop if review supports it |
| GAP-003 | EVIDENCE_GAP | 87 of 128 retained artifacts without linked event | retained evidence audit | PersistentEvidence records | selected-frame evidence is retained and hashed | whether non-event selected evidence adds review value | evidence sampling/review policy | storage/review noise | P2 | measure before changing retention |
| GAP-004 | DATA_GAP | 0 reviewed RiskEvents | zero RiskEvents | human-review matrix | approved non-accusatory review vocabulary | human assessment of usefulness/benign/ambiguity | review workflow | product utility remains unproven | P1 | classify `VALIDATION_ACTIVITY_INSUFFICIENT` at RiskEvent level |

No pose/action, object-interaction, tracking-backend or external-model gap was demonstrated by reviewed evidence in this window.
