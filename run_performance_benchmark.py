import json
import time
import os
import sys
import psutil
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO

def measure_runtime_performance(runtime_name, model_creator, frames, warmup_runs=20):
    process = psutil.Process(os.getpid())
    print(f"\n==========================================", flush=True)
    print(f"Iniciando Benchmark de Rendimiento: {runtime_name}", flush=True)
    print(f"==========================================", flush=True)
    
    # 1. Startup
    t0 = time.perf_counter()
    model = model_creator()
    startup_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Startup time: {startup_ms:.2f} ms", flush=True)
    
    # 2. Warmup
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    t_w0 = time.perf_counter()
    for _ in range(warmup_runs):
        model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    warmup_total_ms = (time.perf_counter() - t_w0) * 1000.0
    print(f"Warmup ({warmup_runs} iteraciones): {warmup_total_ms:.2f} ms", flush=True)
    
    # 3. Benchmark de Inferencia sobre Dataset de 600 Frames
    latencies_ms = []
    cpu_samples = []
    rss_samples = []
    
    # Reset CPU measurement
    psutil.cpu_percent(interval=None)
    
    t_bench_start = time.perf_counter()
    for idx, frame in enumerate(frames):
        t_start = time.perf_counter()
        res = model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
        lat_ms = (time.perf_counter() - t_start) * 1000.0
        latencies_ms.append(lat_ms)
        
        if (idx + 1) % 10 == 0:
            cpu_samples.append(psutil.cpu_percent(interval=None))
            rss_samples.append(process.memory_info().rss / (1024.0 * 1024.0))
            
        if (idx + 1) % 100 == 0:
            print(f"[{runtime_name}] Procesados {idx + 1}/{len(frames)} frames... (Latencia actual: {lat_ms:.2f} ms)", flush=True)
            
    total_bench_time_s = time.perf_counter() - t_bench_start
    throughput_fps = len(frames) / total_bench_time_s
    
    latencies_np = np.array(latencies_ms)
    cpu_np = np.array(cpu_samples) if cpu_samples else np.array([0.0])
    rss_np = np.array(rss_samples) if rss_samples else np.array([0.0])
    
    p50 = float(np.percentile(latencies_np, 50))
    p95 = float(np.percentile(latencies_np, 95))
    p99 = float(np.percentile(latencies_np, 99))
    avg_lat = float(np.mean(latencies_np))
    std_lat = float(np.std(latencies_np))
    
    avg_cpu = float(np.mean(cpu_np))
    peak_cpu = float(np.max(cpu_np))
    
    avg_rss = float(np.mean(rss_np))
    peak_rss = float(np.max(rss_np))
    
    results = {
        "runtime": runtime_name,
        "startup_ms": startup_ms,
        "warmup_ms": warmup_total_ms,
        "frames_tested": len(frames),
        "total_time_s": total_bench_time_s,
        "throughput_fps": throughput_fps,
        "latency": {
            "avg_ms": avg_lat,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "std_ms": std_lat,
            "min_ms": float(np.min(latencies_np)),
            "max_ms": float(np.max(latencies_np))
        },
        "cpu_percent": {
            "avg": avg_cpu,
            "peak": peak_cpu
        },
        "memory_rss_mb": {
            "avg": avg_rss,
            "peak": peak_rss
        }
    }
    
    print(f"\n--- Resumen {runtime_name} ---", flush=True)
    print(f"Latencia p50: {p50:.2f} ms | p95: {p95:.2f} ms | p99: {p99:.2f} ms | Promedio: {avg_lat:.2f} ms", flush=True)
    print(f"Throughput: {throughput_fps:.2f} FPS", flush=True)
    print(f"CPU Avg: {avg_cpu:.1f}% | Peak: {peak_cpu:.1f}%", flush=True)
    print(f"RAM RSS Avg: {avg_rss:.1f} MB | Peak: {peak_rss:.1f} MB", flush=True)
    
    return results

def main():
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    print(f"Cargando {len(manifest)} frames en memoria RAM para benchmark aislado de latencia pura...", flush=True)
    frames = []
    for item in manifest:
        img = cv2.imread(item["file_path"])
        if img is not None:
            frames.append(img)
    print(f"{len(frames)} frames cargados en RAM. Iniciando comparativa...", flush=True)
    
    benchmark_all = {}
    
    # 1. PyTorch CPU
    pt_results = measure_runtime_performance(
        "PyTorch CPU (Baseline)",
        lambda: YOLO("models/yolo11n.pt", task="detect"),
        frames
    )
    benchmark_all["pytorch"] = pt_results
    
    # 2. ONNX Runtime CPU
    onnx_results = measure_runtime_performance(
        "ONNX Runtime CPU",
        lambda: YOLO("models/yolo11n.onnx", task="detect"),
        frames
    )
    benchmark_all["onnx"] = onnx_results
    
    # 3. OpenVINO Runtime CPU
    ov_results = measure_runtime_performance(
        "OpenVINO CPU",
        lambda: YOLO("models/yolo11n_openvino_model", task="detect"),
        frames
    )
    benchmark_all["openvino"] = ov_results
    
    out_file = Path("benchmark_performance_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_all, f, indent=2)
    print(f"\nResultados completos guardados en {out_file}", flush=True)

if __name__ == "__main__":
    main()
