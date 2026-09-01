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

def run_functional_validation(max_frames=600):
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    frames_to_test = manifest[:max_frames]
    print(f"Loaded {len(frames_to_test)} frames for functional validation...")
    
    pt_model = YOLO("models/yolo11n.pt", task="detect")
    onnx_model = YOLO("models/yolo11n.onnx", task="detect")
    ov_model = YOLO("models/yolo11n_openvino_model", task="detect")
    
    validation_results = {
        "total_frames": len(frames_to_test),
        "onnx": {
            "matches": 0,
            "minor_drift": 0,
            "mismatches": 0,
            "iou_scores": [],
            "conf_diffs": [],
            "missed_detections": 0,
            "extra_detections": 0
        },
        "openvino": {
            "matches": 0,
            "minor_drift": 0,
            "mismatches": 0,
            "iou_scores": [],
            "conf_diffs": [],
            "missed_detections": 0,
            "extra_detections": 0
        }
    }
    
    # Warmup
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    pt_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    onnx_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    ov_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    
    for idx, item in enumerate(frames_to_test):
        frame = cv2.imread(item["file_path"])
        if frame is None:
            continue
            
        pt_res = pt_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        pt_boxes = []
        if pt_res.boxes is not None and len(pt_res.boxes) > 0:
            for b in pt_res.boxes:
                pt_boxes.append({
                    "box": list(map(int, b.xyxy[0].tolist())),
                    "conf": float(b.conf.item()),
                    "cls": int(b.cls.item())
                })
                
        onnx_res = onnx_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        onnx_boxes = []
        if onnx_res.boxes is not None and len(onnx_res.boxes) > 0:
            for b in onnx_res.boxes:
                onnx_boxes.append({
                    "box": list(map(int, b.xyxy[0].tolist())),
                    "conf": float(b.conf.item()),
                    "cls": int(b.cls.item())
                })
                
        ov_res = ov_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)[0]
        ov_boxes = []
        if ov_res.boxes is not None and len(ov_res.boxes) > 0:
            for b in ov_res.boxes:
                ov_boxes.append({
                    "box": list(map(int, b.xyxy[0].tolist())),
                    "conf": float(b.conf.item()),
                    "cls": int(b.cls.item())
                })
                
        _eval_candidate(pt_boxes, onnx_boxes, validation_results["onnx"])
        _eval_candidate(pt_boxes, ov_boxes, validation_results["openvino"])
        
        if (idx + 1) % 50 == 0:
            print(f"Validated {idx + 1}/{len(frames_to_test)} frames...", flush=True)
            
    for cand in ["onnx", "openvino"]:
        res = validation_results[cand]
        avg_iou = float(np.mean(res["iou_scores"])) if res["iou_scores"] else 1.0
        avg_conf_diff = float(np.mean(res["conf_diffs"])) if res["conf_diffs"] else 0.0
        match_rate = (res["matches"] + res["minor_drift"]) / float(validation_results["total_frames"]) * 100.0
        res["avg_iou"] = avg_iou
        res["avg_conf_diff"] = avg_conf_diff
        res["match_rate_pct"] = match_rate
        del res["iou_scores"]
        del res["conf_diffs"]
        
    out_path = Path("functional_validation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2)
        
    print("\n=== FUNCTIONAL VALIDATION COMPLETE ===")
    print(f"ONNX Match Rate: {validation_results['onnx']['match_rate_pct']:.2f}% | Avg IoU: {validation_results['onnx']['avg_iou']:.4f} | Avg Conf Diff: {validation_results['onnx']['avg_conf_diff']:.4f} | Misses: {validation_results['onnx']['missed_detections']} | Extras: {validation_results['onnx']['extra_detections']}")
    print(f"OpenVINO Match Rate: {validation_results['openvino']['match_rate_pct']:.2f}% | Avg IoU: {validation_results['openvino']['avg_iou']:.4f} | Avg Conf Diff: {validation_results['openvino']['avg_conf_diff']:.4f} | Misses: {validation_results['openvino']['missed_detections']} | Extras: {validation_results['openvino']['extra_detections']}")

def _eval_candidate(pt_boxes, cand_boxes, cand_stats):
    if len(pt_boxes) == 0 and len(cand_boxes) == 0:
        cand_stats["matches"] += 1
        return
        
    if len(pt_boxes) != len(cand_boxes):
        diff = len(cand_boxes) - len(pt_boxes)
        if diff > 0:
            cand_stats["extra_detections"] += diff
        else:
            cand_stats["missed_detections"] += abs(diff)
            
    matched_pt = set()
    frame_ious = []
    frame_conf_diffs = []
    
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
            frame_ious.append(best_iou)
            frame_conf_diffs.append(abs(c_box["conf"] - pt_boxes[best_pt_idx]["conf"]))
            
    if frame_ious:
        mean_iou = np.mean(frame_ious)
        cand_stats["iou_scores"].extend(frame_ious)
        cand_stats["conf_diffs"].extend(frame_conf_diffs)
        if mean_iou >= 0.90 and len(pt_boxes) == len(cand_boxes):
            cand_stats["matches"] += 1
        elif mean_iou >= 0.70:
            cand_stats["minor_drift"] += 1
        else:
            cand_stats["mismatches"] += 1
    else:
        cand_stats["mismatches"] += 1

if __name__ == "__main__":
    run_functional_validation(600)
