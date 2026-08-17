# Human-review resume

The review launcher is present and resumable, but the validator exited before
writing `signal_review_records.jsonl`; therefore `REVIEW_DATA_NOT_READY` is the
correct current state. No human classifications are invented. Once a valid QW-00
JSONL dataset exists, `review_behavior_signals.bat` can resume/preserve the
operator matrix.
