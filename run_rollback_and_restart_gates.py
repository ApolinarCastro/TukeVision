import json
import time
import os
import sys
import numpy as np
import cv2
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from src.capture.source_manager import SourceManager, CameraDescriptor
from src.app.advance_chain import AdvanceChain
from src.observability.runtime_trace import BoundedRuntimeTrace

def test_rollback_and_restart():
    evidence_dir = Path("evidence/TV-F3-INTEGRATE-OPENVINO-01")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    with open("config/default.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    all_camera_ids = [f"cam_{i:02d}" for i in range(1, 16)]
    
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # -------------------------------------------------------------
    # 1. GATE F: ROLLBACK TEST (INFERENCE_RUNTIME=pytorch) por 300s
    # -------------------------------------------------------------
    print("\n=======================================================", flush=True)
    print("EJECUTANDO GATE F: PRUEBA DE ROLLBACK A PYTORCH (300s)", flush=True)
    print("=======================================================", flush=True)
    
    config["inference"]["runtime"] = "pytorch"
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
        
    chain_pt = AdvanceChain.build(config, source_manager)
    chain_pt.register_from_source_manager()
    
    t0 = time.time()
    errors_rollback = 0
    inferences_rollback = 0
    while time.time() - t0 < 300:
        for cid in all_camera_ids:
            try:
                res = chain_pt.feed(cid, frame_index=1, fps=2.0, frame=dummy_frame, metadata={"source_state": "OPEN"})
                inferences_rollback += 1
            except Exception as e:
                errors_rollback += 1
        time.sleep(0.5)
        
    chain_pt.close()
    
    rollback_results = {
        "gate": "PASS" if errors_rollback == 0 and inferences_rollback > 0 else "FAIL",
        "runtime_tested": "pytorch",
        "duration_seconds": round(time.time() - t0, 1),
        "total_operations": inferences_rollback,
        "errors": errors_rollback
    }
    
    with open(evidence_dir / "rollback_test.json", "w", encoding="utf-8") as f:
        json.dump(rollback_results, f, indent=2)
    print(f"Rollback Gate: {rollback_results['gate']} ({inferences_rollback} operaciones, {errors_rollback} errores)", flush=True)
    
    # -------------------------------------------------------------
    # 2. GATE G: RESTART STABILITY TEST (INFERENCE_RUNTIME=openvino) por 600s
    # -------------------------------------------------------------
    print("\n=======================================================", flush=True)
    print("EJECUTANDO GATE G: REINICIO LIMPIO Y ESTABILIDAD OPENVINO (600s)", flush=True)
    print("=======================================================", flush=True)
    
    config["inference"]["runtime"] = "openvino"
    source_manager_ov = SourceManager()
    for cid in all_camera_ids:
        desc = CameraDescriptor(
            camera_id=cid,
            host=f"rtsp://186.103.177.83:554/cam/realmonitor?channel={int(cid.split('_')[1])}&subtype=1",
            channel=int(cid.split("_")[1]),
            subtype=1,
            max_width=640,
        )
        source_manager_ov.register_source(desc)
        
    chain_ov = AdvanceChain.build(config, source_manager_ov)
    chain_ov.register_from_source_manager()
    
    t0_ov = time.time()
    errors_restart = 0
    inferences_restart = 0
    while time.time() - t0_ov < 600:
        for cid in all_camera_ids:
            try:
                res = chain_ov.feed(cid, frame_index=1, fps=2.0, frame=dummy_frame, metadata={"source_state": "OPEN"})
                inferences_restart += 1
            except Exception as e:
                errors_restart += 1
        time.sleep(0.5)
        
    chain_ov.close()
    
    restart_results = {
        "gate": "PASS" if errors_restart == 0 and inferences_restart > 0 else "FAIL",
        "runtime_tested": "openvino",
        "duration_seconds": round(time.time() - t0_ov, 1),
        "total_operations": inferences_restart,
        "errors": errors_restart
    }
    
    with open(evidence_dir / "restart_test.json", "w", encoding="utf-8") as f:
        json.dump(restart_results, f, indent=2)
    print(f"Restart Stability Gate: {restart_results['gate']} ({inferences_restart} operaciones, {errors_restart} errores)", flush=True)

if __name__ == "__main__":
    test_rollback_and_restart()
