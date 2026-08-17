# Materialization validation

QW00_DATASET_MATERIALIZED: NO — source contract records are absent.

- SOURCE_RECORDS_FOUND: 0 complete review records
- Persisted evidence index entries: 10 (all traceable)
- EVIDENCE_UNAVAILABLE_COUNT: 2 historical selections from E1
- BROKEN_EVIDENCE_REFS: 0 in persisted index
- EVIDENCE_HASH_MISMATCH: 0
- DUPLICATE_EVIDENCE: 0

No JSONL was fabricated and no existing evidence was overwritten. The review
launcher correctly returns `REVIEW_DATA_NOT_READY` when its canonical dataset
is absent.
