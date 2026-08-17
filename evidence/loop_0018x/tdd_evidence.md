# LOOP-0018X TDD evidence

Source: user-provided LOOP-0018X specification. The single-final-commit constraint superseded the skill's intermediate-commit preference; RED/GREEN proof is preserved here.

## Journeys

- An operator receives facts, non-accusatory signals and an explainable review candidate from existing operational contracts.
- An auditor can trace every signal to a configured rule, feature, time window and available evidence reference.
- An administrator can tune or disable rules and retention without code changes.
- Ambiguous or incomplete inputs remain explicit and cannot silently become a risk event.

## RED → GREEN

| Stage | Command | Result |
|---|---|---|
| RED | `python -m unittest tests.test_behavior_pipeline` | Expected import failure: `No module named 'src.behavior'` |
| GREEN focused | same target plus advance-chain/correlation targets | 40 tests passed |
| GREEN full | `python -m unittest discover -s tests` | 402 passed, 4 optional skips |
| Coverage | `python -m trace --count --summary --module unittest tests.test_behavior_pipeline` | behavior engine executable lines reported 100% |

## Guarantees

| Guarantee | Test type | Result |
|---|---|---|
| Serializable feature/signal/risk contracts use non-accusatory output | unit | PASS |
| Dwell, repetition, zone metadata and four-camera trajectory facts are deterministic | unit | PASS |
| Config thresholds, suppression, ambiguity and missing evidence are fail-safe | unit | PASS |
| Risk requires multiple signals and carries rule/evidence explanation | unit | PASS |
| Retention and track isolation are bounded | unit | PASS |
| AdvanceChain remains operational with behavior wiring | integration/regression | PASS |

Known gap: real-world accuracy, zone calibration and action/pose models require a separately approved validation loop. Four existing optional tests remain skipped for unavailable optional conditions; no new skip was added.
