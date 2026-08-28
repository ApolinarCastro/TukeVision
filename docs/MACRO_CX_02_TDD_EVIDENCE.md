# MACRO-CX-02 — TDD and certification evidence

Date: 2026-08-19  
Candidate HEAD: `06d0e6a449a8af6eb9ce8610409632a1f9897a3b`  
Scope: repairable certification defects only; no CCTV, PTZ, merge, push, or
candidate commit.

## Journeys protected

1. A source snapshot is read once, processed once, and the same snapshot is
   delivered to QW-04/downstream consumers.
2. Deployment topology creates the canonical per-store edge runtime instead of
   reporting a boolean-only start.
3. A new evidence namespace reports disk health before its leaf directory
   exists.
4. Learning and runtime-wiring tests leave no dataset or policy state in the
   repository.

## RED → GREEN record

### Exact-frame snapshot contract (CX02-DEF-013)

- RED: `RacingSnapshotManager` exposed a frame between the first and second
  snapshot reads; the callback received `None` while processing used the new
  frame.
- GREEN: `OperationalPipeline.process_available()` accepts the already-read
  snapshot and `run()` uses that same object for processing and callback.
- Regression assertion: snapshot object identity and frame index equal the
  operational result.

### Real edge topology composition (CX02-DEF-003)

- RED: an edge service without a runtime silently toggled state, and topology
  rejected a runtime provider.
- GREEN: missing runtime fails closed; the provider is injected and start/stop
  delegate to it.
- Integration assertion: a real `StoreEdgeRuntime` created through
  `EdgeRuntimeManager.prepare_store` processes frames through the topology and
  stops cleanly.

### Health and test-state regressions

- Clean-start disk metric is asserted against a missing evidence leaf.
- Learning/runtime-wiring use `TemporaryDirectory`; post-suite persistent test
  state is zero.
- ResourceWarning gate: `34/34 PASS`.

## Verification

- Focused macro: `186/186 PASS`.
- Full regression: `599 total`, `595 executed PASS`, `4 optional skips`,
  `0 failures`.
- Compileall: PASS.
- Secret scan: PASS (`21/21` contract tests; zero attributed production hits).
- Diff check: PASS.
- Focused line coverage using Python standard-library `trace --missing`:
  `operational_pipeline=98%`, `deployment.topology=89%`,
  `edge_runtime=81%`, `system_health=85%`.

## Commit policy

No commit was created. The repository contains preserved, mixed changes from
prior loops plus OpenCode/Codex work. A checkpoint would require a separate
attribution and selective-staging gate; this macro does not authorize silently
discarding or absorbing unrelated work.
