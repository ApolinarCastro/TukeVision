import datetime
import json
import os
import psutil

def main():
    tukevision_procs = []
    ffmpeg_procs = []
    current_pid = os.getpid()
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] == current_pid:
                continue
            name = (p.info["name"] or "").lower()
            cmd = " ".join(p.info["cmdline"] or [])
            if "ffmpeg" in name:
                ffmpeg_procs.append(p.info["pid"])
            if "python" in name and ("run_multicamera.py" in cmd or "launcher.py" in cmd):
                tukevision_procs.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "clean_start_gate": "PASS" if len(tukevision_procs) == 0 and len(ffmpeg_procs) == 0 else "FAIL",
        "tukevision_processes": len(tukevision_procs),
        "ffmpeg_processes": len(ffmpeg_procs),
        "details": {
            "tukevision_pids": tukevision_procs,
            "ffmpeg_pids": ffmpeg_procs
        }
    }
    os.makedirs("evidence/phase2_physical_soak", exist_ok=True)
    with open("evidence/phase2_physical_soak/01_clean_start.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("01_clean_start.json generated:")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
