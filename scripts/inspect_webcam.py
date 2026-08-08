"""Script de inspección manual de webcam.

Uso:
    python scripts/inspect_webcam.py [camera_index]

Muestra metadatos básicos y verifica legibilidad de una webcam local.
No es una certificación de negocio.
"""

import sys
from pathlib import Path

# Añadir el proyecto al path para importar los módulos
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from src.capture.live_sources import WebcamSource, WebcamUnavailableError
from src.capture.video_source import VideoSourceError


def main() -> None:
    camera_index = 0
    if len(sys.argv) > 1:
        camera_index = int(sys.argv[1])

    try:
        with WebcamSource(camera_index=camera_index, backend=cv2.CAP_DSHOW) as source:
            metadata = source.open()

            print(f"WEBCAM_INDEX: {camera_index}")
            print(f"SOURCE_TYPE: {metadata.source_type}")
            print(f"WIDTH: {metadata.width}")
            print(f"HEIGHT: {metadata.height}")
            print(f"FPS: {metadata.fps:.2f}" if metadata.fps > 0 else "FPS: UNKNOWN")

            # Leer un puñado de fotogramas para verificar legibilidad
            readable = 0
            for _ in source.frames():
                readable += 1
                if readable >= 10:
                    break

            print(f"READABLE_FRAMES: {readable}")
            print("FINAL_STATUS: OK")

    except WebcamUnavailableError as e:
        print(f"WEBCAM_INDEX: {camera_index}")
        print(f"FINAL_STATUS: WEBCAM_NOT_AVAILABLE - {e}")
        sys.exit(1)
    except VideoSourceError as e:
        print(f"WEBCAM_INDEX: {camera_index}")
        print(f"FINAL_STATUS: ERROR - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
