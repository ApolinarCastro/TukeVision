"""Script de inspección manual de video.

Uso:
    python scripts/inspect_video.py "ruta/video.mp4"

Muestra metadatos básicos y verifica legibilidad.
"""

import sys
from pathlib import Path

# Añadir src al path para importar el módulo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from capture.video_source import VideoSource, VideoSourceError


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/inspect_video.py \"ruta/video.mp4\"")
        sys.exit(1)

    video_path = sys.argv[1]

    try:
        with VideoSource(video_path) as source:
            metadata = source.open()

            print(f"VIDEO_PATH: {metadata.path}")
            print(f"WIDTH: {metadata.width}")
            print(f"HEIGHT: {metadata.height}")
            print(f"FPS: {metadata.fps:.2f}")
            print(f"TOTAL_FRAMES: {metadata.total_frames}")
            print(f"DURATION_SECONDS: {metadata.duration_seconds:.2f}")

            # Contar fotogramas legibles
            readable = 0
            for _ in source.frames():
                readable += 1

            print(f"READABLE_FRAMES: {readable}")
            print("FINAL_STATUS: OK")

    except VideoSourceError as e:
        print(f"VIDEO_PATH: {video_path}")
        print("WIDTH: 0")
        print("HEIGHT: 0")
        print("FPS: 0.00")
        print("TOTAL_FRAMES: 0")
        print("DURATION_SECONDS: 0.00")
        print("READABLE_FRAMES: 0")
        print(f"FINAL_STATUS: ERROR - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()