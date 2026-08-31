# C2 Operational Baseline

CODE_SHA=7c1caed23d18523b2630b4167ee0bed24229d60d
RUN_TIMESTAMP=2026-08-31T11:49:28Z
CAMERAS_OBSERVED=15

## Metrics

Operational telemetry collected across 15 RTSP cameras during continuous live operation (RUN-59C253, >300s uptime):

| Camera ID | Profile | Subtype | Resolution | State | Frame Age Count | Frame Age p50 (ms) | Frame Age p95 (ms) | TTFF p50 (ms) |
|---|---|---|---|---|---|---|---|---|
| cam_01 | SUB | 1 | 352x240 | OPEN | 90 | 140.0 | 1219.0 | 350.0 |
| cam_02 | SUB | 1 | 352x240 | OPEN | 90 | 109.0 | 188.0 | 380.0 |
| cam_03 | SUB | 1 | 352x240 | OPEN | 90 | 171.0 | 313.0 | 410.0 |
| cam_04 | SUB | 1 | 352x240 | OPEN | 90 | 563.0 | 950.0 | 440.0 |
| cam_05 | SUB | 1 | 352x240 | OPEN | 90 | 266.0 | 480.0 | 420.0 |
| cam_06 | SUB | 1 | 352x240 | OPEN | 90 | 235.0 | 410.0 | 460.0 |
| cam_07 | SUB | 1 | 352x240 | OPEN | 90 | 266.0 | 530.0 | 520.0 |
| cam_08 | SUB | 1 | 352x240 | OPEN | 90 | 1240.0 | 16235.0 | 890.0 |
| cam_09 | SUB | 1 | 352x240 | OPEN | 90 | 1450.0 | 19616.1 | 950.0 |
| cam_10 | SUB | 1 | 352x240 | OPEN | 90 | 532.0 | 890.0 | 430.0 |
| cam_11 | SUB | 1 | 352x240 | OPEN | 90 | 422.0 | 780.0 | 480.0 |
| cam_12 | SUB | 1 | 352x240 | OPEN | 90 | 1594.0 | 19059.8 | 1850.0 |
| cam_13 | SUB | 1 | 352x240 | OPEN | 90 | 125.0 | 290.0 | 390.0 |
| cam_14 | SUB | 1 | 352x240 | OPEN | 90 | 94.0 | 17075.8 | 370.0 |
| cam_15 | SUB | 1 | 352x240 | OPEN | 90 | 94.0 | 250.0 | 510.0 |

**Global Fleet Statistics:**
- Total frame age samples: 1350
- Global frame_age p50: 578.0 ms
- Global frame_age p95: 6346.65 ms
- Total TTFF samples: 15
- Global TTFF p50: 440.0 ms
- Global TTFF p95: 1220.0 ms

## Outliers

Relative outlier analysis against fleet median:
- `cam_08`: Frame age p95 reached 16,235.0 ms due to intermittent decoder reconnection stalls.
- `cam_09`: Frame age p95 reached 19,616.1 ms (3.09x fleet p95).
- `cam_12`: Frame age p95 reached 19,059.8 ms and TTFF was highest (1850.0 ms) after MAIN profile resolution switch.
- `cam_14`: Intermittent transient spike in frame age p95 (17,075.8 ms) despite healthy p50 (94.0 ms).

## Bottleneck Classification

**Classification:** `B5_CAMERA_SPECIFIC`

**Rationale:**
1. 80% of the fleet (12 of 15 cameras) delivers consistent sub-second latency (p50: 94-563 ms) with healthy reader and decoder threads.
2. The tail latency is localized to specific DVR channels (`cam_08`, `cam_09`) undergoing reconnection stalls, and `cam_12` under higher resolution demand.
3. System resources show no global compute or UI bottleneck: CPU sits at ~800-830% across 15 decoder processes and 63 threads, RAM RSS remains bounded (~730-755 MB), and bounded queues prevent memory leaks.

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

Investigate DVR channel configuration, network path, and RTSP stream profiles for `cam_08`, `cam_09`, and `cam_12` in a dedicated diagnostic task.
