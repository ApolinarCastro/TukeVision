import json
import time
import os
import sys
import psutil
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO

def compute_iou(box1, box2):
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(0, box1[2] - box1[0]) * max(0, box1[3] - box1[1])
    boxBArea = max(0, box2[2] - box2[0]) * max(0, box2[3] - box2[1])
    
    unionArea = boxAArea + boxBArea - interArea
    if unionArea == 0:
        return 0.0
    return interArea / float(unionArea)

def eval_candidate_frame(pt_boxes, cand_boxes):
    matches = 0
    minor_drift = 0
    mismatches = 0
    missed = 0
    extra = 0
    ious = []
    conf_diffs = []
    
    if len(pt_boxes) == 0 and len(cand_boxes) == 0:
        return 1, 0, 0, 0, 0, ious, conf_diffs
        
    if len(pt_boxes) != len(cand_boxes):
        diff = len(cand_boxes) - len(pt_boxes)
        if diff > 0:
            extra = diff
        else:
            missed = abs(diff)
            
    matched_pt = set()
    for c_box in cand_boxes:
        best_iou = 0.0
        best_pt_idx = -1
        for p_idx, p_box in enumerate(pt_boxes):
            if p_idx in matched_pt:
                continue
            iou = compute_iou(c_box["box"], p_box["box"])
            if iou > best_iou:
                best_iou = iou
                best_pt_idx = p_idx
                
        if best_pt_idx >= 0 and best_iou >= 0.5:
            matched_pt.add(best_pt_idx)
            ious.append(best_iou)
            conf_diffs.append(abs(c_box["conf"] - pt_boxes[best_pt_idx]["conf"]))
            
    if ious:
        mean_iou = np.mean(ious)
        if mean_iou >= 0.90 and len(pt_boxes) == len(cand_boxes):
            matches = 1
        elif mean_iou >= 0.70:
            minor_drift = 1
        else:
            mismatches = 1
    else:
        mismatches = 1
        
    return matches, minor_drift, mismatches, missed, extra, ious, conf_diffs

def main():
    print("Iniciando validacion funcional y benchmark de equivalencia...", flush=True)
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Total frames: {len(manifest)}", flush=True)
    
    pt_model = YOLO("models/yolo11n.pt", task="detect")
    onnx_model = YOLO("models/yolo11n.onnx", task="detect")
    ov_model = YOLO("models/yolo11n_openvino_model", task="detect")
    
    # Warmup
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    pt_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    onnx_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    ov_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    print("Warmup completado.", flush=True)
    
    onnx_stats = {"matches": 0, "minor_drift": 0, "mismatches": 0, "missed": 0, "extra": 0, "ious": [], "confs": []}
    ov_stats = {"matches": 0, "minor_drift": 0, "mismatches": 0, "missed": 0, "extra": 0, "ious": [], "confs": []}
    
    for idx, item in enumerate(manifest):
        frame = cv2.imread(item["file_path"])
        if frame is None:
            continue
            
        r_pt = pt_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        pt_boxes = []
        if r_pt.boxes is not None and len(r_pt.boxes) > 0:
            for b in r_pt.boxes:
                pt_boxes.append({"box": list(map(int, b.xyxy[0].tolist())), "conf": float(b.conf.item()), "cls": int(b.cls.item())})
                
        r_onnx = onnx_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        onnx_boxes = []
        if r_onnx.boxes is not None and len(r_onnx.boxes) > 0:
            for b in r_onnx.boxes:
                onnx_boxes.append({"box": list(map(int, b.xyxy[0].tolist())), "conf": float(b.conf.item()), "cls": int(b.cls.item())})
                
        r_ov = ov_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        ov_boxes = []
        if r_ov.boxes is not None and len(r_ov.boxes) > 0:
            for b in r_ov.boxes:
                ov_boxes.append({"box": list(map(int, b.xyxy[0].tolist())), "conf": float(b.conf.item()), "cls": int(b.cls.item())})
                
        m, md, mm, miss, ext, ious, confs = eval_candidate_frame(pt_boxes, onnx_boxes)
        onnx_stats["matches"] += m
        onnx_stats["minor_drift"] += md
        onnx_stats["mismatches"] += mm
        onnx_stats["missed"] += miss
        onnx_stats["extra"] += ext
        onnx_stats["ious"].extend(ious)
        onnx_stats["confs"].extend(confs)
        
        m, md, mm, miss, ext, ious, confs = eval_candidate_frame(pt_boxes, ov_boxes)
        ov_stats["matches"] += m
        ov_stats["minor_drift"] += md
        ov_stats["mismatches"] += mm
        ov_stats["missed"] += miss
        ov_stats["extra"] += ext
        ov_stats["ious"].extend(ious)
        ov_stats["confs"].extend(confs)
        
        if (idx + 1) % 100 == 0 or (idx + 1) == len(manifest):
            print(f"Progreso: {idx + 1}/{len(manifest)} frames evaluados...", flush=True)
            
    total = len(manifest)
    onnx_match_pct = ((onnx_stats["matches"] + onnx_stats["minor_drift"]) / total) * 100.0
    ov_match_pct = ((ov_stats["matches"] + ov_stats["minor_drift"]) / total) * 100.0
    
    onnx_avg_iou = float(np.mean(onnx_stats["ious"])) if onnx_stats["ious"] else 1.0
    ov_avg_iou = float(np.mean(ov_stats["ious"])) if ov_stats["ious"] else 1.0
    
    onnx_avg_conf_diff = float(np.mean(onnx_stats["confs"])) if onnx_stats["confs"] else 0.0
    ov_avg_conf_diff = float(np.mean(ov_stats["confs"])) if ov_stats["confs"] else 0.0
    
    results = {
        "dataset_frames": total,
        "onnx": {
            "functional_gate": "PASS" if onnx_match_pct >= 95.0 else "FAIL",
            "match_rate_pct": onnx_match_pct,
            "avg_iou": onnx_avg_iou,
            "avg_conf_diff": onnx_avg_conf_diff,
            "exact_matches": onnx_stats["matches"],
            "minor_drift": onnx_stats["minor_drift"],
            "mismatches": onnx_stats["mismatches"],
            "missed_detections": onnx_stats["missed"],
            "extra_detections": onnx_stats["extra"]
        },
        "openvino": {
            "functional_gate": "PASS" if ov_match_pct >= 95.0 else "FAIL",
            "match_rate_pct": ov_match_pct,
            "avg_iou": ov_avg_iou,
            "avg_conf_diff": ov_avg_conf_diff,
            "exact_matches": ov_stats["matches"],
            "minor_drift": ov_stats["minor_drift"],
            "mismatches": ov_stats["mismatches"],
            "missed_detections": ov_stats["missed"],
            "extra_detections": ov_stats["extra"]
        }
    }
    
    with open("functional_equivalence.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("\n--- RESULTADO DE EQUIVALENCIA FUNCIONAL ---", flush=True)
    print(f"ONNX Functional Gate: {results['onnx']['functional_gate']} ({results['onnx']['match_rate_pct']:.2f}% equivalencia, IoU promedio {results['onnx']['avg_iou']:.4f})", flush=True)
    print(f"OpenVINO Functional Gate: {results['openvino']['functional_gate']} ({results['openvino']['match_rate_pct']:.2f}% equivalencia, IoU promedio {results['openvino']['avg_iou']:.4f})", flush=True)

if __name__ == "__main__":
    main()
