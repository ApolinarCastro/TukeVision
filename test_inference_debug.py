import traceback
import sys

try:
    import json
    import numpy as np
    import cv2
    from ultralytics import YOLO

    pt_model = YOLO("models/yolo11n.pt", task="detect")
    onnx_model = YOLO("models/yolo11n.onnx", task="detect")
    ov_model = YOLO("models/yolo11n_openvino_model", task="detect")

    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    print("Testing dummy inference...")
    res_pt = pt_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    print("PT OK")
    res_onnx = onnx_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    print("ONNX OK")
    res_ov = ov_model.predict(source=dummy, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
    print("OV OK")

    with open("benchmark_dataset/dataset_manifest.json", "r") as f:
        manifest = json.load(f)
    print("Testing first 5 frames...")
    for idx, item in enumerate(manifest[:5]):
        frame = cv2.imread(item["file_path"])
        p = pt_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
        o = onnx_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
        v = ov_model.predict(source=frame, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
        print(f"Frame {idx} OK")
except Exception as e:
    traceback.print_exc()
