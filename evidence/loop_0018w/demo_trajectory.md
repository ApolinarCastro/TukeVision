# Controlled three-camera trajectory demonstration

This output is a temporal/topological hypothesis, not identity evidence.

- TRAJECTORY_ID: `TRAJ-CF7A019C0B8B11DC`
- STATUS: `CANDIDATE`
- CAMERA_SEQUENCE: `CAM-01 → CAM-03 → CAM-04`
- TRACK_SEQUENCE: `TRK-CAM-01-001 → TRK-CAM-03-014 → TRK-CAM-04-008`
- START_TIME: `2026-08-17T12:00:00Z`
- END_TIME: `2026-08-17T12:00:15Z`
- LINK_COUNT: 2
- CORRELATION_COMPONENTS per edge: temporal `0.777778`, topology `1.0`,
  direction `1.0` (direction weight is zero because no direction was supplied).
- EVIDENCE_REFS: `CAM-01/E1/frame.jpg`, `CAM-03/E2/frame.jpg`,
  `CAM-04/E3/frame.jpg`.
- INTERPRETATION: `TRAJECTORY_HYPOTHESIS_NOT_IDENTITY`.

Run: `.venv\Scripts\python.exe scripts\demo_cross_camera_trajectory.py`.
