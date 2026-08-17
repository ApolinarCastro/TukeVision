# LOOP-0018Y rule diagnostics

The frozen 30-minute window produced 4,205 aggregate behavior-signal emissions and zero RiskEvents. The validation harness persisted full JSONL only when a RiskEvent existed, so it did not retain per-signal `rule_id` records. Rule-specific usefulness/noise counts cannot be reconstructed without inventing evidence.

| rule_id | trigger_count | review_count | useful | benign | ambiguous | insufficient evidence | classification |
|---|---:|---:|---:|---:|---:|---:|---|
| prolonged_dwell | NOT_MEASURED | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_DATA |
| repeated_activity | NOT_MEASURED | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_DATA |
| multi_camera_sequence | NOT_MEASURED | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_DATA |
| repeated_zone_activity | NOT_MEASURED | 0 | 0 | 0 | 0 | 0 | INSUFFICIENT_DATA |

No rule is classified KEEP, TUNE_CANDIDATE or DISABLE_CANDIDATE from this sample. Doing so would confuse aggregate trigger volume with reviewed utility. The next validation must materialize bounded signal-level review records before another long window.
