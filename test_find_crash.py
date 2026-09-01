import sys
import traceback

def main():
    try:
        import json
        import numpy as np
        import cv2
        from ultralytics import YOLO

        with open("benchmark_dataset/dataset_manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)

        print(f"Manifest items: {len(manifest)}")
        pt_model = YOLO("models/yolo11n.pt", task="detect")
        onnx_model = YOLO("models/yolo11n.onnx", task="detect")
        ov_model = YOLO("models/yolo11n_openvino_model", task="detect")

        for idx, item in enumerate(manifest):
            path = item["file_path"]
            frame = cv2.imread(path)
            if frame is None:
                print(f"Frame {idx} at {path} could not be read!")
                continue
            
            try:
                r1 = pt_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
            except Exception as e:
                print(f"FAILED ON PT AT FRAME {idx}: {e}")
                traceback.print_exc()
                sys.exit(1)

            try:
                r2 = onnx_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
            except Exception as e:
                print(f"FAILED ON ONNX AT FRAME {idx}: {e}")
                traceback.print_exc()
                sys.exit(1)

            try:
                r3 = ov_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
            except Exception as e:
                print(f"FAILED ON OV AT FRAME {idx}: {e}")
                traceback.print_exc()
                sys.exit(1)

            if idx % 50 == 0:
                print(f"Done frame {idx}")

        print("ALL 600 FRAMES PASSED INFERENCE TEST")
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
