import sys
import psutil
import torch
import cv2
import ultralytics

print(f"Python: {sys.version.split()[0]}")
print(f"PyTorch: {torch.__version__}")
print(f"Ultralytics: {ultralytics.__version__}")
print(f"OpenCV: {cv2.__version__}")
print(f"CPU Physical: {psutil.cpu_count(logical=False)}, Logical: {psutil.cpu_count(logical=True)}")
print(f"RAM Total GB: {round(psutil.virtual_memory().total / (1024**3), 2)}")

try:
    import onnxruntime
    print(f"ONNX Runtime: {onnxruntime.__version__}, Providers: {onnxruntime.get_available_providers()}")
except ImportError:
    print("ONNX Runtime: NOT_INSTALLED")

try:
    import openvino
    print(f"OpenVINO: {openvino.__version__}")
except ImportError:
    print("OpenVINO: NOT_INSTALLED")
