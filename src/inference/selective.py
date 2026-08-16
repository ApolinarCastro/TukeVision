"""Inferencia SELECTIVA gobernada por ObservationPolicy (LOOP-0018Q).

    CAMERA/SOURCE -> OBSERVATION -> POLICY -> SELECTIVE INFERENCE
                                        -> EVENT -> EVIDENCE_REFERENCE

SelectiveInferencePipeline compone:

  - ObservationPolicy (REUTILIZADA desde src.observations.activity, sin
    duplicarla): decide CUÁNDO procesar cada frame por cámara según perfil
    QUALITY/BALANCED/ECONOMY. Decisión determinista.
  - InferenceEngine (contrato): motor de inferencia sustituible.
  - EventDetector: regla mínima config-driven.
  - BoundedEventQueue: cola acotada por cámara (procesamiento bounded).

Aislamiento: un fallo del backend para CAM-X se contabiliza como
inference_errors y NO detiene SourceManager, Observation Layer ni otras
cámaras. Sin bucles infinitos de retry: cada feed decide una vez.

Métricas mínimas por cámara y total: considered, processed,
skipped_by_policy, inference_errors, events_generated, latency (sum/avg/last).
Sin crecimiento ilimitado de memoria (contadores + colas acotadas).

No guarda frames: evidencia por referencia (evidence_ref) y bajo demanda.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from src.inference.contract import (
    InferenceEngine,
    InferenceResult,
)
from src.inference.events import (
    BoundedEventQueue,
    DROP_OLDEST,
    EventDetector,
    InferenceEvent,
)
from src.observations.activity import (
    ActivityError,
    ObservationPolicy,
    PROFILE_BALANCED,
)

logger = logging.getLogger("tukevision.inference")


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class SelectiveInferenceError(Exception):
    """Error base de la capa de inferencia selectiva."""
    pass


class SelectiveInferencePipeline:
    """Inferencia selectiva por cámara bajo política de observación.

    La política decide si un frame se procesa o se salta. Cuando se procesa,
    se ejecuta el backend (motor) y el EventDetector convierte el resultado en
    evento si corresponde. Las métricas son por cámara y total.
    """

    def __init__(
        self,
        policy_config: Optional[Dict[str, Any]] = None,
        engine: Optional[InferenceEngine] = None,
        event_detector: Optional[EventDetector] = None,
        event_queue_maxlen: int = 16,
        event_queue_overflow: str = DROP_OLDEST,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self._policy = ObservationPolicy(policy_config)
        self._engine = engine
        self._event_detector = event_detector or EventDetector()
        self._queue_maxlen = event_queue_maxlen
        self._queue_overflow = event_queue_overflow
        self._clock = clock or _utc_now_iso
        self._lock = threading.RLock()
        self._cameras: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, BoundedEventQueue] = {}
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._totals: Dict[str, Any] = {
            "considered": 0,
            "processed": 0,
            "skipped_by_policy": 0,
            "inference_errors": 0,
            "events_generated": 0,
            "latency_ms_sum": 0.0,
            "latency_ms_last": 0.0,
            "latency_ms_avg": 0.0,
        }
        self._closed = False

    # -- registro de cámaras lógicas --------------------------------------
    def register_camera(self, camera_id: str) -> str:
        camera_id = (camera_id or "").strip()
        if not camera_id:
            raise SelectiveInferenceError("camera_id vacío")
        with self._lock:
            if self._closed:
                raise SelectiveInferenceError("SelectiveInference cerrado")
            if camera_id in self._cameras:
                raise SelectiveInferenceError(f"cámara ya registrada: {camera_id}")
            self._cameras[camera_id] = {}
            self._queues[camera_id] = BoundedEventQueue(
                maxlen=self._queue_maxlen,
                overflow=self._queue_overflow,
            )
            self._metrics[camera_id] = {
                "considered": 0,
                "processed": 0,
                "skipped_by_policy": 0,
                "inference_errors": 0,
                "events_generated": 0,
                "latency_ms_sum": 0.0,
                "latency_ms_last": 0.0,
                "latency_ms_avg": 0.0,
            }
        logger.info("SELECTIVE_INFERENCE_CAMERA_REGISTERED camera_id=%s", camera_id)
        return camera_id

    def register_from_source_manager(self, source_manager) -> List[str]:
        """Composición: registra las cámaras lógicas del SourceManager."""
        registered: List[str] = []
        for item in source_manager.list_sources():
            camera_id = item.get("camera_id")
            if camera_id:
                self.register_camera(camera_id)
                registered.append(camera_id)
        return registered

    def list_cameras(self) -> List[str]:
        with self._lock:
            return sorted(self._cameras.keys())

    def set_camera_profile(self, camera_id: str, profile: str) -> None:
        with self._lock:
            self._require_camera(camera_id)
            self._policy.set_camera_profile(camera_id, profile)

    def policy_for(self, camera_id: str) -> ObservationPolicy:
        return self._policy

    def profile_for(self, camera_id: str) -> str:
        return self._policy.profile_for(camera_id)

    # -- procesamiento selectivo --------------------------------------------
    def feed(
        self,
        camera_id: str,
        frame_index: int,
        fps: float = 0.0,
        frame: Any = None,
        observation_ref: Optional[str] = None,
        evidence_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[InferenceEvent]:
        """Procesa selectivamente un frame de una cámara lógica.

        Retorna el evento generado (si el resultado lo dispara) o None
        (saltado por política, sin detección que alcance regla, o fallo
        aislado del backend). El frame NUNCA se almacena ni serializa.
        """
        with self._lock:
            self._require_camera(camera_id)
            if self._closed:
                raise SelectiveInferenceError("SelectiveInference cerrado")
            self._metrics[camera_id]["considered"] += 1
            self._totals["considered"] += 1

        if not self._policy.should_analyze(camera_id, int(frame_index), float(fps or 0.0)):
            with self._lock:
                self._metrics[camera_id]["skipped_by_policy"] += 1
                self._totals["skipped_by_policy"] += 1
            return None

        with self._lock:
            self._metrics[camera_id]["processed"] += 1
            self._totals["processed"] += 1

        # Aislamiento del backend: fallo de CAM-X no afecta a las demás.
        start = time.perf_counter()
        try:
            result: Optional[InferenceResult] = self._engine.infer(
                frame=frame,
                camera_id=camera_id,
                observation_ref=observation_ref,
                evidence_ref=evidence_ref,
                metadata=metadata,
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            with self._lock:
                self._metrics[camera_id]["inference_errors"] += 1
                self._totals["inference_errors"] += 1
                self._metrics[camera_id]["latency_ms_last"] = round(latency, 3)
                self._metrics[camera_id]["latency_ms_sum"] += round(latency, 3)
            logger.error(
                "SELECTIVE_INFERENCE_BACKEND_FAILED camera_id=%s frame=%d err=%s",
                camera_id,
                frame_index,
                exc,
            )
            return None

        # Latencia autoritativa: la del resultado del motor (determinista si el
        # backend la simula). Fallback a medición de pared solo si no existe.
        if result is not None and result.latency_ms > 0:
            latency = result.latency_ms
        else:
            latency = (time.perf_counter() - start) * 1000.0
        with self._lock:
            self._metrics[camera_id]["latency_ms_last"] = round(latency, 3)
            self._metrics[camera_id]["latency_ms_sum"] += round(latency, 3)
            self._totals["latency_ms_last"] = round(latency, 3)
            self._totals["latency_ms_sum"] += round(latency, 3)

        if result is None:
            return None

        # Event detection mínima.
        event = self._event_detector.detect(result)
        if event is None:
            return None

        with self._lock:
            queue = self._queues[camera_id]
            queue.push(event)
            self._metrics[camera_id]["events_generated"] += 1
            self._totals["events_generated"] += 1
            self._recompute_latency_avg(camera_id)

        logger.info(
            "SELECTIVE_INFERENCE_EVENT camera_id=%s frame=%d event=%s type=%s",
            camera_id,
            frame_index,
            event.event_id,
            event.event_type,
        )
        return event

    def _recompute_latency_avg(self, camera_id: str) -> None:
        processed = self._metrics[camera_id]["processed"]
        if processed > 0:
            self._metrics[camera_id]["latency_ms_avg"] = round(
                self._metrics[camera_id]["latency_ms_sum"] / processed, 3
            )
        total_processed = self._totals["processed"]
        if total_processed > 0:
            self._totals["latency_ms_avg"] = round(
                self._totals["latency_ms_sum"] / total_processed, 3
            )

    # -- consulta / consumo -------------------------------------------------
    def consume(self, camera_id: str, limit: Optional[int] = None) -> List[InferenceEvent]:
        with self._lock:
            self._require_camera(camera_id)
            return self._queues[camera_id].drain(limit=limit)

    def queued(self, camera_id: str) -> int:
        with self._lock:
            self._require_camera(camera_id)
            return len(self._queues[camera_id])

    def peek(self, camera_id: str) -> Optional[InferenceEvent]:
        with self._lock:
            self._require_camera(camera_id)
            return self._queues[camera_id].peek()

    def event_queue_dropped(self, camera_id: str) -> int:
        with self._lock:
            self._require_camera(camera_id)
            return self._queues[camera_id].dropped

    def metrics(self) -> Dict[str, Dict[str, Any]]:
        """Métricas por cámara (sin credenciales, sin crecimiento ilimitado)."""
        with self._lock:
            result: Dict[str, Dict[str, Any]] = {}
            for camera_id in sorted(self._cameras):
                m = dict(self._metrics[camera_id])
                m["profile"] = self._policy.profile_for(camera_id)
                m["queued_events"] = len(self._queues[camera_id])
                m["event_queue_dropped"] = self._queues[camera_id].dropped
                result[camera_id] = m
            return result

    def totals(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._totals)

    # -- shutdown ------------------------------------------------------------
    def close(self) -> Dict[str, Any]:
        """Shutdown limpio: cierra el backend y devuelve métricas finales."""
        with self._lock:
            self._closed = True
            for queue in self._queues.values():
                queue.clear()
            engine = self._engine
            if engine is not None:
                try:
                    engine.close()
                except Exception as exc:
                    logger.warning("SELECTIVE_INFERENCE_CLOSE_WARN err=%s", exc)
            logger.info(
                "SELECTIVE_INFERENCE_CLOSED cameras=%d",
                len(self._queues),
            )
            return self.totals()

    # -- internos ------------------------------------------------------------
    def _require_camera(self, camera_id: str) -> None:
        if camera_id not in self._cameras:
            raise SelectiveInferenceError(f"cámara no registrada: {camera_id}")


def build_pipeline(config: Optional[Dict[str, Any]]) -> SelectiveInferencePipeline:
    """Construye el pipeline selectivo desde config `inference` (config-driven).

    Lee backend, thresholds, cola de eventos y reglas de eventos directamente
    de config/default.json -> inference. Fail-safe: config inválida produce un
    error explícito (nunca silencio peligroso en runtime).
    """
    if not isinstance(config, dict):
        raise SelectiveInferenceError("Config de inferencia inválida: no es dict")

    from src.inference.engines import build_engine

    engine = build_engine(config)
    event_rules = config.get("events")
    if event_rules is None:
        event_detector = EventDetector()
    elif isinstance(event_rules, list):
        event_detector = EventDetector(rules=event_rules)
        if not event_detector.rules:
            raise SelectiveInferenceError(
                "inference.events configurado pero sin reglas válidas"
            )
    else:
        raise SelectiveInferenceError("inference.events debe ser una lista")

    queue_maxlen = int(config.get("event_queue_maxlen", 16))
    if queue_maxlen < 1:
        raise SelectiveInferenceError("event_queue_maxlen debe ser >= 1")
    queue_overflow = str(config.get("event_queue_overflow", DROP_OLDEST))
    if queue_overflow not in (DROP_OLDEST, "drop_newest"):
        raise SelectiveInferenceError(
            f"event_queue_overflow inválido: {queue_overflow!r}"
        )

    return SelectiveInferencePipeline(
        policy_config=config.get("policy"),
        engine=engine,
        event_detector=event_detector,
        event_queue_maxlen=queue_maxlen,
        event_queue_overflow=queue_overflow,
    )