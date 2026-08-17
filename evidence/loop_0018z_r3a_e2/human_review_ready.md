# Human review readiness

`review_behavior_signals.bat` is BASE/.venv based, resumable, idempotent, and
preserves existing matrix decisions. It cannot present a real signal until a
canonical `signal_review_records.jsonl` exists. Current status:

`QW00_DATASET_DISCOVERED=NO`
`REVIEW_DATA_NOT_READY=YES`
`HUMAN_REVIEW_READY=NO`

No human classification was invented.
