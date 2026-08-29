import json
import time
import hashlib
from pathlib import Path
from ultralytics import YOLO

def export_models():
    model_path = Path("models/yolo11n.pt")
    assert model_path.exists(), f"Model {model_path} not found"
    
    with open(model_path, "rb") as f:
        pt_sha = hashlib.sha256(f.read()).hexdigest()
    
    print(f"Loading YOLO11n from {model_path} (SHA: {pt_sha})...")
    model = YOLO(str(model_path))
    
    manifest = {
        "source_model": str(model_path),
        "source_sha256": pt_sha,
        "source_size_bytes": model_path.stat().st_size,
        "exports": {}
    }
    
    # 1. Export to ONNX
    print("\n--- Exporting to ONNX ---")
    t0 = time.perf_counter()
    onnx_path_str = model.export(
        format="onnx",
        imgsz=640,
        dynamic=False,
        simplify=True,
        opset=17
    )
    onnx_time = time.perf_counter() - t0
    onnx_path = Path(onnx_path_str)
    with open(onnx_path, "rb") as f:
        onnx_sha = hashlib.sha256(f.read()).hexdigest()
    
    print(f"ONNX export complete in {onnx_time:.2f}s: {onnx_path} (Size: {onnx_path.stat().st_size} bytes, SHA: {onnx_sha})")
    manifest["exports"]["onnx"] = {
        "path": str(onnx_path),
        "sha256": onnx_sha,
        "size_bytes": onnx_path.stat().st_size,
        "export_time_s": onnx_time,
        "format": "onnx",
        "opset": 17,
        "imgsz": 640,
        "dynamic": False,
        "simplify": True
    }
    
    # 2. Export to OpenVINO
    print("\n--- Exporting to OpenVINO ---")
    t0 = time.perf_counter()
    openvino_path_str = model.export(
        format="openvino",
        imgsz=640,
        half=False
    )
    ov_time = time.perf_counter() - t0
    openvino_path = Path(openvino_path_str)
    
    # Openvino exports a directory with .xml and .bin
    ov_files = {}
    if openvino_path.is_dir():
        for p in openvino_path.glob("*"):
            if p.is_file():
                with open(p, "rb") as f:
                    ov_files[p.name] = {
                        "size_bytes": p.stat().st_size,
                        "sha256": hashlib.sha256(f.read()).hexdigest()
                    }
    
    print(f"OpenVINO export complete in {ov_time:.2f}s: {openvino_path} (Files: {list(ov_files.keys())})")
    manifest["exports"]["openvino"] = {
        "path": str(openvino_path),
        "files": ov_files,
        "export_time_s": ov_time,
        "format": "openvino",
        "imgsz": 640,
        "half": False
    }
    
    out_manifest = Path("models/export_manifest.json")
    with open(out_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved to {out_manifest}")

if __name__ == "__main__":
    export_models()
