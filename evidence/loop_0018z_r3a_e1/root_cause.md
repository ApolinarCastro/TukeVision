# Root cause

`EXPORTER_REFERENCES_NON_RETAINED_EVIDENCE` / `RETENTION_EVICTED_BEFORE_REVIEW_EXPORT`
is the demonstrated class: the validator selected records after a long MAIN
window while PersistentEvidence retention remained bounded. The exporter did
not persist its selected records before traceability verification, so two refs
were reported broken and the dataset itself was not written.

No evidence supports changing retention to unlimited storage. No product-core
code was changed in E1; the honest repair is explicit unavailable-evidence
classification and preserving the valid indexed artifacts.
