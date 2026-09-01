"""Autonomous physical soak monitor for Phase 2 1800s certification.

Continuously captures telemetry, stream metrics, resource consumption,
and log error occurrences for evidence bundle generation.
"""

import csv
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
import psutil

SOAK_DIR = Path("evidence/phase2_physical_soak")
SOAK_DIR.mkdir(parents=True, exist_ok=True)
TIMESERIES_CSV = SOAK_DIR / "soak_timeseries.csv"
LIVENESS_CSV = SOAK_DIR / "09_liveness_timeseries.csv"

def get_latest_run_dir():
    evidence_path = Path("evidence")
    runs = [d for d in evidence_path.iterdir() if d.is_dir() and d.name.startswith("RUN-")]
    if not runs:
        return None
    return max(runs, key=lambda d: d.stat().st_mtime)

def get_latest_log():
    logs_path = Path("logs")
    logs = [f for f in logs_path.glob("tukevision-RUN-*.log") if f.is_file()]
    if not logs:
        return None
    return max(logs, key=lambda f: f.stat().st_mtime)

def scan_log_for_errors(log_path):
    if not log_path or not log_path.is_file():
        return {"telemetry_write_failed": 0, "review_export_failed": 0, "eof": 0, "stalls": 0, "errors": 0}
    
    text = ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
        
    tw_failed = len(re.findall(r"TELEMETRY_WRITE_FAILED", text))
    rw_failed = len(re.findall(r"QW04_REVIEW_EXPORT_FAILED", text))
    eof = len(re.findall(r"FFMPEG_EOF", text))
    stalls = len(re.findall(r"FFMPEG_STALL_DETECTED", text))
    errors = len(re.findall(r"ERROR \[", text))
    return {
        "telemetry_write_failed": tw_failed,
        "review_export_failed": rw_failed,
        "eof": eof,
        "stalls": stalls,
        "errors": errors
    }

def main():
    print("Iniciando monitor continuo de soak 1800s...")
    sys.stdout.flush()
    
    if not TIMESERIES_CSV.exists():
        with open(TIMESERIES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "elapsed_s", "timestamp", "run_id", "pid", "live", "stale", "total_accounted",
                "cpu_percent", "ram_rss_mb", "host_ram_percent", "threads", "handles",
                "ffmpeg_processes", "telemetry_write_failed", "review_export_failed",
                "ffmpeg_eof", "stalls", "total_errors"
            ])
            
    if not LIVENESS_CSV.exists():
        with open(LIVENESS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "elapsed_s", "stream_id", "state", "frame_age_s",
                "generation", "frames_received", "last_frame_seq", "is_live"
            ])

    start_time = time.monotonic()
    last_timeseries_time = 0.0
    target_proc = None
    
    while time.monotonic() - start_time < 2000:
        try:
            elapsed = time.monotonic() - start_time
            now_ts = datetime.datetime.now().isoformat()
            
            # Locate target process
            if target_proc is None or not target_proc.is_running():
                for p in psutil.process_iter(["pid", "name", "cmdline"]):
                    try:
                        cmd = " ".join(p.info["cmdline"] or [])
                        if "python" in (p.info["name"] or "").lower() and "run_multicamera.py" in cmd:
                            target_proc = p
                            print(f"Detectado proceso TukeVision PID {target_proc.pid}")
                            sys.stdout.flush()
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
            run_dir = get_latest_run_dir()
            log_path = get_latest_log()
            
            # Read live_status.json
            live_data = {}
            if run_dir and (run_dir / "live_status.json").exists():
                try:
                    with open(run_dir / "live_status.json", encoding="utf-8") as f:
                        live_data = json.load(f)
                except Exception:
                    pass
                    
            cameras = live_data.get("cameras", {})
            live_count = sum(1 for c in cameras.values() if c.get("live"))
            stale_count = sum(1 for c in cameras.values() if not c.get("live"))
            
            # Record 10s liveness
            for cid, cinfo in cameras.items():
                age_val = cinfo.get("frame_age_s")
                age_rounded = round(float(age_val), 2) if age_val is not None else -1.0
                with open(LIVENESS_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        now_ts, round(elapsed, 1), cid, cinfo.get("liveness_state", "UNKNOWN"),
                        age_rounded, cinfo.get("reconnect_count", 0),
                        live_data.get("trace", {}).get(cid, {}).get("FRAME_RECEIVED", 0),
                        cinfo.get("frame_sequence", 0), 1 if cinfo.get("live") else 0
                    ])
                    
            # Record 60s timeseries
            if time.monotonic() - last_timeseries_time >= 60.0 or last_timeseries_time == 0.0:
                last_timeseries_time = time.monotonic()
                
                # System metrics
                cpu_pct = 0.0
                ram_mb = 0.0
                threads_count = 0
                handles_count = 0
                if target_proc and target_proc.is_running():
                    try:
                        cpu_pct = target_proc.cpu_percent(interval=None)
                        ram_mb = target_proc.memory_info().rss / (1024 * 1024)
                        threads_count = target_proc.num_threads()
                        handles_count = target_proc.num_handles() if hasattr(target_proc, "num_handles") else 0
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
                host_ram = psutil.virtual_memory().percent
                ffmpeg_count = len([p for p in psutil.process_iter(["name"]) if "ffmpeg" in (p.info["name"] or "").lower()])
                errs = scan_log_for_errors(log_path)
                
                with open(TIMESERIES_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        round(elapsed, 1), now_ts, live_data.get("run_id", "UNKNOWN"),
                        target_proc.pid if target_proc else 0, live_count, stale_count, len(cameras),
                        round(cpu_pct, 1), round(ram_mb, 1), host_ram, threads_count, handles_count,
                        ffmpeg_count, errs["telemetry_write_failed"], errs["review_export_failed"],
                        errs["eof"], errs["stalls"], errs["errors"]
                    ])
                print(f"[{now_ts}] Elapsed: {int(elapsed)}s | Live: {live_count}/15 | RAM: {round(ram_mb,1)}MB | FFmpeg Procs: {ffmpeg_count} | Errs: {errs}")
                sys.stdout.flush()
        except Exception as exc:
            import traceback
            print(f"Error en iteracion soak_monitor: {exc}")
            traceback.print_exc()
            sys.stdout.flush()
            
        time.sleep(10.0)

if __name__ == "__main__":
    main()
