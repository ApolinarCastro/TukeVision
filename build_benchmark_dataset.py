import json
import hashlib
from pathlib import Path
import cv2

def build_benchmark_dataset(target_count=600):
    clips_dir = Path("evidence")
    mp4_files = sorted(list(clips_dir.glob("**/clips/*/*.mp4")))
    print(f"Found {len(mp4_files)} total MP4 clips in evidence.")
    
    # We will sample frames across multiple cameras
    dataset_dir = Path("benchmark_dataset")
    dataset_dir.mkdir(exist_ok=True)
    frames_dir = dataset_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    
    manifest = []
    frames_extracted = 0
    
    # Select clips across various cameras
    cams = {}
    for p in mp4_files:
        cam_id = p.parent.name
        cams.setdefault(cam_id, []).append(p)
        
    print(f"Cameras with clips: {list(cams.keys())}")
    
    for cam_id, clip_list in cams.items():
        if frames_extracted >= target_count:
            break
        for clip_path in clip_list[:10]: # take up to 10 clips per camera
            if frames_extracted >= target_count:
                break
            cap = cv2.VideoCapture(str(clip_path))
            if not cap.isOpened():
                continue
            
            frame_idx = 0
            while cap.isOpened() and frames_extracted < target_count:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sample every 5th frame to get diversity
                if frame_idx % 5 == 0:
                    frame_name = f"frame_{frames_extracted:05d}_{cam_id}.jpg"
                    frame_path = frames_dir / frame_name
                    cv2.imwrite(str(frame_path), frame)
                    
                    with open(frame_path, "rb") as f:
                        sha = hashlib.sha256(f.read()).hexdigest()
                    
                    manifest.append({
                        "frame_id": f"frame_{frames_extracted:05d}",
                        "file_name": frame_name,
                        "file_path": str(frame_path.relative_to(Path("."))),
                        "camera_id": cam_id,
                        "source_clip": str(clip_path.relative_to(Path("."))),
                        "sha256": sha,
                        "height": frame.shape[0],
                        "width": frame.shape[1]
                    })
                    frames_extracted += 1
                frame_idx += 1
            cap.release()
            
    manifest_path = dataset_dir / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Dataset build complete: {len(manifest)} frames extracted and indexed in {manifest_path}")

if __name__ == "__main__":
    build_benchmark_dataset(600)
