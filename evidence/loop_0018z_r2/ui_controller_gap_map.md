# UiController gap map

`UiController` previously consumed one `poll_visual()` snapshot and TkApp
rendered one label. R2 generalizes only the presentation boundary:

- `GENERALIZE_SINGLE_TO_MULTI`: add four-key latest-wins model.
- `ADD_MINIMAL_ORCHESTRATION`: `ingest_camera_snapshot(camera_id, snapshot)`.
- `REUSE_EXISTING_API`: upstream callers provide already-produced snapshots;
  no SourceManager or OperationalPipeline changes are needed.
- `LEGACY_COMPAT_REQUIRED`: existing `start`, `poll_visual`, and single-camera
  state remain unchanged.

No UI method opens RTSP, creates captures, starts capture threads, or invokes
inference.
