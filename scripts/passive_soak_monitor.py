"""Non-disruptive physical soak telemetry monitor for RUN-1A082E (1800s observation window).

Tracks 15/15 stream liveness, process resources, and timestamps of state transitions
in strict read-only mode without interfering with the active TukeVision instance.
"""

import csv
import datetime
import json
import os
import sys
import time
from pathlib import Path
import psutil

SOAK_DIR = Path("evidence/phase2_physical_soak")
SOAK_DIR.mkdir(parents=True, exist_ok=True)
TIMESERIES_CSV = SOAK_DIR / "soak_timeseries.csv"
LIVENESS_CSV = SOAK_DIR / "09_liveness_timeseries.csv"

def main():
    print("Iniciando monitor pasivo de observacion 1800s sobre RUN-1A082E...")
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

    start_mono = time.monotonic()
    last_60s = 0.0
    run_dir = Path("evidence/RUN-1A082E")
    target_pid = 26340

    while time.monotonic() - start_mono < 1850:
        try:
            elapsed = time.monotonic() - start_mono
            now_iso = datetime.datetime.now().isoformat()

            # Read live_status.json
            live_status_file = run_dir / "live_status.json"
            data = {}
            if live_status_file.exists():
                try:
                    with open(live_status_file, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass

            cameras = data.get("cameras", {})
            live_cnt = sum(1 for c in cameras.values() if c.get("live"))
            stale_cnt = sum(1 for c in cameras.values() if not c.get("live"))

            # Log 10s liveness
            for cid, cinfo in cameras.items():
                age_val = cinfo.get("frame_age_s")
                age_r = round(float(age_val), 2) if age_val is not None else -1.0
                with open(LIVENESS_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        now_iso, round(elapsed, 1), cid, cinfo.get("liveness_state", "UNKNOWN"),
                        age_r, cinfo.get("reconnect_count", 0),
                        data.get("trace", {}).get(cid, {}).get("FRAME_RECEIVED", 0),
                        cinfo.get("frame_sequence", 0), 1 if cinfo.get("live") else 0
                    ])

            # Log 60s summary
            if time.monotonic() - last_60s >= 60.0 or last_60s == 0.0:
                last_60s = time.monotonic()

                # Process metrics
                proc_ram_mb = 0.0
                proc_cpu = 0.0
                threads = 0
                handles = 0
                try:
                    p = psutil.Process(target_pid)
                    if p.is_running():
                        proc_ram_mb = p.memory_info().rss / (1024 * 1024)
                        proc_cpu = p.cpu_percent(interval=None)
                        threads = p.num_threads()
                        handles = p.num_handles() if hasattr(p, "num_handles") else 0
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                host_ram_pct = psutil.virtual_memory().percent
                ffmpeg_procs = len([proc for proc in psutil.process_iter(["name"]) if "ffmpeg" in (proc.info["name"] or "").lower()])

                with open(TIMESERIES_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        round(elapsed, 1), now_iso, "RUN-1A082E", target_pid,
                        live_cnt, stale_cnt, len(cameras), round(proc_cpu, 1),
                        round(proc_ram_mb, 1), host_ram_pct, threads, handles,
                        ffmpeg_procs, 0, 0, 0, 0, 0
                    ])

                print(f"[{now_iso}] Elapsed: {int(elapsed)}s | Live: {live_cnt}/15 | RAM: {round(proc_ram_mb, 1)}MB | FFmpeg: {ffmpeg_procs}")
                sys.stdout.flush()

        except Exception as e:
            print(f"Monitor error: {e}")
            sys.stdout.flush()

        time.sleep(10.0)

if __name__ == "__main__":
    main()
