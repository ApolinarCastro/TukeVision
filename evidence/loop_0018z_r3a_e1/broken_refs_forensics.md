# Broken-reference forensics

The prior validator reported exactly two broken refs, but it terminated before
persisting the selected review records. `evidence_index.json` contains the
persisted subset (10 refs across 4 review IDs); all 10 frame paths exist and
all 10 `metadata.json` files exist. Their recorded SHA-256 values verify.

The two failing refs therefore have no surviving `review_id`, `signal_id`, or
evidence path in the preserved artifacts. They cannot be named or reconstructed
without inventing data. They are classified as `NON_RECOVERABLE_EVICTED_ARTIFACT`
with `EVIDENCE_UNAVAILABLE`, not silently treated as valid.
