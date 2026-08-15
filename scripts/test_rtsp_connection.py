"""Prueba de conexión RTSP autorizada (LOOP-0012A).

Ejecuta el diagnóstico de conexión RTSP sobre una URL proporcionada
explícitamente por un operador autorizado. No descubre dispositivos, no
escanea red, no prueba credenciales y no ejecuta el pipeline de negocio.

Seguridad:
- La contraseña se solicita de forma interactiva y segura (getpass);
  nunca se imprime ni se persiste.
- La URL con credenciales solo existe en memoria durante la ejecución.
- La salida del diagnóstico no incluye credenciales ni la URL original.

Uso:
    python scripts/test_rtsp_connection.py "rtsp://usuario:clave@host/path"
    python scripts/test_rtsp_connection.py --host "rtsp://192.168.1.50:554/stream" --username admin --channel 5

Opciones:
    --host HOST          URL base RTSP sin credenciales.
    --username USER      Usuario; la contraseña se pide de forma segura.
    --channel N          Canal RTSP (1-16, por defecto 1).
    --timeout SEC        Límite total de la prueba en segundos (15 por defecto).
    --max-frames N       Máximo de fotogramas a leer (30 por defecto).
"""

import argparse
import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.capture.rtsp_url import build_rtsp_url
from src.diagnostics.rtsp_connection_test import (
    RTSPConnectionTest,
    RTSPFrameState,
    summarize_result,
)
from src.observability.logging_setup import redact_rtsp_url


def _with_credentials(host: str, username: str, password: str, channel: int = 1) -> str:
    """Inserta credenciales en una URL RTSP base sin exponer la contraseña.

    Mantiene compatibilidad con los tests de seguridad existentes
    (AC-SEC-01/02) delegando en el helper compartido.
    """
    return build_rtsp_url(host, username, password, channel=channel, subtype=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de conexión RTSP autorizada")
    parser.add_argument("url", nargs="?", default=None, help="URL RTSP explícita")
    parser.add_argument("--host", default=None, help="URL base RTSP sin credenciales")
    parser.add_argument("--username", default=None, help="Usuario RTSP")
    parser.add_argument("--channel", type=int, default=1, help="Canal RTSP (1-16)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Límite en segundos")
    parser.add_argument("--max-frames", type=int, default=30, help="Máximo de fotogramas")
    args = parser.parse_args()

    if args.channel < 1 or args.channel > 16:
        print("Error: canal debe estar entre 1 y 16")
        return 2

    rtsp_url: str = ""
    if args.url:
        rtsp_url = args.url.strip()
    elif args.host and args.username:
        password = getpass.getpass("Contraseña RTSP (no se mostrará): ")
        if not password:
            print("Error: la contraseña no puede estar vacía")
            return 2
        rtsp_url = _with_credentials(args.host.strip(), args.username, password, args.channel)
    elif args.host:
        rtsp_url = args.host.strip()
    else:
        parser.print_help()
        return 2

    if not rtsp_url.startswith("rtsp://"):
        print("Error: la fuente debe ser una URL rtsp://")
        return 2

    # Solo se muestra la representación redactada (sin credenciales).
    print(f"SOURCE (redactada): {redact_rtsp_url(rtsp_url)}")
    print("Iniciando diagnóstico (tiempo limitado)...")

    test = RTSPConnectionTest(
        connect_timeout_seconds=min(args.timeout, 10.0),
        test_duration_seconds=args.timeout,
        max_frames=args.max_frames,
    )
    result = test.run(rtsp_url)

    print(summarize_result(result))

    if result.frame_status == RTSPFrameState.FRAMES_RECEIVED:
        print("RESULT: PASS - frames recibidos")
        return 0

    print("RESULT: FAIL - sin recepción de frames")
    return 1


if __name__ == "__main__":
    sys.exit(main())
