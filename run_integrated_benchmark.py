import json
import time
import os
import psutil
import numpy as np
import cv2
from pathlib import Path
from src.detection.person_detector import PersonDetector

def run_integrated_benchmark():
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    frames = [cv2.imread(item["file_path"]) for item in manifest if cv2.imread(item["file_path"]) is not None]
    print(f"Cargados {len(frames)} frames en memoria para Integrated Benchmark...", flush=True)
    
    process = psutil.Process(os.getpid())
    results = {}
    
    for rt_name in ["pytorch", "openvino"]:
        print(f"\n--- Probando PersonDetector integrado con runtime: {rt_name} ---", flush=True)
        detector = PersonDetector("models/yolo11n.pt", runtime=rt_name, confidence_threshold=0.35)
        
        # Warmup
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(10):
            detector.detect(dummy)
            
        latencies = []
        cpu_samples = []
        rss_samples = []
        psutil.cpu_percent(interval=None)
        
        t0 = time.perf_counter()
        for idx, frame in enumerate(frames):
            t_f0 = time.perf_counter()
            r = detector.detect(frame)
            lat = (time.perf_counter() - t_f0) * 1000.0
            latencies.append(lat)
            
            if (idx + 1) % 10 == 0:
                cpu_samples.append(psutil.cpu_percent(interval=None))
                rss_samples.append(process.memory_info().rss / (1024.0 * 1024.0))
                
        total_time = time.perf_counter() - t0
        fps = len(frames) / total_time
        
        lat_np = np.array(latencies)
        p50 = float(np.percentile(lat_np, 50))
        p95 = float(np.percentile(lat_np, 95))
        p99 = float(np.percentile(lat_np, 99))
        avg_lat = float(np.mean(lat_np))
        
        avg_cpu = float(np.mean(cpu_np)) if (cpu_np := np.array(cpu_samples)).size > 0 else 0.0
        avg_rss = float(np.mean(rss_np)) if (rss_np := np.array(rss_samples)).size > 0 else 0.0
        
        results[rt_name] = {
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "avg_ms": avg_lat,
            "fps": fps,
            "cpu_avg": avg_cpu,
            "rss_avg_mb": avg_rss
        }
        
        print(f"[{rt_name}] p50: {p50:.2f} ms | p95: {p95:.2f} ms | Throughput: {fps:.2f} FPS | CPU: {avg_cpu:.1f}% | RSS: {avg_rss:.1f} MB", flush=True)
        detector.close()
        
    gate = "PASS" if results["openvino"]["p50_ms"] < (0.65 * results["pytorch"]["p50_ms"]) else "FAIL"
    results["integrated_performance_gate"] = gate
    
    with open("integrated_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\n--- INTEGRATED BENCHMARK GATE: {gate} ---")
    print(f"PyTorch p50: {results['pytorch']['p50_ms']:.2f} ms vs OpenVINO p50: {results['openvino']['p50_ms']:.2f} ms (-{((1.0 - results['openvino']['p50_ms']/results['pytorch']['p50_ms'])*100.0):.1f}%)")

if __name__ == "__main__":
    run_integrated_benchmark()
