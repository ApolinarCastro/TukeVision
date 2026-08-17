# UI reuse check

Classification: `REUSE_WITH_MINIMAL_ADAPTATION`.

The existing Tk path (`TkApp._set_photo`, `Tk.after` polling, and
`UiController.poll_visual`) already renders latest-wins snapshots. R1 adds
only `MultiCameraViewModel`, a bounded presentation adapter with four fixed
panel slots. It consumes snapshots supplied by the certified manager/pipeline;
it owns no RTSP source, `cv2.VideoCapture`, processing thread, or inference.

Layout is fixed as CAM-001/CAM-002 over CAM-003/CAM-004. Offline state is held
per panel so one unavailable camera cannot block the others.
