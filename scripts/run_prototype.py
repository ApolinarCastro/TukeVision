"""Ejecuta el prototipo completo SPEC-0001 sobre un video local.

Uso:
    python scripts/run_prototype.py "data/input/video.mp4"
"""

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.app.pipeline import Pipeline, PipelineError, load_config
from src.observability.logging_setup import new_run_id, setup_logging


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/run_prototype.py \"data/input/video.mp4\"")
        sys.exit(1)

    video_path = sys.argv[1]
    run_id = new_run_id()
    setup_logging(run_id=run_id)
    logger = logging.getLogger("tukevision.script")

    if not Path(video_path).exists():
        print(f"VIDEO_PATH: {video_path}")
        print("FINAL_STATUS: ERROR - El archivo de video no existe")
        sys.exit(1)

    try:
        config = load_config()
        pipeline = Pipeline(config=config)
        logger.info("Procesando video. video_path=%s", video_path)
        summary = pipeline.process(video_path)

        print(f"VIDEO_PATH: {summary.video_path}")
        print(f"FRAMES_PROCESSED: {summary.frames_processed}")
        print(f"PERSONS_DETECTED: {summary.persons_detected}")
        print(f"TRACKS_CREATED: {summary.tracks_created}")
        print(f"OBSERVATIONS_CREATED: {summary.observations_created}")
        print(f"EVENTS_CREATED: {summary.events_created}")
        print(f"ALERTS_CREATED: {summary.alerts_created}")
        print(f"EVIDENCE_CREATED: {summary.evidence_created}")
        print(f"OUTPUT_VIDEO: {summary.output_video}")
        print(f"FINAL_STATUS: {summary.final_status}")

    except PipelineError as e:
        print(f"VIDEO_PATH: {video_path}")
        print(f"FINAL_STATUS: ERROR - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"VIDEO_PATH: {video_path}")
        print(f"FINAL_STATUS: ERROR - {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
