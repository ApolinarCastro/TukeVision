import json
import time
import os
import sys
import numpy as np
import cv2
from pathlib import Path

# Add project root to sys.path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src.capture.source_manager import SourceManager, CameraDescriptor
from src.app.advance_chain import AdvanceChain
from src.observability.runtime_trace import BoundedRuntimeTrace
from src.observability.resource_telemetry import ResourceTelemetry

def run_synthetic_multicamera_soak(duration_seconds=1800):
    print("=================================================================", flush=True)
    print(f"INICIANDO MULTICAMERA STABILITY SOAK ({duration_seconds}s) CON OPENVINO", flush=True)
    print("=================================================================", flush=True)
    
    # 1. Cargar configuración
    with open("config/default.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    config["inference"]["runtime"] = "openvino"
    config["inference"]["backend"] = "yolo"
    
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    # Cargar frames agrupados por cámara
    camera_frames = {}
    for item in manifest:
        cid = item.get("camera_id", "cam_01")
        img = cv2.imread(item["file_path"])
        if img is not None:
            camera_frames.setdefault(cid, []).append(img)
            
    all_camera_ids = [f"cam_{i:02d}" for i in range(1, 16)]
    for cid in all_camera_ids:
        if cid not in camera_frames or not camera_frames[cid]:
            camera_frames[cid] = [np.zeros((480, 640, 3), dtype=np.uint8)]
            
    print(f"Cámaras preparadas: {len(all_camera_ids)} fuentes ({', '.join(all_camera_ids)})", flush=True)
    
    # 2. Inicializar SourceManager y registrar 15 fuentes
    source_manager = SourceManager()
    for cid in all_camera_ids:
        desc = CameraDescriptor(
            camera_id=cid,
            host=f"rtsp://186.103.177.83:554/cam/realmonitor?channel={int(cid.split('_')[1])}&subtype=1",
            channel=int(cid.split("_")[1]),
            subtype=1,
            max_width=640,
        )
        source_manager.register_source(desc)
        
    # 3. Construir AdvanceChain completa (Activity -> SelectiveInference -> LocalTracker -> Behavior -> Evidence)
    chain = AdvanceChain.build(config, source_manager)
    chain.register_from_source_manager()
    
    trace = BoundedRuntimeTrace(all_camera_ids)
    
    import psutil
    process = psutil.Process(os.getpid())
    
    start_time = time.time()
    last_report = start_time
    frame_counters = {cid: 0 for cid in all_camera_ids}
    
    timeseries = []
    
    print(f"Iniciando loop de ejecución multicámara...", flush=True)
    
    while (time.time() - start_time) < duration_seconds:
        now = time.time()
        elapsed = now - start_time
        
        # Simular llegada de frames en las 15 cámaras (a ~2 FPS de análisis según perfil BALANCED)
        for cid in all_camera_ids:
            idx = frame_counters[cid]
            frames_list = camera_frames[cid]
            frame = frames_list[idx % len(frames_list)]
            
            result = chain.feed(
                camera_id=cid,
                frame_index=idx,
                fps=2.0,
                frame=frame,
                metadata={"source_state": "OPEN", "resolution": "640x480"}
            )
            
            trace.observe_pipeline_result(cid, idx, result)
            trace.mark_ui_model_received(cid, idx)
            trace.mark_ui_rendered(cid, idx)
            
            frame_counters[cid] += 1
            
        time.sleep(0.4)  # ~2.5 FPS por cámara
        
        if now - last_report >= 60.0:
            cpu = psutil.cpu_percent(interval=None)
            rss = process.memory_info().rss / (1024.0 * 1024.0)
            threads = process.num_threads()
            
            total_frames = sum(frame_counters.values())
            trace_dict = trace.snapshot()
            total_inf = sum(trace_dict[c]["INFERENCE_EXECUTED"] for c in all_camera_ids)
            total_det = sum(trace_dict[c]["DETECTIONS_RETURNED"] for c in all_camera_ids)
            
            timeseries.append({
                "elapsed_s": round(elapsed, 1),
                "rss_mb": round(rss, 2),
                "cpu_percent": round(cpu, 1),
                "threads": threads,
                "total_frames": total_frames,
                "total_inferences": total_inf,
                "total_detections": total_det
            })
            
            print(f"[Elapsed: {elapsed:.1f}s/{duration_seconds}s] Frames: {total_frames} | Inferences: {total_inf} | Detections: {total_det} | RSS: {rss:.1f} MB | CPU: {cpu:.1f}% | Threads: {threads}", flush=True)
            last_report = now
            
    total_time = time.time() - start_time
    print(f"\n--- Multicamera Soak Finalizado con Éxito ({total_time:.1f}s) ---", flush=True)
    
    trace_final = trace.snapshot()
    chain.close()
    
    evidence_dir = Path("evidence/TV-F3-INTEGRATE-OPENVINO-01")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    with open(evidence_dir / "multicamera_soak_trace.json", "w", encoding="utf-8") as f:
        json.dump(trace_final, f, indent=2)
        
    with open(evidence_dir / "multicamera_soak_timeseries.json", "w", encoding="utf-8") as f:
        json.dump(timeseries, f, indent=2)
        
    print(f"Evidencias guardadas en {evidence_dir}", flush=True)

if __name__ == "__main__":
    dur = 1800 if len(sys.argv) < 2 else int(sys.argv[1])
    run_synthetic_multicamera_soak(dur)
