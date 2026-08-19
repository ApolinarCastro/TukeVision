# LOOP-0021 system health TDD evidence

Date: 2026-08-19
Baseline: `61d7ab38516d9da656a53c71d919f9857eda50d4`

## RED

Command:

```text
python -m unittest -v tests.test_system_health
```

Observed result before implementation: import failure for the absent
`src.observability.system_health` module. The reproducer was committed as
`9a9084a` before product code was added.

## GREEN

- LOOP-0021 focused tests: 14/14 PASS.
- Related focused regression: 98/98 PASS.
- Full regression: 495/495 PASS, with 4 optional skips.
- Compileall: PASS.
- Secret scan: 21/21 PASS.
- New regressions: 0.
- Product-code commit: `89fd34c`.

The focused suite covers CPU, RAM and disk presentation; unavailable-metric
fallback; bounded 3-second sampling; per-camera real source health; degraded,
offline and unknown states; STOP clearing historical OPEN state; no frame or
connection consumption; runtime exposure; and preservation of the certified
exact-frame/stop helpers.

## Coverage

`coverage.py` is not installed and no dependency was added. Python's standard
library `trace` runner was used instead against the 14 focused tests.

```text
src.observability.system_health: 182 executed / 210 executable lines = 86.7%
```

This exceeds the adopted 80% TDD threshold. Physical operator verification is
separate from these technical tests and remains pending.
