import datetime
import json
import os
import subprocess
import psutil

def main():
    branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    with open("config/default.json", encoding="utf-8") as f:
        cfg = json.load(f)
    cameras = []
    if os.path.exists("config/multistore.active.json"):
        with open("config/multistore.active.json", encoding="utf-8") as f:
            mcfg = json.load(f)
            for store in mcfg.get("multistore", {}).get("stores", []):
                for rec in store.get("recorders", []):
                    cameras.extend(rec.get("cameras", []))
    if not cameras:
        cameras = cfg.get("cameras", [])
        
    py_proc = len([p for p in psutil.process_iter(["name"]) if "python" in (p.info["name"] or "").lower()])
    ffmpeg_proc = len([p for p in psutil.process_iter(["name"]) if "ffmpeg" in (p.info["name"] or "").lower()])
    
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "git_branch": branch,
        "git_commit": commit,
        "python_version": "3.12.13",
        "configured_streams": len(cameras),
        "frame_stall_timeout_s": cfg.get("video", {}).get("frame_stall_timeout_s", 10.0),
        "active_python_processes": py_proc,
        "active_ffmpeg_processes": ffmpeg_proc,
    }
    
    os.makedirs("evidence/phase2_physical_soak", exist_ok=True)
    with open("evidence/phase2_physical_soak/00_preflight.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("00_preflight.json generated successfully:")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
