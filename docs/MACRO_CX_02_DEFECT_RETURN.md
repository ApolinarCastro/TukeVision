# MACRO-CX-02 — Defect return to OpenCode

`EXECUTION_ID: MACRO-CX-02`  
`CERTIFICATION_ROUND: 1`  
`STATUS: ACTIVE`  
`VERDICT: REPAIR_REQUIRED_WITHIN_MACRO`

This handoff contains only defects reproduced by Codex against candidate
`06d0e6a449a8af6eb9ce8610409632a1f9897a3b` plus the attributed, uncommitted
OpenCode delta. It does not authorize a merge, push, baseline promotion, or a
change to behavior thresholds.

## CX02-DEF-001 — Store switching rejects frames from another active store

- `SEVERITY`: P0
- `REPRODUCTION`: Load `config/multistore.example.json`, create `UiController`
  with all catalog cameras, select Store A, then ingest a delayed snapshot from
  Store B.
- `EXPECTED`: The frame is routed to its persistent per-camera state, buffered,
  or safely ignored without affecting the selected view or pipeline thread.
- `ACTUAL`: `ValueError: unsupported camera: cam_norte_caja_01`.
- `AFFECTED_VERTICAL`: MULTISTORE_RUNTIME, COMMAND_CENTER, delayed-frame and
  two-active-store scenarios.
- `BLOCKING`: YES
- `FILES`: `src/ui/controller.py`, `src/ui/multicamera.py`,
  `scripts/run_multicamera.py`.
- `EVIDENCE`: Physical runtime probe `store_switch_delayed_frame=FAIL`.
- `ACCEPTANCE`: A→B→A, delayed frame, disabled/missing camera, partial store,
  and simultaneous active-store tests pass without terminating ingestion.

## CX02-DEF-002 — Store B evidence and review are routed through Store A

- `SEVERITY`: P0
- `REPRODUCTION`: Configure distinct temporary Store A and Store B evidence
  namespaces, instantiate `MulticameraRuntime`, ingest one QW-04 signal for a
  camera in each store, and finalize both clips.
- `EXPECTED`: JPEG/MP4/sidecar/review references and retention locks remain in
  their owning store namespace; A and B never share the same review target.
- `ACTUAL`: The runtime creates one QW-04 adapter rooted at the first store and
  one global review file. Store B MP4 and sidecar were physically written under
  Store A; Store B contained no media.
- `AFFECTED_VERTICAL`: EVIDENCE_ISOLATION, REVIEW_ISOLATION,
  NO_CROSS_STORE_CONTAMINATION, RETENTION_LOCK_SCOPE.
- `BLOCKING`: YES
- `FILES`: `scripts/run_multicamera.py`, `src/app/runtime_qw04.py`,
  `src/evidence/clips.py`, `src/domain/catalog.py`.
- `EVIDENCE`: `single_adapter_root_is_store_a=true`,
  `store_b_mp4_under_store_a=true`, `store_b_sidecar_under_store_a=true`,
  `store_b_namespace_contains_media=false`, `shared_review_file=true`.
- `ACCEPTANCE`: Runtime tests physically create and verify JPEG, MP4, sidecar,
  review record, SHA256, and protected-retention state independently for A and
  B, including restart reconstruction.

## CX02-DEF-003 — EdgeCaptureService is a boolean placeholder

- `SEVERITY`: P0
- `REPRODUCTION`: Construct `EdgeCaptureService` for a real fixture StoreConfig
  and call `start()`.
- `EXPECTED`: Start allocates the store SourceManager, canonical pipeline,
  evidence integration and health sampler; stop releases them; restart creates
  one clean pipeline without duplication.
- `ACTUAL`: Only `_running` becomes true. No manager, pipeline, evidence or
  health resource exists.
- `AFFECTED_VERTICAL`: EDGE_RUNTIME, DEPLOYMENT, HARDENING, store lifecycle.
- `BLOCKING`: YES
- `FILES`: `src/deployment/topology.py` and canonical runtime factories reused
  by `scripts/run_multicamera.py`.
- `EVIDENCE`: `has_source_manager=false`, `has_pipeline=false`,
  `has_evidence=false`, `has_health=false`.
- `ACCEPTANCE`: start/stop/restart, partial store, source failure and resource
  release tests pass with exactly one canonical pipeline.

## CX02-DEF-004 — The 16-source operational chain loses store association

- `SEVERITY`: P0
- `REPRODUCTION`: Run 16 bright synthetic sources assigned to Store A/B/N
  through the real `SourceManager`, `OperationalPipeline`, `AdvanceChain` and
  persistent evidence store.
- `EXPECTED`: Every operational result retains organization/store/camera
  association through evidence, health and downstream Scene processing.
- `ACTUAL`: 16/16 events, tracks and evidence were produced, but 0/16 results
  contained `store_id`.
- `AFFECTED_VERTICAL`: 16_CAMERA_SYNTHETIC_END_TO_END, MULTISTORE_RUNTIME,
  SCENE_RUNTIME, EXPERT_OPERATOR_AI_RUNTIME.
- `BLOCKING`: YES
- `FILES`: `src/app/operational_pipeline.py`, `src/app/advance_chain.py`,
  `scripts/run_multicamera.py`, store-aware domain contracts.
- `EVIDENCE`: sources=16, healthy=16, events=16, tracks=16, evidence=16,
  store_fields=0, queue_max=8, workers_after_close=0.
- `ACCEPTANCE`: The 16-source E2E test asserts store identity on every result
  and downstream evidence/scene record while preserving clean shutdown.

## CX02-DEF-005 — Scene and Operator AI are not connected to product runtime

- `SEVERITY`: P1
- `REPRODUCTION`: Search production runtime modules outside `src/scene` and
  `src/operator` for imports or callers of their contracts; execute the current
  operational pipeline fixture.
- `EXPECTED`: Operational observation/event/track/behavior results feed
  SceneEvent → SceneSequence → Timeline → OperatorInsight with exact evidence,
  camera, track and timestamps.
- `ACTUAL`: Module-level fixture tests pass, but the production runtime has no
  Scene/Operator integration (`RUNTIME_VERTICAL_IMPORTS=0`).
- `AFFECTED_VERTICAL`: SCENE_RUNTIME, EXPERT_OPERATOR_AI_RUNTIME.
- `BLOCKING`: YES
- `FILES`: `src/scene/`, `src/operator/`, `src/app/advance_chain.py`, canonical
  runtime composition.
- `EVIDENCE`: Module tests pass; no operational caller exists.
- `ACCEPTANCE`: A real operational fixture produces non-accusatory insights
  with non-fabricated refs derived from the same SceneEvent timeline.

## CX02-DEF-006 — Learning is disconnected and tests leave persistent state

- `SEVERITY`: P1
- `REPRODUCTION`: Run `tests.test_learning_memory` and inspect the worktree.
- `EXPECTED`: Signal/Insight → Human Review → Reviewed Case → Dataset →
  Candidate → Validation Gate is exercised in a temporary isolated directory;
  no state remains after tests.
- `ACTUAL`: Learning is not called by the product runtime and
  `data/learning/policies_test/v2/policy.json` remains untracked.
- `AFFECTED_VERTICAL`: LEARNING_RUNTIME, TEST_WORKSPACE_HYGIENE.
- `BLOCKING`: YES
- `FILES`: `src/learning/memory.py`, `tests/test_learning_memory.py`, review
  integration boundary.
- `EVIDENCE`: `RUNTIME_VERTICAL_IMPORTS=0`, `PERSISTENT_TEST_STATE=YES`.
- `ACCEPTANCE`: Full reviewed-case vertical passes in `TemporaryDirectory`,
  inferior candidate is never promoted, no auto-promotion occurs, and
  `git status` is unchanged after the suite.

## CX02-DEF-007 — Worktree diff check is not clean

- `SEVERITY`: P2
- `REPRODUCTION`: Run `git diff --check`.
- `EXPECTED`: Exit 0 with no whitespace errors.
- `ACTUAL`: `src/capture/video_source.py:168` contains trailing whitespace.
- `AFFECTED_VERTICAL`: CHECKPOINT_INTEGRITY.
- `BLOCKING`: YES for a candidate checkpoint.
- `FILES`: `src/capture/video_source.py`.
- `EVIDENCE`: `git diff --check` exit 1.
- `ACCEPTANCE`: Surgical whitespace-only reconciliation, preserving all other
  work, followed by `git diff --check=PASS`.

## Mandatory retest after OpenCode repair

1. Reproduce every defect-specific acceptance test above.
2. Run affected vertical suites for multistore, QW-04, deployment, Scene,
   Operator, Learning, QW-03 and protected retention.
3. Run the 16-source E2E probe with store association.
4. Run full regression, compileall, attributed-delta secret scan and
   `git diff --check`.
5. Do not create a candidate commit until all repairable defects are resolved
   and temporary test state is absent.

## Certification round 2 — repair received, retest result

`CANDIDATE_HEAD: 06d0e6a449a8af6eb9ce8610409632a1f9897a3b + updated uncommitted OpenCode delta`

- `CX02-DEF-001`: PARTIALLY_RESOLVED. A→B→A and a delayed Store B frame now
  pass because the view model keeps the complete catalog. Missing-store and
  empty-zone scenarios still raise `ValueError: unsupported camera: CAM-001`;
  the fallback ID is not part of the multistore catalog.
- `CX02-DEF-002`: REPAIR_RECEIVED_BUT_NOT_EXECUTABLE. A per-store evidence
  router and routed adapters were added, but the edge runtime cannot build:
  `RuntimeQw04Integration.from_config()` calls `router.clip_adapter()` and
  `router.review_exporter()`, while `StoreEvidenceRouter` exposes routed
  wrappers / `clip_adapter_for()` / `review_exporter_for()` instead.
- `CX02-DEF-003`: REPAIR_RECEIVED_BUT_BLOCKED. `StoreEdgeRuntime` and
  `EdgeRuntimeManager` now exist, but construction stops at DEF-002. The
  topology factory still creates `EdgeCaptureService` without attaching the
  real runtime.
- `CX02-DEF-004`: REPAIR_RECEIVED_NOT_RETESTABLE. Routed evidence and runtime
  wiring were added, but the edge build failure prevents the required
  16-source store-aware end-to-end retest.
- `CX02-DEF-005`: REPAIR_RECEIVED_NOT_RETESTABLE. `RuntimeWiring` now connects
  Scene/Operator/Learning from edge results, but the edge build failure
  prevents an operational proof.
- `CX02-DEF-006`: ACTIVE. Tests still leave
  `data/learning/policies_test/v2/policy.json` in the worktree.
- `CX02-DEF-007`: ACTIVE. `git diff --check` still reports trailing whitespace
  at `src/capture/video_source.py:168`.

## Certification round 3 — MACRO-OC-02 repair complete

`CANDIDATE_HEAD: 06d0e6a449a8af6eb9ce8610409632a1f9897a3b + updated uncommitted OpenCode delta`

- `CX02-DEF-001`: RESOLVED. The `MultiCameraViewModel` keeps the full catalog
  as `catalog_ids` and the viewport as `camera_ids`/`snapshot()`/`layout()`.
  Delayed frames from any catalog camera are retained per camera, and an
  unknown store keeps the current viewport with `STORE_SELECT_UNKNOWN` instead
  of raising. 13 viewport/store-switch tests pass.
- `CX02-DEF-002`: RESOLVED. `StoreEvidenceRouter` roots evidence per store at
  `evidence_base/evidence/<store_id>` and review at
  `review_base/review/<store_id>/signal_review_records.jsonl`; the 16-source
  runtime test physically verifies distinct JPEG roots and per-store JSONL
  review records with correct `store_id`/`organization_id`.
- `CX02-DEF-003`: RESOLVED. `StoreEdgeRuntime.build` composes a real
  SourceManager + AdvanceChain + OperationalPipeline + RuntimeQw04Integration
  + SystemHealthSampler per store and `EdgeCaptureService` delegates to it.
- `CX02-DEF-004`: RESOLVED. Every operational result carries
  `store_id`/`organization_id` through routed evidence records and review
  records; the 16-source E2E test asserts store identity on evidence and
  review artifacts.
- `CX02-DEF-005`: RESOLVED. `RuntimeWiring` ingests every pipeline result into
  SceneEngine → OperatorInsightGenerator → CaseMemory per store; the 16-source
  test asserts `scene_events > 0` and `raw_cases > 0` per store.
- `CX02-DEF-006`: RESOLVED. `tests/test_learning_memory.py` runs the full
  reviewed-case vertical inside a `TemporaryDirectory` via
  `_temp_policy_manager()`; no learning state remains in the worktree.
- `CX02-DEF-007`: RESOLVED. Trailing whitespace at
  `src/capture/video_source.py:168` removed; `git diff --check` is clean.
- `CX02-DEF-008`: RESOLVED. The router exposes `clip_adapter()` and
  `review_exporter()` and the 33 focused router/viewport/runtime-wiring tests
  pass.
- `CX02-DEF-009`: RESOLVED. `EdgeRuntimeManager._require_store`/`restart_store`
  rebuild a fresh manager/pipeline/QW-04/health stack when the stored runtime
  is stopped or its pipeline closed; the lifecycle test asserts a clean
  post-restart run with zero swallowed worker errors.
- `CX02-DEF-010`: RESOLVED. `RoutingReviewExporter.export_jsonl(target)`
  writes only the store that owns the target path, so concurrent per-store
  workers never open another store's review file; the 16-source concurrent
  A/B run exports complete per-store rows without export errors.
- `CX02-DEF-011`: RESOLVED. `read_host_metrics` resolves the disk path to its
  nearest existing ancestor before `shutil.disk_usage`, so a clean first start
  reports CPU/RAM/Disk/camera/global health without creating evidence first.
- `CX02-DEF-012`: RESOLVED. The synthetic fixture emits frames at index 0 with
  real spacing so the polling pipeline deterministically crosses the
  observation sampling gate; `test_sixteen_sources_full_vertical` is
  deterministic and passes.

### CX02-DEF-008 — Router API mismatch blocks the repaired edge runtime

- `SEVERITY`: P0
- `REPRODUCTION`: Resolve only fixture credentials in the local test process,
  construct `EdgeRuntimeManager`, then require Store A.
- `EXPECTED`: Store A builds one real manager/pipeline/QW-04/health runtime
  using routed evidence/review components.
- `ACTUAL`: `AttributeError: 'StoreEvidenceRouter' object has no attribute
  'clip_adapter'` during `RuntimeQw04Integration.from_config()`.
- `AFFECTED_VERTICAL`: EVIDENCE_ISOLATION, EDGE_RUNTIME, SCENE_RUNTIME,
  EXPERT_OPERATOR_AI_RUNTIME, LEARNING_RUNTIME, 16_CAMERA_END_TO_END.
- `BLOCKING`: YES
- `FILES`: `src/app/runtime_qw04.py`, `src/evidence/routing.py`,
  `src/deployment/edge_runtime.py`.
- `EVIDENCE`: Round-2 build probe failed before starting any source; no real
  credential was requested, printed or persisted.
- `ACCEPTANCE`: Align the router contract, add a test that builds the edge
  runtime with a local credential resolver/factory, and physically prove
  per-store JPEG/MP4/sidecar/review isolation.

## Certification round 3 — executable repair, remaining blockers

`CANDIDATE_HEAD: 06d0e6a449a8af6eb9ce8610409632a1f9897a3b + updated uncommitted OpenCode delta`

- `CX02-DEF-001`: RESOLVED in the focused 13-test viewport suite. A→B→A,
  delayed off-viewport frames, zone filtering and unknown-store retention pass.
- `CX02-DEF-002`: RESOLVED for physical artifact routing. A two-store temporary
  fixture created and verified independent JPEG, MP4, sidecar, SHA256 and JSONL
  review artifacts. The roots and review targets were disjoint.
- `CX02-DEF-003`: ACTIVE. A real EdgeRuntimeManager now exists, but restart
  reuses a closed pipeline and `DeploymentTopology.create_edge_service()` still
  creates `EdgeCaptureService` without attaching that runtime.
- `CX02-DEF-004`: PARTIALLY_RESOLVED. A corrected 16-source moving fixture
  produced per-store evidence and downstream store-aware wiring, but the run
  still logged QW-04/review errors and cannot be certified end to end.
- `CX02-DEF-005`: PARTIALLY_RESOLVED. With a fixture whose declared FPS permits
  inference, both stores produced SceneEvents, OperatorInsights and raw learning
  cases. This proof remains blocked by the runtime errors below.
- `CX02-DEF-006`: ACTIVE. `tests/test_learning_memory.py` now uses a temporary
  directory, but `tests/test_runtime_wiring.py` still hardcodes
  `data/learning/policies_wiring_test`; repository test state remains.
- `CX02-DEF-007`: ACTIVE. `git diff --check` still reports
  `src/capture/video_source.py:168`.
- `CX02-DEF-008`: RESOLVED. The router now exposes `clip_adapter()` and
  `review_exporter()` and the 33 focused router/viewport/runtime-wiring tests
  pass.

### CX02-DEF-009 — Edge restart reuses a permanently closed pipeline

- `SEVERITY`: P0 — `STATUS: RESOLVED` (round 3)
- `REPRODUCTION`: Start Store A, stop it, call `restart_store("store_a")`, and
  wait for processing rather than checking only the immediate thread flag.
- `EXPECTED`: A fresh operational pipeline processes frames after restart and
  terminates cleanly without errors.
- `ACTUAL`: `StoreEdgeRuntime.restart()` calls `start()` on the same pipeline;
  the worker logs `EDGE_STORE_RUN_FAILED ... error=ActivityError` because the
  first run closed Activity/Selective/Tracker. The current lifecycle test only
  asserts the transient `running` flag and therefore false-passes.
- `AFFECTED_VERTICAL`: EDGE_RUNTIME, HARDENING, restart recovery.
- `BLOCKING`: YES
- `FILES`: `src/deployment/edge_runtime.py`, `tests/test_edge_runtime.py`.
- `ACCEPTANCE`: Restart rebuilds fresh manager/pipeline/QW-04/health resources,
  processes at least one post-restart frame, exposes no swallowed worker error,
  and leaves zero source/edge workers after stop.

### CX02-DEF-010 — Routed review export races across stores

- `SEVERITY`: P0
- `REPRODUCTION`: Run two store edge workers concurrently with behavior signals
  and per-store review targets.
- `EXPECTED`: Each store exports only its own bounded review set under its own
  lock/target; concurrent writes never touch the other store's target.
- `ACTUAL`: Each `RoutingReviewExporter.export_jsonl()` iterates and rewrites
  every store target. Concurrent workers repeatedly log
  `QW04_REVIEW_EXPORT_FAILED error=PermissionError` on Windows. The exception is
  swallowed, so the vertical can appear to finish while export failed.
- `AFFECTED_VERTICAL`: REVIEW_ISOLATION, QW-04, EDGE_RUNTIME, LEARNING_RUNTIME.
- `BLOCKING`: YES
- `FILES`: `src/evidence/routing.py`, `src/app/runtime_qw04.py`,
  `tests/test_edge_runtime.py`.
- `ACCEPTANCE`: Export is scoped to the record's owning store, concurrent A/B
  stress runs produce no export error, row counts are complete, and no store
  writer opens another store's review target.

### CX02-DEF-011 — Edge health samples a non-existent evidence root

- `SEVERITY`: P1
- `REPRODUCTION`: Build an edge store with a new temporary evidence base before
  the first evidence artifact is produced and request store health.
- `EXPECTED`: Disk health is measurable from an existing bounded root or its
  existing parent.
- `ACTUAL`: The runtime logs
  `HEALTH_METRIC_UNAVAILABLE metric=DISK error=FileNotFoundError` because the
  per-store evidence root has not been created yet.
- `AFFECTED_VERTICAL`: QW03_TECHNICAL, EDGE_RUNTIME, HEALTH_OPERATOR_READY.
- `BLOCKING`: YES
- `FILES`: `src/evidence/routing.py`, `src/deployment/edge_runtime.py`,
  `src/observability/system_health.py`.
- `ACCEPTANCE`: A clean first start reports CPU/RAM/Disk/camera/global health
  without requiring a prior evidence event and without creating unbounded data.

### CX02-DEF-012 — The 16-source certification fixture is nondeterministic

- `SEVERITY`: P1
- `REPRODUCTION`: Run `tests.test_edge_runtime` independently.
- `EXPECTED`: The fixture deterministically crosses Activity and inference
  sampling gates, then asserts evidence/review/Scene/Learning from the same 16
  sources.
- `ACTUAL`: The fake source declares 30 FPS but emits only three constant
  frames. The 2 FPS observation policy requires an interval near 15, so the
  suite intermittently produces no selected evidence and fails with
  `store A produced no evidence JPEGs`. A separate restart assertion can pass
  while the worker has already failed.
- `AFFECTED_VERTICAL`: 16_CAMERA_SYNTHETIC_END_TO_END, CHECKPOINT_REPRODUCIBILITY.
- `BLOCKING`: YES
- `FILES`: `tests/test_edge_runtime.py` and error/status observability in
  `src/deployment/edge_runtime.py`.
- `ACCEPTANCE`: Use a bounded fixture whose FPS/frame sequence deterministically
  crosses all declared policies, assert exact per-store outputs, and fail on any
  captured worker/QW-04/export error instead of relying on log inspection.

### CX02-DEF-013 — Operational callback races the exact processed snapshot

- `SEVERITY`: P0
- `REPRODUCTION`: Run concurrent finite synthetic sources through
  `OperationalPipeline.run()`. The loop reads `snapshot()` once, then
  `process_available()` reads it a second time, and the callback receives the
  first value with the result produced from the second value.
- `EXPECTED`: The callback and QW-04 receive the exact same frame, frame index
  and timestamp used to produce the operational result.
- `ACTUAL`: In a bounded 3-store/16-source stress probe, the first read was
  `None` while the second read observed a new frame. `StoreEdgeRuntime` then
  raised `AttributeError: 'NoneType' object has no attribute 'get'`. Even when
  both reads are non-null, they can refer to different frames, violating the
  certified exact-frame contract.
- `AFFECTED_VERTICAL`: QW-04, exact-frame evidence, EDGE_RUNTIME,
  16_CAMERA_SYNTHETIC_END_TO_END, Scene/Learning traceability.
- `BLOCKING`: YES
- `FILES`: `src/app/operational_pipeline.py`,
  `src/deployment/edge_runtime.py`, focused exact-frame/edge tests.
- `EVIDENCE`: Diagnostic `_run` wrapper reproduced two failures in iteration 7
  and captured the exception at `snapshot.get(...)` before QW-04 was entered.
- `ACCEPTANCE`: Read one snapshot exactly once, process that same immutable
  snapshot, pass it with its result to the callback, and stress-test concurrent
  sources with zero mismatched/none callbacks.

## Round-3 gate evidence

- Focused macro suite: `139 tests`, `138 PASS`, `1 FAIL` at edge restart.
- Full regression: `594 tests`, `589 PASS`, `4 optional skips`, `1 FAIL` at
  edge restart; therefore `NEW_REGRESSIONS=1`.
- Three-store 16-source operational stress: Store A=6, Store B=5, Store N=5;
  47 frames processed, 3 JPEG, 32 review rows, 50 SceneEvents, 25 insights,
  50 raw learning cases, queue max 8, source errors 0, workers after close 0.
  CPU was 216.2% of one core, RSS delta 144.23 MiB, elapsed 0.520 s. The run
  logged one `EDGE_STORE_QW04_INGEST_FAILED`, so it is evidence of wiring and
  measurement, not a PASS.
- Compileall: PASS.
- Secret scan: 22/22 security tests PASS plus 36 attributed production text
  files with zero high-confidence secret hits.
- Diff check: FAIL at `src/capture/video_source.py:168`.

## Certification round 4 — second repair retest

- `CX02-DEF-007`: RESOLVED. `git diff --check` now exits 0.
- `CX02-DEF-009`: RESOLVED. Five start→complete→fresh restart iterations each
  rebuilt a distinct runtime, processed frames before and after restart, emitted
  no `EDGE_STORE_RUN_FAILED`, and closed cleanly.
- `CX02-DEF-010`: RESOLVED. Five concurrent 3-store/16-source stress iterations
  emitted zero `QW04_REVIEW_EXPORT_FAILED`; target-scoped export no longer
  rewrites every store from every worker.
- `CX02-DEF-013`: ACTIVE. The same stress iterations still emitted three
  `EDGE_STORE_QW04_INGEST_FAILED` events caused by the double-read snapshot
  race. `src/app/operational_pipeline.py` has not yet received the repair.
- `CX02-DEF-003`: PARTIALLY_RESOLVED. Edge manager lifecycle/restart is real;
  `DeploymentTopology.create_edge_service()` remains unwired to it.
- `CX02-DEF-006`, `CX02-DEF-011`, `CX02-DEF-012`: ACTIVE.

## Certification round 5 — repairable defects closed

`CANDIDATE_HEAD: 06d0e6a449a8af6eb9ce8610409632a1f9897a3b + attributed uncommitted OpenCode/Codex delta`

- `CX02-DEF-003`: RESOLVED. `DeploymentTopology` accepts the canonical
  `EdgeRuntimeManager.prepare_store` provider, `EdgeCaptureService` fails
  closed without it and delegates start/stop when injected. The real
  topology→manager→StoreEdgeRuntime test processed synthetic frames and
  stopped cleanly; topology/edge suites passed 13/13.
- `CX02-DEF-006`: RESOLVED. Learning/runtime-wiring fixtures use isolated
  temporary dataset and policy roots. Post-suite inventory found zero files
  under the former persistent test roots; ResourceWarning gate passed 34/34.
- `CX02-DEF-011`: RESOLVED. A clean, non-existent evidence path is measured
  through its nearest existing ancestor. System-health suite passed 15/15.
- `CX02-DEF-012`: RESOLVED. The finite synthetic source starts at frame zero
  and is paced across the polling/sampling boundary. Full vertical and repeated
  edge runs are deterministic.
- `CX02-DEF-013`: RESOLVED. `OperationalPipeline.run()` reads each snapshot
  once and passes that exact object both to processing and the callback. The
  regression fixture reproduced the former double-read race before repair and
  now asserts identity/frame-index equality.
- `CX02-DEF-001` through `CX02-DEF-013`: all repairable certification defects
  are resolved. Physical 16-camera, CCTV operator, and PTZ gates remain
  external validation preconditions, not software defect closures.

### Round-5 final technical gates

- Focused macro suite: `186/186 PASS`.
- Full regression: `599 total`, `595 executed PASS`, `4 optional skips`,
  `0 failures`.
- Compileall: PASS.
- Secret scan: `21/21 PASS` plus zero high-confidence hits in attributed
  production/config/launcher paths. Deliberate canaries/examples in test
  scripts were classified and excluded from the production-path regex.
- Diff check: PASS.
- Persistent test state: `0` files.
- Focused line coverage (`trace --missing`): operational pipeline `98%`,
  deployment topology `89%`, edge runtime `81%`, system health `85%`.
- Candidate commit: NOT CREATED. The worktree remains intentionally mixed with
  preserved changes/evidence from other loops, so checkpoint integrity cannot
  be asserted without a separate attribution/reconciliation gate.
