import sys
print("Step 1: start", flush=True)

import cv2
print("Step 2: cv2 imported", flush=True)

from ultralytics import YOLO
print("Step 3: YOLO imported", flush=True)

pt_model = YOLO("models/yolo11n.pt", task="detect")
print("Step 4: PT loaded", flush=True)

onnx_model = YOLO("models/yolo11n.onnx", task="detect")
print("Step 5: ONNX loaded", flush=True)

ov_model = YOLO("models/yolo11n_openvino_model", task="detect")
print("Step 6: OV loaded", flush=True)

img = cv2.imread("benchmark_dataset/frames/frame_00000_cam_01.jpg")
print("Step 7: Img read", flush=True)

print("Step 8: Testing PT predict", flush=True)
r_pt = pt_model.predict(source=img, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
print("Step 9: PT predict done", flush=True)

print("Step 10: Testing ONNX predict", flush=True)
r_onnx = onnx_model.predict(source=img, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
print("Step 11: ONNX predict done", flush=True)

print("Step 12: Testing OV predict", flush=True)
r_ov = ov_model.predict(source=img, imgsz=640, classes=[0], conf=0.35, device="cpu", verbose=False)
print("Step 13: OV predict done", flush=True)
