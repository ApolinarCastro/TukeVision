# Operational pipeline before LOOP-0018V

| Link | Existing operational implementation | Before classification |
|---|---|---|
| ENTRYPOINT | `scripts/run_interface.py` → `UiController` | CONNECTED |
| SOURCE CREATION | `build_source(FILE/WEBCAM/RTSP)` | CONNECTED |
| SOURCE MANAGER | Certified `src/capture/source_manager.py`, not called by UI | EXISTS_NOT_CONNECTED |
| FRAME CONSUMER | `Pipeline.process_source(..., on_frame=UiController._on_frame)` | CONNECTED |
| PIPELINE | Legacy single-source `src/app/pipeline.py` | CONNECTED |
| UI/CONTROLLER | `src/ui/controller.py` | CONNECTED |
| OBSERVATION | Legacy `ObservationEngine`; certified `ActivityLayer` detached | EXISTS_NOT_CONNECTED |
| INFERENCE | Legacy `PersonDetector`; certified selective pipeline detached | EXISTS_NOT_CONNECTED |
| EVENT | Legacy event engine; certified `EventDetector` detached | EXISTS_NOT_CONNECTED |
| TRACKING | Legacy `PersonTracker`; certified `LocalTracker` detached | EXISTS_NOT_CONNECTED |
| EVIDENCE | Alert-specific `EvidenceStore`; no stable operational `evidence_ref` | MISSING_ADAPTER |

## Surgical connection

The RTSP branch of the existing controller is the integration seam. It now
constructs the certified `SourceManager`, and `OperationalPipeline` polls each
camera snapshot into the existing `AdvanceChain`. FILE and WEBCAM retain the
legacy path. `PersistentEvidenceStore` is the minimum filesystem adapter;
policy-selected evidence is referenced before inference and the existing
contracts propagate the reference into event and local track.

No certified source, activity, inference, event, or tracker implementation is
copied or replaced.
