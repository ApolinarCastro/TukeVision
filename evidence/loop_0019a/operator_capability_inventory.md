# LOOP-0019A operator capability inventory

| Capability | Exists | Integrated runtime | Visible operator |
|---|---|---|---|
| 4 CCTV | YES | YES | YES, 2×2 renderer |
| Detection | YES | YES | AVAILABLE_NOT_VISIBLE |
| Bounding boxes | YES | YES | AVAILABLE_NOT_VISIBLE |
| LocalTrack | YES | YES | AVAILABLE_NOT_VISIBLE |
| Track ID | YES | YES | AVAILABLE_NOT_VISIBLE in multicamera panel |
| TemporalActivity | YES | YES | AVAILABLE_NOT_VISIBLE |
| CrossCameraCorrelation | YES | YES | AVAILABLE_NOT_VISIBLE |
| BehaviorSignal | YES | YES | AVAILABLE_NOT_VISIBLE |
| RiskEvent | YES | YES | AVAILABLE_NOT_VISIBLE |
| Static Evidence | YES | YES | AVAILABLE_NOT_VISIBLE from operator UI |
| QW-04 Clip | TECHNICAL ADAPTER | SHADOW/TESTED | AVAILABLE_NOT_VISIBLE |
| Camera Health | YES | YES | YES, per-panel source state |

No fake data, overlays, or second pipeline were added. The operator UI currently
provides the live 2×2 frames and per-camera state; the remaining rows are
documented visibility gaps, not silently simulated.
