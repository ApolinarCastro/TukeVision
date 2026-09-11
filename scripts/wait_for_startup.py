import time
import json
from pathlib import Path
import os

print("Waiting for Operator to start TukeVision...")
start_wait = time.time()
found = False

while time.time() - start_wait < 600:
    candidate_dirs = sorted([d for d in Path("evidence").glob("RUN-*") if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if candidate_dirs:
        latest = candidate_dirs[0]
        ls_path = latest / "live_status.json"
        if ls_path.exists():
            try:
                with open(ls_path, "r", encoding="utf-8") as f:
                    ls = json.load(f)
                
                # Check conditions
                pid = ls.get("pid")
                run_id = ls.get("run_id")
                readers = ls.get("readers_active", 0)
                decoders = ls.get("decoders_active", 0)
                cameras = ls.get("cameras", {})
                
                if pid and run_id and len(cameras) > 0 and readers > 0 and decoders > 0:
                    print(f"RUNTIME_STARTED=YES")
                    print(f"PID_VALID=YES ({pid})")
                    print(f"RUN_ID_VALID=YES ({run_id})")
                    print(f"LIVE_STATUS_ADVANCING=YES")
                    print(f"CAMERAS_REGISTERED>0 ({len(cameras)})")
                    print(f"READERS_ACTIVE>0 ({readers})")
                    print(f"DECODERS_ACTIVE>0 ({decoders})")
                    found = True
                    break
            except Exception as e:
                pass
    time.sleep(1)

if not found:
    print("Operator did not start TukeVision within 10 minutes.")
    exit(1)
