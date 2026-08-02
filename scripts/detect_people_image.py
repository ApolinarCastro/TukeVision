"""Script de detección manual de personas en una imagen.

Uso:
    python scripts/detect_people_image.py "ruta/imagen.jpg"

Ejecuta detección y muestra resultados sin guardar ni dibujar.
"""

import sys
import time
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import psutil
import os

from detection.person_detector import (
    PersonDetector,
    PersonDetectorError,
    DetectionResult,
)


def get_ram_mb() -> float:
    """Obtiene memoria RAM del proceso actual en MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/detect_people_image.py \"ruta/imagen.jpg\"")
        sys.exit(1)

    image_path = sys.argv[1]

    try:
        # Cargar imagen
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"IMAGE_PATH: {image_path}")
            print("IMAGE_WIDTH: 0")
            print("IMAGE_HEIGHT: 0")
            print("MODEL: yolo11n.pt")
            print("PERSON_COUNT: 0")
            print("DETECTIONS:")
            print("INFERENCE_SECONDS: 0.0000")
            print("FINAL_STATUS: ERROR - No se puede leer la imagen")
            sys.exit(1)

        h, w = frame.shape[:2]

        model_path = Path("models/yolo11n.pt")
        model_name = "yolo11n.pt"

        # Memoria antes
        ram_before = get_ram_mb()

        # Inicialización del detector (carga diferida del modelo)
        init_start = time.perf_counter()
        detector = PersonDetector(
            model_path=str(model_path),
            class_ids=[0],
            confidence_threshold=0.35,
            device="cpu",
            image_size=640
        )
        model_initialization_seconds = time.perf_counter() - init_start

        ram_after_init = get_ram_mb()

        # Primera inferencia (incluye carga real del modelo si es lazy)
        first_inference_start = time.perf_counter()
        result1 = detector.detect(frame)
        first_inference_seconds = time.perf_counter() - first_inference_start

        ram_after_first = get_ram_mb()

        # Segunda inferencia (para distinguir calentamiento)
        second_inference_start = time.perf_counter()
        result2 = detector.detect(frame)
        second_inference_seconds = time.perf_counter() - second_inference_start

        ram_after_second = get_ram_mb()

        # Usar la segunda inferencia como resultado principal (ya calentado)
        result = result2

        # Salida
        print(f"IMAGE_PATH: {image_path}")
        print(f"IMAGE_WIDTH: {w}")
        print(f"IMAGE_HEIGHT: {h}")
        print(f"MODEL: {model_name}")
        print("MODEL_LOADING_MODE: Lazy")
        print(f"PERSON_COUNT: {len(result.detections)}")
        print("DETECTIONS:")

        for i, det in enumerate(result.detections):
            print(f"  PERSON_{i}:")
            print(f"    confidence: {det.confidence:.4f}")
            print(f"    x1: {det.x1}")
            print(f"    y1: {det.y1}")
            print(f"    x2: {det.x2}")
            print(f"    y2: {det.y2}")

        print(f"MODEL_INITIALIZATION_SECONDS: {model_initialization_seconds:.4f}")
        print(f"FIRST_INFERENCE_SECONDS: {first_inference_seconds:.4f}")
        print(f"SECOND_INFERENCE_SECONDS: {second_inference_seconds:.4f}")
        print(f"RAM_BEFORE_MB: {ram_before:.1f}")
        print(f"RAM_AFTER_INIT_MB: {ram_after_init:.1f}")
        print(f"RAM_AFTER_FIRST_INFERENCE_MB: {ram_after_first:.1f}")
        print(f"RAM_AFTER_SECOND_INFERENCE_MB: {ram_after_second:.1f}")
        print("FINAL_STATUS: OK")

        detector.close()

    except PersonDetectorError as e:
        print(f"IMAGE_PATH: {image_path}")
        print("IMAGE_WIDTH: 0")
        print("IMAGE_HEIGHT: 0")
        print("MODEL: yolo11n.pt")
        print("PERSON_COUNT: 0")
        print("DETECTIONS:")
        print("INFERENCE_SECONDS: 0.0000")
        print(f"FINAL_STATUS: ERROR - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"IMAGE_PATH: {image_path}")
        print("IMAGE_WIDTH: 0")
        print("IMAGE_HEIGHT: 0")
        print("MODEL: yolo11n.pt")
        print("PERSON_COUNT: 0")
        print("DETECTIONS:")
        print("INFERENCE_SECONDS: 0.0000")
        print(f"FINAL_STATUS: ERROR - {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()