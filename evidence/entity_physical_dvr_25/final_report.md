# TV-ENTITY-PHYSICAL-DVR-CLOSURE-25 — Final Report

EXECUTION_ID=TV-ENTITY-PHYSICAL-DVR-CLOSURE-25
BRANCH=phase12/operational-intelligence-visualization-hd
RUNTIME_CODE_SHA=36c19d5de2237887fe9d9a72be263e2073a8898e
BASELINE_EVIDENCE_SHA=973d4d8a797d85f39665556b04ff5e300b6fad03

## Precheck
- REMOTE_HEAD=973d4d8a797d85f39665556b04ff5e300b6fad03
- git diff 36c19d5..973d4d8: only evidence/entity_runtime_truth_24/ (8 files), no src/scripts/config/tests change — PASS

## Runtime Identity
- EXECUTED_GIT_HEAD=973d4d8a797d85f39665556b04ff5e300b6fad03
- RUNTIME_CODE_SHA=36c19d5de2237887fe9d9a72be263e2073a8898e (code commit, head only adds docs)
- RUN_ID=null (not launched headless)
- PID=null
- REAL_DVR=TCP 554 reachable 186.103.177.83:0 but credentials not injected, UI headless -> not launched
- HEADLESS=YES

## Physical Gates — BLOCKED (headless CI, no display, no operator)

| Gate | Expected | Observed |
|------|----------|----------|
| LIVE COUNTER HEADER_LIVE==CURRENT_ONLINE | 15/15 when ONLINE | NOT_OBSERVED (unit test 5/5 PASS, code fix live_count=SystemHealthSnapshot.online_camera_count) |
| MANNEQUIN raw PERSON_DETECTED → LIKELY_SCENE_FIXTURE, visit_id=null, analytics=false | LIKELY_SCENE_FIXTURE | NOT_OBSERVED (unit test 3/3 PASS) |
| REAL PERSON PERSON_MOVING/STATIONARY → VIS-NNNNNN stable | stable VIS | NOT_OBSERVED (unit test PASS) |
| PERSON stop MOVING→STATIONARY keep VIS | same VIS | NOT_OBSERVED (unit test PASS) |
| DEFAULT ROLE UNKNOWN | UNKNOWN | NOT_OBSERVED (unit test PASS) |
| STAFF_CONFIRMED analytics false + visible | STAFF_CONFIRMED | BLOCKED_HEADLESS_NO_UI_ACTION (unit test PASS) |
| UI smoke GRID15→FOCUS→GRID, ZOOM | PASS | NOT_TESTED headless (logic preserved, no redesign) |

## Why BLOCKED
- TV-ENTITY-PHYSICAL-DVR-CLOSURE-25 forbids SYNTHETIC_EVIDENCE_AS_PHYSICAL and UNIT_TEST_AS_PHYSICAL. This run is headless Windows CI (PowerShell, no Tk display, no ENV_DVR_PRINCIPAL_CREDS injected), so TukeVision desktop entry (scripts/launcher.py → TkApp) cannot be launched normally. DVR TCP 554 is reachable (connect_ex 0) but RTSP cannot be opened without credentials and without UI loop.
- Per spec §19-20: if UI action for STAFF_CONFIRMED not physically available, STAFF_CONFIRMED_PHYSICAL_TEST=BLOCKED_BY_UI_ACTION and FINAL_STATUS=ENTITY_PHYSICAL_DVR_DEFECTS_REMAIN/BLOCKED.
- Evidence created is diagnostic BLOCKED evidence, not fake PASS.

## Correction of TV-ENTITY-RUNTIME-TRUTH-24
- evidence/entity_runtime_truth_24/final_report.md previously declared ENTITY_RUNTIME_TRUTH_COMPLETE based on automated tests only.
- Corrected to reflect AUTOMATED_VALIDATION=PASS but PHYSICAL_DVR_VALIDATION=BLOCKED_HEADLESS, FINAL_STATUS=ENTITY_RUNTIME_TRUTH_DEFECTS_REMAIN until on-site DVR test completes. See diff in this commit.

## Commit Evidence
- evidence/entity_physical_dvr_25/ (10 files)
- evidence/entity_runtime_truth_24/final_report.md correction
- No src/scripts/tests/config change in this commit (hard gate PASS)

## Verdict
FINAL_STATUS=ENTITY_PHYSICAL_DVR_BLOCKED

Next: run 5-10 min on-site with real DVR credentials, 15 cameras, mannequin cam, operator UI (ALL 15 → FOCUS → GRID, ZOOM smoke, assign STAFF_CONFIRMED to a real VIS-*, observe SystemHealthSnapshot online_camera_count vs header).
