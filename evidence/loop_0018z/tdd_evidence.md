# LOOP-0018Z TDD evidence

## RED

Command: `python -m unittest tests.test_signal_review_export`

Observed failure before product implementation:

`ModuleNotFoundError: No module named 'src.review'`

Result: 0 tests executed, 1 expected import error.

## GREEN

After adding only the signal-review contract/exporter:

`Ran 7 tests in 0.022s — OK`

After adding explicit evidence-preservation and secret-redaction coverage:

The focused pre-validation suite ran 140 tests successfully. The complete suite
ran 411 tests successfully with 4 optional skips and no failures.

No behavior thresholds were changed. `BehaviorEngine` was not modified.
