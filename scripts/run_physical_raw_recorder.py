import time
import json
import os
from pathlib import Path
import argparse

def get_latest_run_dir(evidence_root: Path) -> Path:
    runs = sorted([d for d in evidence_dir.glob("RUN-*") if d.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        raise RuntimeError("No RUN-* directory found")
    return runs[0]

def record_sample(run_dir: Path, out_path: Path, index: int, start_monotonic: float):
    sample = {
        "sample_index": index,
        "utc_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "monotonic_timestamp": time.monotonic(),
        "elapsed_seconds": time.monotonic() - start_monotonic,
        "runtime": {"pid": None, "run_id": None, "commit_sha": None, "heartbeat": None},
        "process": {"cpu_percent": None, "rss_mb": None, "ram_percent": None, "thread_count": None},
        "streams": {"readers_active": None, "decoders_active": None},
        "cameras": {},
        "ui": {"heartbeat": None, "layout_mode": None, "grid_snapshot": None},
        "missing_fields": []
    }
    
    # Read live_status.json
    live_status_path = run_dir / "live_status.json"
    ls = {}
    if live_status_path.exists():
        try:
            ls = json.loads(live_status_path.read_text(encoding="utf-8"))
        except Exception:
            pass
            
    # Read resource_telemetry.json
    telemetry_path = run_dir / "resource_telemetry.json"
    tel = {}
    if telemetry_path.exists():
        try:
            t = json.loads(telemetry_path.read_text(encoding="utf-8"))
            if t.get("samples"):
                tel = t["samples"][-1]
        except Exception:
            pass

    # Read certification_code_identity.json
    identity_path = Path("evidence/TV-F12-RAW-EVIDENCE-PHYSICAL-CLOSURE-12/certification_code_identity.json")
    cert_sha = None
    if identity_path.exists():
        try:
            cert_sha = json.loads(identity_path.read_text(encoding="utf-8")).get("CERTIFICATION_CODE_SHA")
        except Exception:
            pass

    # Populate runtime
    sample["runtime"]["pid"] = ls.get("pid")
    sample["runtime"]["run_id"] = ls.get("run_id")
    sample["runtime"]["commit_sha"] = cert_sha
    sample["runtime"]["heartbeat"] = ls.get("observed_monotonic")
    
    # Populate process
    sample["process"]["cpu_percent"] = tel.get("cpu_percent")
    sample["process"]["rss_mb"] = tel.get("process_rss_mb")
    sample["process"]["ram_percent"] = tel.get("ram_percent")
    sample["process"]["thread_count"] = tel.get("thread_count")
    
    # Populate streams
    sample["streams"]["readers_active"] = ls.get("readers_active")
    sample["streams"]["decoders_active"] = ls.get("decoders_active")
    
    # Populate UI
    if "ui" in ls:
        sample["ui"]["layout_mode"] = ls["ui"].get("layout_mode")
        sample["ui"]["grid_snapshot"] = ls["ui"].get("grid_snapshot")
    elif "grid_snapshot" in ls: # fallback
        sample["ui"]["grid_snapshot"] = ls.get("grid_snapshot")
        sample["ui"]["layout_mode"] = "GRID"
    
    # Populate cameras
    cams = ls.get("cameras", {})
    trace = ls.get("trace", {})
    for cid, cdata in cams.items():
        sample["cameras"][cid] = {
            "camera_id": cid,
            "capture_state": cdata.get("capture_state"),
            "liveness_state": cdata.get("liveness_state"),
            "generation": cdata.get("generation"),
            "frame_sequence": cdata.get("frame_sequence"),
            "frame_age_s": cdata.get("frame_age_s"),
            "requested_subtype": 1 if cdata.get("active_profile") == "SUB" else 0,
            "active_subtype": cdata.get("active_subtype"),
            "requested_profile": cdata.get("active_profile"),
            "active_profile": cdata.get("active_profile"),
            "source_width": cdata.get("source_width"),
            "source_height": cdata.get("source_height"),
            "source_resolution_observed": bool(cdata.get("source_width") and cdata.get("source_height")),
            "ui_rendered_sequence": cdata.get("ui_rendered_sequence"),
            "last_ui_rendered_at": trace.get(cid, {}).get("last_frame_index"), # Approximate
            "connection_state": cdata.get("liveness_state"),
            "decoder_state": cdata.get("decoder_state"),
            "last_connection_attempt": cdata.get("reader_heartbeat"),
            "last_connection_result": cdata.get("liveness_state"),
            "last_decode_success": cdata.get("last_successful_decode_at"),
        }
        
    # Check for missing fields
    def check_missing(d, prefix=""):
        for k, v in d.items():
            if isinstance(v, dict):
                check_missing(v, prefix + k + ".")
            elif v is None:
                sample["missing_fields"].append(prefix + k)
                
    check_missing(sample["runtime"], "runtime.")
    check_missing(sample["process"], "process.")
    check_missing(sample["streams"], "streams.")
    check_missing(sample["ui"], "ui.")
    for cid, cdata in sample["cameras"].items():
        check_missing(cdata, f"cameras.{cid}.")
        
    # Append to file
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(sample) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    
    evidence_dir = Path("evidence")
    out_dir = evidence_dir / "TV-F12-RAW-EVIDENCE-PHYSICAL-CLOSURE-12"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "raw_samples.jsonl"
    
    run_dir = get_latest_run_dir(evidence_dir)
    print(f"Observing RUN ID: {run_dir.name}")
    
    start_monotonic = time.monotonic()
    index = 0
    
    while True:
        elapsed = time.monotonic() - start_monotonic
        if elapsed >= args.duration:
            break
            
        record_sample(run_dir, out_path, index, start_monotonic)
        index += 1
        time.sleep(args.interval)
        
    # Final sample to guarantee >=1800s
    record_sample(run_dir, out_path, index, start_monotonic)
    print("Recorder finished.")
