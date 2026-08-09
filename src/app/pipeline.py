"""Integración del flujo completo.

Responsabilidad única: orquestar el pipeline
Video → Detección → Seguimiento → Observaciones → Evento → Regla →
Riesgo → Alerta → Evidencia para un único video local.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

import cv2
import numpy as np

from src.capture.video_source import VideoSource, VideoSourceError
from src.detection.person_detector import PersonDetector
from src.tracking.person_tracker import PersonTracker
from src.context.zone import Zone
from src.observations.engine import ObservationEngine
from src.events.engine import EventEngine
from src.business.rules import RuleEngine, default_rule
from src.risk.calculator import RiskCalculator
from src.alerts.engine import AlertEngine
from src.alerts.models import Alert
from src.evidence.store import EvidenceStore
from src.evidence.models import EvidenceMetadata


class PipelineError(Exception):
    """Excepción base para errores del pipeline."""
    pass


class PipelineConfigError(PipelineError):
    """Configuración insuficiente o inválida."""
    pass


@dataclass(frozen=True)
class PipelineSummary:
    """Resumen del procesamiento de un video."""
    video_path: str
    frames_processed: int
    persons_detected: int
    tracks_created: int
    observations_created: int
    events_created: int
    alerts_created: int
    evidence_created: int
    output_video: str
    final_status: str


@dataclass(frozen=True)
class FrameSnapshot:
    """Estado observado de un fotograma, para consumo de la interfaz.

    Se construye tras anotar cada fotograma y se entrega a un callback
    opcional sin alterar la lógica del pipeline. Contiene únicamente
    datos ya calculados por el núcleo certificado.
    """
    frame_index: int
    frame: np.ndarray
    source_type: str
    source_path: str
    source_state: str
    fps: float
    tracked_objects: tuple
    stays_seconds: Dict[int, float]
    in_zone_track_ids: tuple
    risk_text: str
    latest_alert: Optional[Alert]
    latest_evidence_path: Optional[str]
    frames_processed: int
    persons_detected: int
    alerts_total: int
    evidence_total: int


def load_config(config_path: str = "config/default.json") -> dict:
    """Carga la configuración desde un archivo JSON."""
    path = Path(config_path)
    if not path.exists():
        raise PipelineConfigError(f"Configuración no encontrada: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class Pipeline:
    """Procesa un video local completo, de forma secuencial y en CPU."""

    def __init__(self, config: Optional[dict] = None) -> None:
        self._config = config or load_config()

        video_cfg = self._config.get("video", {})
        detection_cfg = self._config.get("detection", {})
        zone_cfg = self._config.get("zone", {})
        business_cfg = self._config.get("business", {})
        alert_cfg = self._config.get("alerts", {})

        if not zone_cfg.get("id") or not zone_cfg.get("polygon"):
            raise PipelineConfigError("La zona debe tener id y polígono")

        self._max_width = video_cfg.get("max_width", 640)
        self._process_every_n_frames = video_cfg.get("process_every_n_frames", 1)
        self._store_id = business_cfg.get("store_id", "STORE-001")
        self._camera_id = business_cfg.get("camera_id", "CAM-001")
        self._max_stay_seconds = float(business_cfg.get("max_stay_seconds", 30.0))
        self._remain_interval_frames = int(
            business_cfg.get("remain_interval_frames", 30)
        )
        self._risk_threshold = int(alert_cfg.get("risk_threshold", 60))

        self._detector = PersonDetector(
            model_path=str(Path("models") / detection_cfg.get("model", "yolo11n.pt")),
            class_ids=detection_cfg.get("class_ids", [0]),
            confidence_threshold=detection_cfg.get("confidence_threshold", 0.35),
            device=detection_cfg.get("device", "cpu"),
            image_size=detection_cfg.get("image_size", 640),
        )
        self._tracker = PersonTracker()
        self._zone = Zone(
            zone_id=zone_cfg["id"],
            name=zone_cfg.get("name", "Zona piloto"),
            polygon=zone_cfg["polygon"],
        )
        self._observation_engine = ObservationEngine(
            remain_interval_frames=self._remain_interval_frames
        )
        self._event_engine = EventEngine(max_stay_seconds=self._max_stay_seconds)
        self._rule_engine = RuleEngine([default_rule()])
        self._risk_calculator = RiskCalculator()
        self._alert_engine = AlertEngine(risk_threshold=self._risk_threshold)
        self._evidence_store = EvidenceStore()

        self._entry_frame: Dict[int, int] = {}
        self._clock_start: Optional[float] = None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _elapsed_seconds(self) -> float:
        """Tiempo transcurrido desde el inicio del procesamiento (reloj monotónico)."""
        if self._clock_start is None:
            self._clock_start = time.monotonic()
        return time.monotonic() - self._clock_start

    def _frame_timestamp(self, frame_index: int, fps: float) -> str:
        """Genera un timestamp ISO basado en el índice de fotograma y FPS."""
        # Usamos una fecha base fija para que los timestamps sean deterministas
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        seconds = frame_index / max(fps, 1.0)
        return (base + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

    def _live_timestamp(self, elapsed_seconds: float) -> str:
        """Genera un timestamp ISO basado en el reloj monotónico de una fuente en vivo."""
        base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        return (base + timedelta(seconds=elapsed_seconds)).isoformat().replace("+00:00", "Z")

    def _stay_seconds(self, track_id: int, current_frame: int, fps: float) -> float:
        entry = self._entry_frame.get(track_id)
        if entry is None:
            self._entry_frame[track_id] = current_frame
            return 0.0
        return (current_frame - entry) / max(fps, 1.0)

    def _annotate(
        self,
        frame,
        tracked,
        fps: float,
        current_frame: int,
        risk_text: str = "",
    ) -> None:
        """Dibuja zona, cajas, identificadores y tiempo de permanencia."""
        pts = np.array(
            [[int(p[0]), int(p[1])] for p in self._zone.polygon],
            dtype=np.int32,
        )
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 200, 0), thickness=2)

        for obj in tracked:
            x1, y1, x2, y2 = obj.x1, obj.y1, obj.x2, obj.y2
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
            stay = self._stay_seconds(obj.track_id, current_frame, fps)
            label = f"ID {obj.track_id} {stay:.1f}s"
            cv2.putText(
                frame, label, (x1, max(10, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
            )

        if risk_text:
            cv2.putText(
                frame, risk_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
            )

    def process(
        self,
        video_path: str,
        output_video: Optional[str] = None,
        on_frame: Optional[Callable[[FrameSnapshot], None]] = None,
    ) -> PipelineSummary:
        """Procesa un video local y devuelve un resumen."""
        source = VideoSource(
            video_path,
            max_width=self._max_width,
            process_every_n_frames=self._process_every_n_frames,
        )
        return self.process_source(source, output_video=output_video, on_frame=on_frame)

    def process_source(
        self,
        source,
        output_video: Optional[str] = None,
        on_frame: Optional[Callable[[FrameSnapshot], None]] = None,
    ) -> PipelineSummary:
        """Procesa una fuente con interfaz común (archivo, webcam o RTSP).

        La fuente debe exponer open(), frames(), close(), metadata e is_live.
        El núcleo del pipeline no conoce el origen de los fotogramas.
        """
        if output_video is None:
            output_dir = Path("data/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_video = str(output_dir / "processed.mp4")

        frames_processed = 0
        persons_detected = 0
        tracks_created = 0
        observations_created = 0
        events_created = 0
        alerts_created = 0
        evidence_created = 0
        unique_tracks = set()
        output_writer = None

        try:
            metadata = source.open()
            is_live = getattr(source, "is_live", False) is True
            self._clock_start = time.monotonic()
            self._entry_frame.clear()

            out_path = Path(output_video)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            writer_fps = metadata.fps if metadata.fps > 0 else 30.0
            output_writer = cv2.VideoWriter(
                str(out_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                writer_fps,
                (metadata.width, metadata.height),
            )

            for frame_index, frame in source.frames():
                frames_processed += 1
                if is_live:
                    time_value = self._elapsed_seconds()
                    time_fps = 1.0
                    frame_time = self._live_timestamp(time_value)
                else:
                    time_value = frame_index
                    time_fps = writer_fps
                    frame_time = self._frame_timestamp(frame_index, writer_fps)

                detection_result = self._detector.detect(frame)
                persons_detected += len(detection_result.detections)

                tracking_result = self._tracker.update(
                    detection_result.detections
                )
                tracked = tracking_result.tracked_objects
                unique_tracks.update(obj.track_id for obj in tracked)

                risk_text = ""
                latest_alert = None
                latest_evidence_path = None
                for obj in tracked:
                    transition = self._zone.update(
                        obj.track_id, obj.x1, obj.y1, obj.x2, obj.y2
                    )
                    stay = self._stay_seconds(
                        obj.track_id, time_value, time_fps
                    )
                    observation = self._observation_engine.process_transition(
                        transition=transition,
                        track_id=obj.track_id,
                        store_id=self._store_id,
                        camera_id=self._camera_id,
                        zone_id=self._zone.zone_id,
                        source_frame=frame_index,
                        timestamp=frame_time,
                        confidence=obj.confidence,
                        value=stay,
                    )
                    if observation is None:
                        continue
                    observations_created += 1
                    event = self._event_engine.process(observation)
                    if event is None:
                        continue
                    events_created += 1
                    rule = self._rule_engine.evaluate(event)
                    if rule is None:
                        continue
                    risk = self._risk_calculator.calculate(event, rule)
                    alert = self._alert_engine.evaluate(event, risk)
                    if alert is None:
                        risk_text = f"riesgo {risk.score}"
                        continue
                    alerts_created += 1
                    latest_alert = alert
                    meta = EvidenceMetadata(
                        alert_id=alert.alert_id,
                        event_id=event.event_id,
                        observation_ids=tuple(event.observation_ids),
                        track_id=event.track_id,
                        zone_id=self._zone.zone_id,
                        duration_seconds=event.duration_seconds,
                        risk_score=risk.score,
                        rule_id=rule.rule_id,
                        timestamp=event.timestamp,
                        frame_sha256="",
                    )
                    evidence_path = self._evidence_store.save(frame, meta)
                    evidence_created += 1
                    latest_evidence_path = str(evidence_path)
                    risk_text = (
                        f"ALERTA {alert.alert_id} riesgo {risk.score}"
                    )

                self._annotate(
                    frame, tracked, time_fps, time_value, risk_text
                )
                if on_frame is not None:
                    stays_seconds = {}
                    in_zone_track_ids = tuple(
                        obj.track_id
                        for obj in tracked
                        if self._zone.is_inside(obj.track_id)
                    )
                    for obj in tracked:
                        stays_seconds[obj.track_id] = self._stay_seconds(
                            obj.track_id, time_value, time_fps
                        )
                    on_frame(FrameSnapshot(
                        frame_index=frame_index,
                        frame=frame,
                        source_type=getattr(source, "source_type", "FILE"),
                        source_path=getattr(source.metadata, "path", ""),
                        source_state=getattr(source, "state", "OPEN"),
                        fps=getattr(source.metadata, "fps", 0.0),
                        tracked_objects=tuple(tracked),
                        stays_seconds=stays_seconds,
                        in_zone_track_ids=in_zone_track_ids,
                        risk_text=risk_text,
                        latest_alert=latest_alert,
                        latest_evidence_path=latest_evidence_path,
                        frames_processed=frames_processed,
                        persons_detected=persons_detected,
                        alerts_total=alerts_created,
                        evidence_total=evidence_created,
                    ))
                output_writer.write(frame)

            # Finalizar eventos pendientes para tracks que siguen en la zona al final
            if is_live:
                final_timestamp = self._live_timestamp(self._elapsed_seconds())
            else:
                final_timestamp = self._frame_timestamp(frames_processed, writer_fps)
            final_events = self._event_engine.finalize(final_timestamp)
            for event in final_events:
                events_created += 1
                rule = self._rule_engine.evaluate(event)
                if rule is None:
                    continue
                risk = self._risk_calculator.calculate(event, rule)
                alert = self._alert_engine.evaluate(event, risk)
                if alert is None:
                    continue
                alerts_created += 1
                meta = EvidenceMetadata(
                    alert_id=alert.alert_id,
                    event_id=event.event_id,
                    observation_ids=tuple(event.observation_ids),
                    track_id=event.track_id,
                    zone_id=self._zone.zone_id,
                    duration_seconds=event.duration_seconds,
                    risk_score=risk.score,
                    rule_id=rule.rule_id,
                    timestamp=event.timestamp,
                    frame_sha256="",
                )
                evidence_path = self._evidence_store.save(frame, meta)
                evidence_created += 1

            tracks_created = len(unique_tracks)

            return PipelineSummary(
                video_path=metadata.path,
                frames_processed=frames_processed,
                persons_detected=persons_detected,
                tracks_created=tracks_created,
                observations_created=observations_created,
                events_created=events_created,
                alerts_created=alerts_created,
                evidence_created=evidence_created,
                output_video=output_video,
                final_status="OK",
            )
        except VideoSourceError as e:
            raise PipelineError(f"Error de video: {e}")
        except BaseException:
            raise
        except Exception as e:
            raise PipelineError(f"Error en pipeline: {e}")
        finally:
            if output_writer is not None:
                output_writer.release()
            try:
                source.close()
            except Exception:
                pass
            self._detector.close()
            self._tracker.close()
