import json
import time
import os
import sys
import psutil
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO

def run_stability_benchmark(runtime_name, model_creator, frames, duration_seconds=600):
    process = psutil.Process(os.getpid())
    print(f"\n=======================================================", flush=True)
    print(f"Iniciando Prueba de Estabilidad Sostenida (10 Min): {runtime_name}", flush=True)
    print(f"=======================================================", flush=True)
    
    model = model_creator()
    
    t_start = time.perf_counter()
    iterations = 0
    errors = 0
    num_frames = len(frames)
    
    latencies = []
    cpu_samples = []
    rss_samples = []
    threads_samples = []
    
    psutil.cpu_percent(interval=None)
    last_report = t_start
    
    while (time.perf_counter() - t_start) < duration_seconds:
        frame = frames[iterations % num_frames]
        t_f0 = time.perf_counter()
        try:
            res = model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
            lat = (time.perf_counter() - t_f0) * 1000.0
            latencies.append(lat)
        except Exception as e:
            errors += 1
            print(f"[{runtime_name}] ERROR en iteracion {iterations}: {e}", flush=True)
            
        iterations += 1
        
        now = time.perf_counter()
        if now - last_report >= 60.0:
            elapsed = now - t_start
            current_cpu = psutil.cpu_percent(interval=None)
            current_rss = process.memory_info().rss / (1024.0 * 1024.0)
            current_threads = process.num_threads()
            
            cpu_samples.append(current_cpu)
            rss_samples.append(current_rss)
            threads_samples.append(current_threads)
            
            p50_curr = float(np.percentile(latencies[-500:], 50)) if latencies else 0.0
            print(f"[{runtime_name}] Elapsed: {elapsed:.1f}s / {duration_seconds}s | Iteraciones: {iterations} | Latencia p50 (reciente): {p50_curr:.2f} ms | RSS: {current_rss:.1f} MB | CPU: {current_cpu:.1f}% | Errores: {errors}", flush=True)
            last_report = now
            
    total_time = time.perf_counter() - t_start
    fps = iterations / total_time
    
    lat_np = np.array(latencies)
    p50 = float(np.percentile(lat_np, 50))
    p95 = float(np.percentile(lat_np, 95))
    p99 = float(np.percentile(lat_np, 99))
    avg_lat = float(np.mean(lat_np))
    
    rss_start = rss_samples[0] if rss_samples else (process.memory_info().rss / (1024.0 * 1024.0))
    rss_end = rss_samples[-1] if rss_samples else rss_start
    rss_growth_mb = rss_end - rss_start
    
    stability_gate = "PASS" if errors == 0 and rss_growth_mb < 200.0 else "FAIL"
    
    results = {
        "runtime": runtime_name,
        "duration_seconds": total_time,
        "total_inferences": iterations,
        "total_errors": errors,
        "stability_gate": stability_gate,
        "throughput_fps": fps,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "latency_avg_ms": avg_lat,
        "rss_start_mb": rss_start,
        "rss_end_mb": rss_end,
        "rss_growth_mb": rss_growth_mb,
        "rss_peak_mb": float(np.max(rss_samples)) if rss_samples else rss_end,
        "cpu_avg_percent": float(np.mean(cpu_samples)) if cpu_samples else 0.0,
        "threads_avg": float(np.mean(threads_samples)) if threads_samples else 0.0
    }
    
    print(f"\n--- Resumen Estabilidad 10 min: {runtime_name} ---", flush=True)
    print(f"Gate: {stability_gate} | Total Inferencias: {iterations} | Errores: {errors}", flush=True)
    print(f"Throughput promedio: {fps:.2f} FPS | Latencia p50: {p50:.2f} ms", flush=True)
    print(f"Crecimiento RSS: {rss_growth_mb:.2f} MB (Inicio: {rss_start:.1f} MB -> Fin: {rss_end:.1f} MB)", flush=True)
    
    return results

def main():
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    print(f"Cargando dataset de {len(manifest)} frames para prueba sostenida...", flush=True)
    frames = []
    for item in manifest:
        img = cv2.imread(item["file_path"])
        if img is not None:
            frames.append(img)
            
    stability_all = {}
    
    # 1. PyTorch CPU
    pt_res = run_stability_benchmark(
        "PyTorch CPU (Baseline)",
        lambda: YOLO("models/yolo11n.pt", task="detect"),
        frames,
        duration_seconds=600
    )
    stability_all["pytorch"] = pt_res
    
    # 2. ONNX Runtime CPU
    onnx_res = run_stability_benchmark(
        "ONNX Runtime CPU",
        lambda: YOLO("models/yolo11n.onnx", task="detect"),
        frames,
        duration_seconds=600
    )
    stability_all["onnx"] = onnx_res
    
    # 3. OpenVINO Runtime CPU
    ov_res = run_stability_benchmark(
        "OpenVINO CPU",
        lambda: YOLO("models/yolo11n_openvino_model", task="detect"),
        frames,
        duration_seconds=600
    )
    stability_all["openvino"] = ov_res
    
    out_file = Path("benchmark_stability_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(stability_all, f, indent=2)
    print(f"\nResultados de estabilidad de 10 minutos guardados en {out_file}", flush=True)

if __name__ == "__main__":
    main()
