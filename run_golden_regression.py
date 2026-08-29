import json
import time
import numpy as np
import cv2
from pathlib import Path
from src.detection.person_detector import PersonDetector

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

def run_golden_frame_regression(num_frames=100):
    with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    subset = manifest[:num_frames]
    print(f"Iniciando Golden Frame Regression sobre {len(subset)} frames...", flush=True)
    
    pt_detector = PersonDetector("models/yolo11n.pt", runtime="pytorch", confidence_threshold=0.35)
    ov_detector = PersonDetector("models/yolo11n.pt", runtime="openvino", confidence_threshold=0.35)
    
    # Warmup
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    pt_detector.detect(dummy)
    ov_detector.detect(dummy)
    
    matches = 0
    minor_drift = 0
    mismatches = 0
    missed = 0
    extra = 0
    ious = []
    conf_diffs = []
    
    for idx, item in enumerate(subset):
        frame = cv2.imread(item["file_path"])
        if frame is None:
            continue
            
        r_pt = pt_detector.detect(frame)
        r_ov = ov_detector.detect(frame)
        
        pt_boxes = [{"box": [d.x1, d.y1, d.x2, d.y2], "conf": d.confidence, "cls": d.class_id} for d in r_pt.detections]
        ov_boxes = [{"box": [d.x1, d.y1, d.x2, d.y2], "conf": d.confidence, "cls": d.class_id} for d in r_ov.detections]
        
        if len(pt_boxes) == 0 and len(ov_boxes) == 0:
            matches += 1
            continue
            
        if len(pt_boxes) != len(ov_boxes):
            diff = len(ov_boxes) - len(pt_boxes)
            if diff > 0:
                extra += diff
            else:
                missed += abs(diff)
                
        matched_pt = set()
        frame_ious = []
        frame_conf_diffs = []
        for o_box in ov_boxes:
            best_iou = 0.0
            best_pt_idx = -1
            for p_idx, p_box in enumerate(pt_boxes):
                if p_idx in matched_pt:
                    continue
                iou = compute_iou(o_box["box"], p_box["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_pt_idx = p_idx
                    
            if best_pt_idx >= 0 and best_iou >= 0.5:
                matched_pt.add(best_pt_idx)
                frame_ious.append(best_iou)
                frame_conf_diffs.append(abs(o_box["conf"] - pt_boxes[best_pt_idx]["conf"]))
                
        if frame_ious:
            m_iou = np.mean(frame_ious)
            ious.extend(frame_ious)
            conf_diffs.extend(frame_conf_diffs)
            if m_iou >= 0.90 and len(pt_boxes) == len(ov_boxes):
                matches += 1
            elif m_iou >= 0.70:
                minor_drift += 1
            else:
                mismatches += 1
        else:
            mismatches += 1
            
    match_pct = ((matches + minor_drift) / len(subset)) * 100.0
    avg_iou = float(np.mean(ious)) if ious else 1.0
    avg_conf_diff = float(np.mean(conf_diffs)) if conf_diffs else 0.0
    
    gate = "PASS" if match_pct >= 95.0 else "FAIL"
    
    results = {
        "golden_frames_tested": len(subset),
        "functional_equivalence_gate": gate,
        "match_rate_pct": match_pct,
        "avg_iou": avg_iou,
        "avg_conf_diff": avg_conf_diff,
        "exact_matches": matches,
        "minor_drift": minor_drift,
        "mismatches": mismatches,
        "missed_detections": missed,
        "extra_detections": extra
    }
    
    with open("golden_frame_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\n--- GOLDEN FRAME REGRESSION ({len(subset)} frames) ---")
    print(f"Gate: {gate} | Match Rate: {match_pct:.2f}% | Avg IoU: {avg_iou:.4f} | Avg Conf Diff: {avg_conf_diff:.4f} | Misses: {missed} | Extras: {extra}")
    
    pt_detector.close()
    ov_detector.close()
    return results

if __name__ == "__main__":
    run_golden_frame_regression(100)
