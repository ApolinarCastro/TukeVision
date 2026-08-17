# Dataset source map

Candidate source: `evidence/loop_0018z/evidence_index.json`.

It contains 10 verified evidence entries grouped under four `review_id`
values. It does **not** contain the corresponding `signal_id`, timestamp,
track, rule/type, rule score, source refs, or serialized `BehaviorSignal` /
`SignalReviewRecord` objects. `stage_results.json` contains aggregate counters,
not individual signal records.

Therefore no complete QW-00 dataset can be materialized from the preserved
artifacts without inventing contract fields or falsely assigning evidence to a
signal. The correct state is `REVIEW_DATA_NOT_READY`.
