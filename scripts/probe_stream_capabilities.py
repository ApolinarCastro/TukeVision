"""Probe physical RTSP dimensions for SUB and MAIN profiles to prevent false HD claims."""
import sys
from pathlib import Path
import json
import cv2
import time

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.domain.catalog import StoreCatalog
from src.capture.rtsp_url import build_rtsp_url

def probe_stream(rtsp_url: str) -> tuple:
    """Connect to stream and wait for the first valid frame to measure its dimensions."""
    print(f"  Probing {rtsp_url[:30]}...")
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
    if not cap.isOpened():
        return (None, None)
    
    w, h = None, None
    for i in range(30):
        ret, frame = cap.read()
        if ret and frame is not None:
            h, w = frame.shape[:2]
            break
        time.sleep(0.1)
    cap.release()
    return w, h

def main():
    config = json.loads((BASE / "config/multistore.active.json").read_text(encoding="utf-8"))
    catalog = StoreCatalog.from_dict(config)
    import os
    creds_json = os.environ.get("ENV_DVR_PRINCIPAL_CREDS", "{}")
    try:
        creds = json.loads(creds_json)
        user = creds.get("username", "")
        pwd = creds.get("password", "")
    except Exception:
        user, pwd = "", ""

    entries = catalog.camera_descriptors(
        max_width=1280, 
        process_every_n_frames=1,
        credential_resolver=lambda r: (user, pwd)
    )
    
    results = {}
    print(f"Probing {len(entries)} cameras...")
    for entry in entries:
        cid = entry.camera_id
        print(f"Camera: {cid}")
        
        # Test SUB (subtype=1)
        sub_url = build_rtsp_url(host=entry.descriptor.host, username=user, password=pwd, channel=entry.descriptor.channel, subtype=1)
        w_sub, h_sub = probe_stream(sub_url)
        
        # Test MAIN (subtype=0)
        main_url = build_rtsp_url(host=entry.descriptor.host, username=user, password=pwd, channel=entry.descriptor.channel, subtype=0)
        w_main, h_main = probe_stream(main_url)
        
        results[cid] = {
            "SUB": f"{w_sub}x{h_sub}" if w_sub else "FAILED",
            "MAIN": f"{w_main}x{h_main}" if w_main else "FAILED",
            "HD_TRUE": bool(w_main and h_main and w_main >= 1280 and h_main >= 720)
        }
        print(f"  Result: {results[cid]}")

    out_file = BASE / "evidence/camera_stream_capabilities.json"
    out_file.parent.mkdir(exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2))
    print(f"Capabilities written to {out_file}")

if __name__ == "__main__":
    main()
