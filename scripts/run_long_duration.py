"""Prueba prolongada controlada de TukeVision (LOOP-0011).

Ejecuta el pipeline sobre la webcam local durante un tiempo acotado por
MAX_DURATION_SECONDS (por defecto 1800s = 30 minutos). Al alcanzar el
límite, la ejecución termina limpiamente con final_status=DURATION_LIMIT:
se cierran escritor, fuente, detector y tracker (sin forzar procesos).

No es una prueba de 24 horas: valida el funcionamiento sostenido y el
mecanismo equivalente explícito de terminación para fuentes en vivo.

Uso:
    python scripts/run_long_duration.py [--seconds 1800] [--output DIR]
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.app.pipeline import Pipeline, PipelineError, load_config
from src.capture.live_sources import WebcamSource
from src.observability.logging_setup import new_run_id, setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba prolongada de TukeVision")
    parser.add_argument(
        "--seconds",
        type=int,
        default=1800,
        help="Duración máxima en segundos (por defecto 1800).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directorio del video de salida (por defecto data/temp).",
    )
    args = parser.parse_args()

    run_id = new_run_id()
    logger = setup_logging(run_id=run_id)
    logger.info(
        "LONG_RUN_INIT run_id=%s max_duration_seconds=%s",
        run_id,
        args.seconds,
    )

    output_dir = Path(args.output or "data/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_video = str(output_dir / f"long_run_{run_id}.mp4")

    try:
        config = load_config()
        pipeline = Pipeline(config=config)
    except PipelineError as e:
        logger.error("LONG_RUN_CONFIG_ERROR %s", e)
        print("LONG_RUN_CONFIG_ERROR")
        print(f"FINAL_STATUS: ERROR - {e}")
        return 1

    source = WebcamSource(
        camera_index=0,
        max_width=config.get("video", {}).get("max_width", 640),
        process_every_n_frames=config.get("video", {}).get(
            "process_every_n_frames", 1
        ),
        backend=cv2.CAP_DSHOW,
    )

    start = time.monotonic()
    try:
        summary = pipeline.process_source(
            source,
            output_video=output_video,
            max_duration_seconds=float(args.seconds),
        )
        elapsed = time.monotonic() - start
        logger.info(
            "LONG_RUN_END final_status=%s elapsed=%.1fs frames=%s "
            "personas=%s alertas=%s evidencia=%s",
            summary.final_status,
            elapsed,
            summary.frames_processed,
            summary.persons_detected,
            summary.alerts_created,
            summary.evidence_created,
        )
        print(f"RUN_ID: {run_id}")
        print(f"LONG_RUN_DURATION_SECONDS: {int(elapsed)}")
        print(f"MAX_DURATION_SECONDS: {args.seconds}")
        print(f"FRAMES_PROCESSED: {summary.frames_processed}")
        print(f"PERSONS_DETECTED: {summary.persons_detected}")
        print(f"ALERTS_CREATED: {summary.alerts_created}")
        print(f"EVIDENCE_CREATED: {summary.evidence_created}")
        print(f"OUTPUT_VIDEO: {summary.output_video}")
        print(f"FINAL_STATUS: {summary.final_status}")
        return 0
    except (PipelineError, Exception) as e:  # noqa: BLE001
        logger.exception("LONG_RUN_ERROR")
        print(f"FINAL_STATUS: ERROR - {type(e).__name__}: {e}")
        return 1
    finally:
        logger.info("LONG_RUN_CLOSE solicitado")


if __name__ == "__main__":
    sys.exit(main())
