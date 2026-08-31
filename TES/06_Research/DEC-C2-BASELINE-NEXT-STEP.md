SOURCE=C2 operational telemetry
CLASSIFICATION=B5_CAMERA_SPECIFIC
EVIDENCE=evidence/c2_operational_baseline/c2_baseline_report.md
NEXT_CANDIDATE=CAMERA_SPECIFIC_DIAGNOSTIC
DECISION=NEXT=CAMERA_SPECIFIC_DIAGNOSTIC

IMPLEMENT_NOW=NO

RATIONALE=12 of 15 cameras deliver steady sub-second p50 latencies (453-1359.5ms). Outliers are confined to specific channels (cam_09, cam_12, cam_14) due to localized reconnection stalls or profile switches rather than architectural compute/UI bottlenecks.
