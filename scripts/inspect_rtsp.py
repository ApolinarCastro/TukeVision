"""Script de inspección manual de una fuente RTSP.

Uso:
    python scripts/inspect_rtsp.py "rtsp://..."

La URL se recibe como argumento o mediante la variable de entorno
TUKEVISION_RTSP_URL. Nunca se almacena en código ni en configuración.

Solo debe usarse con fuentes autorizadas, controladas y conocidas.
Resultado únicamente técnico (TECHNICAL_STREAM_VALIDATION).
"""

import os
import sys
from pathlib import Path

# Añadir el proyecto al path para importar los módulos
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.capture.live_sources import RTSPSource
from src.capture.video_source import VideoSourceError


def main() -> None:
    rtsp_url = os.environ.get("TUKEVISION_RTSP_URL")
    if len(sys.argv) > 1:
        rtsp_url = sys.argv[1]

    if not rtsp_url:
        print("Uso: python scripts/inspect_rtsp.py \"rtsp://...\"")
        print("     o definir la variable de entorno TUKEVISION_RTSP_URL")
        sys.exit(1)

    try:
        with RTSPSource(rtsp_url=rtsp_url) as source:
            metadata = source.open()

            print(f"SOURCE_TYPE: {metadata.source_type}")
            print(f"WIDTH: {metadata.width}")
            print(f"HEIGHT: {metadata.height}")
            print(f"FPS: {metadata.fps:.2f}" if metadata.fps > 0 else "FPS: UNKNOWN")

            readable = 0
            for _ in source.frames():
                readable += 1
                if readable >= 10:
                    break

            print(f"READABLE_FRAMES: {readable}")
            print("FINAL_STATUS: TECHNICAL_STREAM_VALIDATION")

    except VideoSourceError as e:
        print(f"FINAL_STATUS: ERROR - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
