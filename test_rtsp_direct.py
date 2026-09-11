import os
import json
import sys
import time

# This will be set by the operator
# os.environ['ENV_DVR_PRINCIPAL_CREDS'] = '{"username": "admin", "password": "ACTUAL_PASSWORD"}'

sys.path.insert(0, '.')

from src.capture.source_manager import SourceManager, CameraDescriptor
from src.capture.live_sources import SourceState

# Test with the actual password from environment
creds_json = os.environ.get('ENV_DVR_PRINCIPAL_CREDS', '')
if not creds_json:
    print("ERROR: Set ENV_DVR_PRINCIPAL_CREDS environment variable first")
    sys.exit(1)

creds = json.loads(creds_json)
username = creds.get('username', '')
password = creds.get('password', '')

print(f"Testing with username={username}, password={password[:3]}...")

# Create source manager
manager = SourceManager()

# Test CAM-01
descriptor = CameraDescriptor(
    camera_id="cam_01",
    host="rtsp://186.103.177.83:554/cam/realmonitor?channel=1&subtype=0",
    channel=1,
    subtype=0,
    username=username,
    password=password,
    max_width=640,
    process_every_n_frames=1,
    frame_stall_timeout_s=10.0,
    rtsp_open_timeout_ms=8000,
)

manager.register_source(descriptor)

print("Starting source...")
meta = manager.start("cam_01")
print(f"Metadata: {meta}")

print("Waiting for frames...")
for i in range(30):
    snapshot = manager.snapshot("cam_01")
    if snapshot and snapshot.get("frame") is not None:
        frame = snapshot["frame"]
        print(f"SUCCESS: Got frame {snapshot['frame_index']} - shape={frame.shape}, state={snapshot['state']}")
        break
    state = snapshot.get("state", "UNKNOWN") if snapshot else "NO_SNAPSHOT"
    print(f"  Attempt {i+1}: state={state}")
    time.sleep(1)
else:
    print("TIMEOUT: No frame received")

manager.close_all()
print("Done")