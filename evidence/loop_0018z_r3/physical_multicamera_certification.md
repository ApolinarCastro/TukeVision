# LOOP-0018Z-R3 physical certification

CAM_001_VIEW: NOT_CERTIFIED (launcher legacy source selection is single-source)
CAM_002_VIEW: NOT_CERTIFIED
CAM_003_VIEW: NOT_CERTIFIED
CAM_004_VIEW: NOT_CERTIFIED
FOUR_CAMERA_VIEW: NOT_CERTIFIED
FRAME_SOURCE: `UiController.poll_multicamera()` drives the four Tk cells
UI_CAPTURE_OWNER: NO
DIRECT_UI_VIDEOCAPTURE: NO
DIRECT_UI_RTSP: NO
SECOND_PROCESSING_PIPELINE: NO
CAMERA_ISOLATION: unit-tested PASS
CLEAN_SHUTDOWN: unit-tested legacy path PASS; physical four-camera session not run
SECRET_LEAK: 0 observed

The physical renderer is now materialized and tested, but the existing official
launcher/application flow still starts one legacy source and does not expose a
four-source SourceManager session to Tk. No credential was requested and no
physical claim is made. Parent LOOP-0018Z was not resumed.
