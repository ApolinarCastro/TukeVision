# TV-ENTITY-PHYSICAL-ONSITE-VALIDATION-26 — Final Report

EXECUTION_ID=TV-ENTITY-PHYSICAL-ONSITE-VALIDATION-26
BRANCH=phase12/operational-intelligence-visualization-hd
RUNTIME_CODE_SHA=36c19d5de2237887fe9d9a72be263e2073a8898e
BASELINE_SHA=b7f4a9f5e24c76c586a1dff9909708efeb609bc7

## Status
BLOCKED — No operator launch during automated CI run (headless, no display).

- HEAD=b7f4a9f5e24c76c586a1dff9909708efeb609bc7 correctly contains runtime code 36c19d5 + evidence 973d4d8 + blocked evidence b7f4a9f.
- Config shows 15 cameras on 186.103.177.83:554 (TCP 554 reachable) but UI requires manual launch via scripts/launcher.py on real PC per §3.
- This run did NOT launch TukeVision; no RUN_ID/PID, no RTSP streams opened, no mannequin/person observed.

## Gates — All BLOCKED (awaiting on-site)
- GATE A HEADER 15/15: NOT_OBSERVED (code fix in place: live_count=SystemHealthSnapshot.online_camera_count, unit test 5/5 PASS)
- GATE B MANNEQUIN LIKELY_SCENE_FIXTURE visit_id=null analytics false: NOT_OBSERVED (validator unit test PASS)
- GATE C PERSON REAL VIS-NNNNNN stable: NOT_OBSERVED (visit manager unit test PASS)
- GATE D PERSON STATIONARY keeps VIS: NOT_OBSERVED
- GATE E ROLE UNKNOWN visible: NOT_OBSERVED
- GATE F STAFF_CONFIRMED: BLOCKED_NO_UI_ACTION (unit test PASS)
- GATE G GRID15 recoverable 3x5: NOT_TESTED headless
- GATE H FOCUS UI_FREEZE/BLACKOUT: NOT_TESTED
- GATE I ZOOM + pan + reset: NOT_TESTED
- GATE J SOURCE RESOLUTION truth: NOT_OBSERVED

## Governance
SYNTHETIC_AS_PHYSICAL=NO, UNIT_TEST_AS_PHYSICAL=NO — correctly not faked.

## Next
Operator must launch TukeVision on-site (double-click launcher, enter DVR creds, observe 5-10 min, capture live_counter/mannequin/real_person/staff JSONL, verify GRID/FOCUS/ZOOM, normal shutdown). Then re-run closure with real evidence.

FINAL_STATUS=ENTITY_PHYSICAL_DVR_BLOCKED
