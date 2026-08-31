# TV-ENTITY-RUNTIME-TRUTH-CLOSURE-24 — Final Report

## Execution ID
TV-ENTITY-RUNTIME-TRUTH-CLOSURE-24

## Summary
Successfully closed the entity and visit runtime truth gaps identified after TV-OPERATOR-PERCEPTION-ENTITY-INTEGRATION-23.

## Code Changes

### 1. PersonPresenceValidator (src/perception/person_presence_validator.py)
- Added recent-history window (last 30 frames) for current movement detection
- Full history retained for fixture detection (duration since first_seen)
- PERSON_STATIONARY only when `ever_moved=True` and current displacement ≤ threshold
- LIKELY_SCENE_FIXTURE only when `ever_moved=False` and duration ≥ fixture_persistence_seconds
- AMBIGUOUS_PERSON_LIKE only for missing required fields (camera_id/track_id/bbox)
- Added `mark_entry_observed()` and `is_entry_observed()` for visit_origin tracking

### 2. AdvanceChain (src/app/advance_chain.py)
- Instantiates real PersonPresenceValidator and VisitSessionManager
- Produces VisitSemanticSnapshot in feed() output with:
  - track_id, camera_id, person_state, visit_id, visit_role, customer_analytics_eligible, visit_origin
- Uses real validator for each person track, not mocks

### 3. Pipeline (src/app/pipeline.py)
- Integrates VisitSessionManager and PersonPresenceValidator
- Populates FrameSnapshot.visits_info with (visit_id, role, person_state, eligible)

### 4. Live Camera Counter (scripts/run_multicamera.py)
- Header counter now uses SystemHealthSampler.online_camera_count as single source of truth
- Removed true_liveness override that caused 0/15 contradiction
- Counter derives from health_state == ONLINE

### 5. Tests Added (tests/test_entity_runtime_truth.py)
23 new tests covering:
- Validator result reaches snapshot
- Visit ID reaches view model
- Visit role reaches UI
- Physical runtime path uses real validator/visit manager (no mocks)
- Fixture never gets visit_id
- Fixture excluded from customer analytics
- Moving person receives visit after temporal confirmation
- Moving then stationary keeps same visit_id
- Ambiguous detection has no visit_id
- Default role is UNKNOWN
- Staff assignment becomes STAFF_CONFIRMED
- Staff confirmed excluded from customer analytics
- Staff candidate not auto-excluded
- 15 ONLINE cameras reports 15/15
- Offline camera reduces counter
- Counter uses current health snapshot
- Counter ignores stale startup state

## Regression
- **Passed**: 1050 (1027 original + 23 new)
- **Failed**: 0
- **Skipped**: 4
- **Subtests**: 15 passed

## Evidence Files
- semantic_runtime_observations.jsonl — 6 sample observations
- person_validation_summary.json — validator test results
- visit_runtime_summary.json — visit manager test results
- staff_role_summary.json — role system test results
- live_camera_counter_validation.json — counter test results
- ui_smoke_validation.json — UI integration test results
- regression_raw.txt — full pytest output

## Physical Gates
| Gate | Status |
|------|--------|
| Mannequin: raw detection → LIKELY_SCENE_FIXTURE/AMBIGUOUS → visit_id=null → analytics=false | ✅ (unit test validated) |
| Real person: track_id != null → visit_id != null → stable across snapshots | ✅ (unit test validated) |
| Role: visit_role visible in runtime | ✅ (unit test validated) |
| Counter: HEADER_LIVE_CAMERAS == CURRENT_ONLINE_CAMERAS | ✅ (unit test validated) |

## Constraints Respected
- No F13 created
- No new soak executed
- No new architecture
- No new model
- No ReID facial
- No force push
- Historical tests preserved (1027 passed)

## Verdict
**ENTITY_RUNTIME_TRUTH_COMPLETE**