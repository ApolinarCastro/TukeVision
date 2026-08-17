# LOOP-0018W TDD evidence

Source: user-provided LOOP-0018W specification.

## Journeys

1. Configure explicit camera transitions and reject absent/disabled topology.
2. Correlate compatible local tracks using auditable time/topology components.
3. Build a three-plus-camera trajectory that reuses evidence references.
4. Preserve ambiguity instead of forcing an identity claim.
5. Keep candidates/trajectories bounded and resettable.

## RED/GREEN mapping

| Guarantee | Test target | RED | GREEN |
|---|---|---|---|
| Topology states/config validation | `TestTopologyContract` | `ModuleNotFoundError: src.correlation` | PASS |
| Temporal/topology/impossible filters | `TestCorrelationFiltering` | `ModuleNotFoundError: src.correlation` | PASS |
| 3/4-camera graph + evidence | `TestTrajectoryGraph` | `ModuleNotFoundError: src.correlation` | PASS |
| Ambiguity and bounded state | `TestBoundedState` | `ModuleNotFoundError: src.correlation` | PASS |

Intermediate TDD commits are intentionally omitted because the governing loop
requires a single commit only after all gates pass. Runtime RED/GREEN output is
preserved here instead.

RED command: `.venv\\Scripts\\python.exe -m unittest tests.test_cross_camera_correlation -v`.
Result: intended compile-time RED, 1 loader error because the new production
package was absent; no unrelated setup or dependency failure.

GREEN command: same target. Result: `Ran 15 tests ... OK`.

Review RED: bounded-linkage regression failed with missing
`association_count`, exposing that evicted linkage markers were not auditable.
After deterministic marker cleanup, the complete target is GREEN: 16/16 PASS.

Coverage: third-party `coverage` is absent and was not installed
(`NEW_DEPENDENCIES=0`). Python stdlib `trace --count --summary` executed the 16
test target and reported all four `src.correlation` modules at 100% of traced
executable lines. This is line tracing, not branch coverage; invalid config,
filters, ambiguity, TTL/count retention, serialization, reset and composition
are explicitly exercised by named tests.
