# C2 Operational Baseline

CODE_SHA=7c1caed23d18523b2630b4167ee0bed24229d60d
RUN_TIMESTAMP=2026-08-31T15:55:34Z
CAMERAS_OBSERVED=15

## Metrics

Operational telemetry collected across 15 RTSP cameras during continuous live operation (RUN-59C253, 365.5s uptime):

| Camera ID | Profile | Subtype | Resolution | State | Frame Age Count | Frame Age p50 (ms) | Frame Age p95 (ms) | TTFF p50 (ms) |
|---|---|---|---|---|---|---|---|---|
| cam_01 | SUB | 1 | 352x240 | OPEN | 90 | 484.5 | 2726.8 | 350.0 |
| cam_02 | SUB | 1 | 352x240 | OPEN | 90 | 484.5 | 3457.7 | 380.0 |
| cam_03 | SUB | 1 | 352x240 | OPEN | 90 | 547.0 | 2801.7 | 410.0 |
| cam_04 | SUB | 1 | 352x240 | CONNECTING | 90 | 672.5 | 5548.65 | 440.0 |
| cam_05 | SUB | 1 | 352x240 | OPEN | 90 | 570.0 | 4418.05 | 420.0 |
| cam_06 | SUB | 1 | 352x240 | OPEN | 90 | 469.0 | 2403.95 | 460.0 |
| cam_07 | SUB | 1 | 352x240 | OPEN | 90 | 531.0 | 3525.0 | 520.0 |
| cam_08 | SUB | 1 | 352x240 | OPEN | 90 | 562.5 | 2139.55 | 890.0 |
| cam_09 | SUB | 1 | 352x240 | OPEN | 90 | 773.5 | 19616.1 | 950.0 |
| cam_10 | SUB | 1 | 352x240 | OPEN | 90 | 453.0 | 2274.25 | 430.0 |
| cam_11 | SUB | 1 | 352x240 | OPEN | 90 | 515.5 | 2398.8 | 480.0 |
| cam_12 | SUB | 1 | 352x240 | OPEN | 90 | 664.5 | 19059.85 | 1850.0 |
| cam_13 | SUB | 1 | 352x240 | OPEN | 90 | 453.0 | 2325.95 | 390.0 |
| cam_14 | SUB | 1 | 352x240 | OPEN | 90 | 844.0 | 17075.85 | 370.0 |
| cam_15 | SUB | 1 | 352x240 | OPEN | 90 | 1359.5 | 8134.15 | 510.0 |

## Outliers

Relative outlier analysis against fleet median (Q3 + 1.5 * IQR):
- `cam_09`: frame_age_ms p95 reached 19616.1 ms.
- `cam_12`: frame_age_ms p95 reached 19059.85 ms.
- `cam_14`: frame_age_ms p95 reached 17075.85 ms.

## Bottleneck Classification

**Classification:** `B5_CAMERA_SPECIFIC`

**Rationale:**
1. Most cameras deliver consistent latency with healthy reader and decoder threads.
2. The tail latency is localized to specific DVR channels (`cam_08`, `cam_09`, `cam_12`, `cam_15`) undergoing reconnection stalls or processing delays.
3. System resources show no global compute or UI bottleneck.

## Evidence

- `evidence/c2_operational_baseline/c2_metrics_raw.json`
- `evidence/c2_operational_baseline/c2_metrics_summary.json`
- `evidence/c2_operational_baseline/c2_camera_outliers.json`
- `evidence/RUN-59C253/live_status.json`
- `evidence/RUN-59C253/resource_telemetry.json`
- `evidence/RUN-59C253/runtime_trace.json`

## Next Candidate

`NEXT_CANDIDATE=CAMERA_SPECIFIC_DIAGNOSTIC`

## Decision

`DECISION=NEXT=CAMERA_SPECIFIC_DIAGNOSTIC`
`IMPLEMENT_NOW=NO`

Investigate DVR channel configuration, network path, and RTSP stream profiles for outlier cameras in a dedicated diagnostic task.
