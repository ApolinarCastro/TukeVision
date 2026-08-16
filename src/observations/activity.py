"""Activity / Observation Layer mínima (LOOP-0018P).

Convierte señales de múltiples cámaras lógicas en observaciones canónicas,
estructuradas, serializables y sin credenciales. Está desacoplada de la
captura: no hereda ni reescribe SourceManager (composición), no guarda frames
ni objetos OpenCV y nunca expone secretos.

Arquitectura (PRODUCT_CORE.md / FIRST_PRODUCT_DELIVERY.md):

    CAPTURE -> OBSERVATION -> POLICY -> INFERENCE -> EVENT -> EVIDENCE

En LOOP-0018P se dejan operativos OBSERVATION y POLICY mínima:

  - ActivityObservation: observación canónica inmutable por cámara
    (camera_id lógico, timestamp UTC, categoría, estado, payload acotado,
    confianza opcional, origen/productor y referencia opcional a evidencia).
  - BoundedObservationQueue: cola FIFO acotada por cámara con política de
    overflow explícita (memoria limitada, sin crecimiento ilimitado).
  - ObservationPolicy: política CONFIG-DRIVEN con perfiles QUALITY, BALANCED
    y ECONOMY que decide sampling por cámara SIN modificar SourceManager.
  - ActivityLayer: orquesta registro de fuentes lógicas, ingestión
    determinista, aplicación de política, encolado acotado por cámara y
    shutdown limpio. Un productor defectuoso de UNA cámara no bloquea el resto
    (AISLAMIENTO_POR_CAMERA).

Reutilización (REUSE BEFORE NEW DEVELOPMENT, LOOP-0018N):
  - Patrón de perfil con fallback seguro adaptado de E-05 quality_engine
    (QUALITY/ECONOMY -> QUALITY/BALANCED/ECONOMY para análisis/sampling).
  - Patrón de retención acotada (colas con tope y overflow) siguiendo la
    convención BOUNDED_QUEUE ya certificada del SourceManager.
  - redact_rtsp_url de src.observability para no exponer credenciales.

Restricción de CPU (LOOP-0018N): YOLO11n ~54.5 ms/frame a 640x480. La política
por defecto NO habilita inferencia continua 15fps x 4 cámaras; su default es
seguro (perfil BALANCED) y solo decide sampling para inferencia selectiva
posterior. Este módulo no ejecuta YOLO.
"""

import json
import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Deque, Dict, List, Optional

from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.activity")

# ---------------------------------------------------------------------------
# Categorías y estados canónicos de observación
# ---------------------------------------------------------------------------
FRAME_SAMPLE = "FRAME_SAMPLE"
SIGNAL = "SIGNAL"
STATE_CHANGE = "STATE_CHANGE"

VALID_OBSERVATION_TYPES = (FRAME_SAMPLE, SIGNAL, STATE_CHANGE)

ACTIVE = "ACTIVE"
STALE = "STALE"
DEGRADED = "DEGRADED"
ERROR = "ERROR"

VALID_OBSERVATION_STATES = (ACTIVE, STALE, DEGRADED, ERROR)

# Perfiles de política de análisis (CONFIG-DRIVEN).
PROFILE_QUALITY = "QUALITY"
PROFILE_BALANCED = "BALANCED"
PROFILE_ECONOMY = "ECONOMY"
VALID_PROFILES = (PROFILE_QUALITY, PROFILE_BALANCED, PROFILE_ECONOMY)

# Límites sanitizadores (nunca permitir presupuestos absurdos ni configs rotas).
_MIN_MAX_ANALYSIS_FPS = 0.1
_MAX_MAX_ANALYSIS_FPS = 30.0

DEFAULT_SAFE_CONFIG: Dict[str, Any] = {
    "default_profile": PROFILE_BALANCED,
    "profiles": {
        PROFILE_QUALITY: {"max_analysis_fps": 5.0},
        PROFILE_BALANCED: {"max_analysis_fps": 2.0},
        PROFILE_ECONOMY: {"max_analysis_fps": 1.0},
    },
}

# Tamaño máximo acotado del payload de una observación (JSON, en bytes).
_PAYLOAD_MAX_SERIALIZED_BYTES = 4096


def _utc_now_iso() -> str:
    """Timestamp UTC ISO-8601 (formato canónico del sistema)."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


class ActivityError(Exception):
    """Error base de la Activity Layer."""
    pass


class InvalidObservationError(ActivityError):
    """Datos insuficientes o inválidos para crear una observación."""
    pass


# ---------------------------------------------------------------------------
# Schema canónico de observación
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActivityObservation:
    """Observación canónica, inmutable y serializable.

    NO contiene frames, objetos OpenCV ni credenciales. El payload es un dict
    JSON-serializable y acotado. Toda cadena pasa por redact_rtsp_url en la
    serialización (defensa en profundidad contra URLs RTSP con secretos).
    """

    observation_id: str
    camera_id: str
    timestamp: str
    observation_type: str
    state: str
    payload: Dict[str, Any]
    confidence: Optional[float] = None
    origin: str = "activity"
    evidence_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise InvalidObservationError("El identificador es obligatorio")
        if not self.camera_id:
            raise InvalidObservationError("El identificador de cámara es obligatorio")
        if not self.timestamp:
            raise InvalidObservationError("El timestamp es obligatorio")
        if self.observation_type not in VALID_OBSERVATION_TYPES:
            raise InvalidObservationError(
                f"Tipo de observación inválido: {self.observation_type}"
            )
        if self.state not in VALID_OBSERVATION_STATES:
            raise InvalidObservationError(f"Estado inválido: {self.state}")
        if not isinstance(self.payload, dict):
            raise InvalidObservationError("El payload debe ser un dict")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise InvalidObservationError(
                "La confianza debe estar entre 0 y 1"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Representación JSON-serializable, sin secretos ni objetos OpenCV."""
        payload = {}
        for key, value in self.payload.items():
            if isinstance(value, str):
                value = redact_rtsp_url(value)
            payload[key] = value
        try:
            serialized = json.dumps(payload, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise InvalidObservationError(
                "El payload no es JSON-serializable"
            ) from exc
        if len(serialized.encode("utf-8")) > _PAYLOAD_MAX_SERIALIZED_BYTES:
            raise InvalidObservationError(
                "El payload supera el límite acotado de bytes"
            )
        return {
            "observation_id": self.observation_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "observation_type": self.observation_type,
            "state": self.state,
            "payload": payload,
            "confidence": self.confidence,
            "origin": self.origin,
            "evidence_ref": self.evidence_ref,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityObservation":
        """Reconstruye una observación desde su representación canónica."""
        required = (
            "observation_id",
            "camera_id",
            "timestamp",
            "observation_type",
            "state",
            "payload",
        )
        for key in required:
            if key not in data:
                raise InvalidObservationError(f"Falta campo: {key}")
        return cls(
            observation_id=data["observation_id"],
            camera_id=data["camera_id"],
            timestamp=data["timestamp"],
            observation_type=data["observation_type"],
            state=data["state"],
            payload=dict(data["payload"]),
            confidence=data.get("confidence"),
            origin=data.get("origin", "activity"),
            evidence_ref=data.get("evidence_ref"),
        )


# ---------------------------------------------------------------------------
# Cola acotada por cámara
# ---------------------------------------------------------------------------
DROP_OLDEST = "drop_oldest"
DROP_NEWEST = "drop_newest"
_VALID_OVERFLOW = (DROP_OLDEST, DROP_NEWEST)


class BoundedObservationQueue:
    """Cola FIFO acotada por cámara con política de overflow explícita.

    - drop_oldest (default): si la cola está llena se descarta el más antiguo.
    - drop_newest: si la cola está llena NO se encola el nuevo.
    Memoria siempre <= maxlen por cámara. Conteo determinista de descartados.
    """

    def __init__(self, camera_id: str, maxlen: int = 16, overflow: str = DROP_OLDEST) -> None:
        if maxlen < 1:
            raise ActivityError("maxlen debe ser >= 1")
        if overflow not in _VALID_OVERFLOW:
            raise ActivityError(f"overflow inválido: {overflow!r}")
        self._camera_id = camera_id
        self._maxlen = maxlen
        self._overflow = overflow
        self._queue: Deque[ActivityObservation] = deque(maxlen=maxlen)
        self._dropped = 0

    @property
    def camera_id(self) -> str:
        return self._camera_id

    @property
    def overflow(self) -> str:
        return self._overflow

    @property
    def maxlen(self) -> int:
        return self._maxlen

    @property
    def dropped(self) -> int:
        return self._dropped

    def push(self, observation: ActivityObservation) -> None:
        """Encola respetando la política de overflow."""
        if self._overflow == DROP_NEWEST and len(self._queue) >= self._maxlen:
            self._dropped += 1
            return
        if self._overflow == DROP_OLDEST and len(self._queue) >= self._maxlen:
            self._dropped += 1
        self._queue.append(observation)

    def drain(self, limit: Optional[int] = None) -> List[ActivityObservation]:
        """Extrae y devuelve las observaciones en orden FIFO (consumo)."""
        result: List[ActivityObservation] = []
        count = 0
        while self._queue and (limit is None or count < limit):
            result.append(self._queue.popleft())
            count += 1
        return result

    def peek(self) -> Optional[ActivityObservation]:
        if not self._queue:
            return None
        return self._queue[0]

    def __len__(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()


# ---------------------------------------------------------------------------
# Política de análisis (CONFIG-DRIVEN)
# ---------------------------------------------------------------------------
class ObservationPolicy:
    """Decide el sampling por cámara según perfil QUALITY/BALANCED/ECONOMY.

    Cada perfil define max_analysis_fps (presupuesto máximo de análisis por
    cámara). El intervalo de frames se deriva del fps real de la cámara:

        interval = max(1, round(fps_real / max_analysis_fps))

    La decisión es determinista respecto de (camera_id, frame_index, fps):
        should_analyze = (frame_index % interval) == 0

    No modifica SourceManager: solo consulta fps real (composición) y decide.
    Config inválida o ausente -> fallback seguro (BALANCED, sin inferencia
    continua 15fps x 4).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged = dict(DEFAULT_SAFE_CONFIG)
        if isinstance(config, dict):
            for key, value in config.items():
                if value is not None:
                    merged[key] = value
        self._config = merged

        default_profile = self._config.get("default_profile", PROFILE_BALANCED)
        if default_profile not in VALID_PROFILES:
            logger.warning(
                "OBSERVATION_POLICY_INVALID_PROFILE profile=%r -> default=%s",
                default_profile,
                PROFILE_BALANCED,
            )
            default_profile = PROFILE_BALANCED
        self._default_profile = default_profile

        self._profiles: Dict[str, Dict[str, float]] = {}
        raw_profiles = self._config.get("profiles")
        if not isinstance(raw_profiles, dict):
            raw_profiles = {}
        for name in VALID_PROFILES:
            safe = DEFAULT_SAFE_CONFIG["profiles"][name]
            raw = raw_profiles.get(name) or {}
            max_fps = raw.get("max_analysis_fps", safe["max_analysis_fps"])
            try:
                max_fps = float(max_fps)
            except (TypeError, ValueError):
                max_fps = safe["max_analysis_fps"]
            if not (_MIN_MAX_ANALYSIS_FPS <= max_fps <= _MAX_MAX_ANALYSIS_FPS):
                logger.warning(
                    "OBSERVATION_POLICY_CLAMP profile=%s max_analysis_fps=%r -> %s",
                    name,
                    max_fps,
                    safe["max_analysis_fps"],
                )
                max_fps = safe["max_analysis_fps"]
            self._profiles[name] = {"max_analysis_fps": max_fps}

        cameras = self._config.get("cameras")
        if not isinstance(cameras, dict):
            cameras = {}
        self._camera_profiles: Dict[str, str] = {}
        for camera_id, profile in cameras.items():
            if profile in VALID_PROFILES:
                self._camera_profiles[str(camera_id)] = profile

    @property
    def default_profile(self) -> str:
        return self._default_profile

    def set_camera_profile(self, camera_id: str, profile: str) -> None:
        """Fija un perfil por cámara en runtime (override de configuración)."""
        if profile not in VALID_PROFILES:
            raise ActivityError(f"perfil inválido: {profile!r}")
        self._camera_profiles[str(camera_id)] = profile

    def profile_for(self, camera_id: str) -> str:
        return self._camera_profiles.get(camera_id, self._default_profile)

    def max_analysis_fps(self, camera_id: str) -> float:
        profile = self.profile_for(camera_id)
        return self._profiles[profile]["max_analysis_fps"]

    def sampling_interval_frames(self, camera_id: str, fps: float) -> int:
        """Intervalo de frames entre análisis (>= 1) para una cámara."""
        fps = float(fps or 0.0)
        if fps <= 0:
            fps = 15.0  # fallback seguro si no se conoce el fps real
        interval = round(fps / self.max_analysis_fps(camera_id))
        return max(1, int(interval))

    def should_analyze(self, camera_id: str, frame_index: int, fps: float) -> bool:
        """Decisión determinista de análisis para un frame de una cámara."""
        interval = self.sampling_interval_frames(camera_id, fps)
        return int(frame_index) % interval == 0

    def describe(self, camera_id: str, fps: float) -> Dict[str, Any]:
        """Descripción auditable de la decisión de política (evidencia)."""
        return {
            "camera_id": camera_id,
            "profile": self.profile_for(camera_id),
            "max_analysis_fps": self.max_analysis_fps(camera_id),
            "fps": float(fps or 0.0),
            "sampling_interval_frames": self.sampling_interval_frames(camera_id, fps),
        }


# ---------------------------------------------------------------------------
# Activity Layer
# ---------------------------------------------------------------------------
class ActivityLayer:
    """Orquesta la ingestión de señales de cámaras lógicas en observaciones.

    - register_camera: registra una fuente lógica (camera_id) y su fps.
    - feed: ingiere un frame (metadatos/índice) de una cámara; aplica política
      de sampling; si corresponde, invoca al productor y encola la observación.
    - consume/queued/stats: consulta y consumo por cámara.
    - close: shutdown limpio (stats finales, colas vaciadas).
    - Aislamiento: un productor defectuoso de una cámara se marca como ERROR y
      NO bloquea las demás cámaras.
    - Composición con SourceManager: register_from_source_manager lee el
      inventario público (sin credenciales) y el fps real de health().
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        producer: Optional[Callable[[str, int, Optional[Dict[str, Any]]], Optional[Dict[str, Any]]]] = None,
        queue_maxlen: int = 16,
        queue_overflow: str = DROP_OLDEST,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        policy_cfg = config.get("observation") if isinstance(config, dict) else None
        self._policy = ObservationPolicy(policy_cfg)
        self._producer = producer or self._default_producer
        self._queue_maxlen = queue_maxlen
        self._queue_overflow = queue_overflow
        self._clock = clock or _utc_now_iso
        self._lock = threading.RLock()
        self._cameras: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, BoundedObservationQueue] = {}
        self._counters: Dict[str, Dict[str, int]] = {}
        self._seq: Dict[str, int] = {}
        self._closed = False

    # -- registro de fuentes lógicas --------------------------------------
    def register_camera(self, camera_id: str, fps: float = 0.0) -> str:
        """Registra una fuente lógica de observación. Devuelve camera_id."""
        camera_id = (camera_id or "").strip()
        if not camera_id:
            raise ActivityError("camera_id vacío")
        with self._lock:
            if self._closed:
                raise ActivityError("ActivityLayer cerrado")
            if camera_id in self._cameras:
                raise ActivityError(f"cámara ya registrada: {camera_id}")
            self._cameras[camera_id] = {"fps": float(fps or 0.0), "state": ACTIVE}
            self._queues[camera_id] = BoundedObservationQueue(
                camera_id=camera_id,
                maxlen=self._queue_maxlen,
                overflow=self._queue_overflow,
            )
            self._counters[camera_id] = {
                "frames_seen": 0,
                "samples_analyzed": 0,
                "observations_enqueued": 0,
                "observations_dropped": 0,
                "producer_errors": 0,
            }
            self._seq[camera_id] = 0
        logger.info("ACTIVITY_SOURCE_REGISTERED camera_id=%s", camera_id)
        return camera_id

    def register_from_source_manager(self, source_manager) -> List[str]:
        """Composición: registra las cámaras del SourceManager (sin tocar su código).

        Lee el inventario público (list_sources, sin credenciales) y el fps real
        de health(). No abre cámaras.
        """
        registered: List[str] = []
        for item in source_manager.list_sources():
            camera_id = item.get("camera_id")
            if not camera_id:
                continue
            fps = 0.0
            try:
                health = source_manager.health(camera_id)
                fps = float(getattr(health, "fps", 0.0) or 0.0)
            except Exception:
                fps = 0.0
            self.register_camera(camera_id, fps=fps)
            registered.append(camera_id)
        return registered

    def list_cameras(self) -> List[str]:
        with self._lock:
            return sorted(self._cameras.keys())

    def set_camera_fps(self, camera_id: str, fps: float) -> None:
        with self._lock:
            self._require_camera(camera_id)
            self._cameras[camera_id]["fps"] = float(fps or 0.0)

    def set_camera_profile(self, camera_id: str, profile: str) -> None:
        with self._lock:
            self._require_camera(camera_id)
            self._policy.set_camera_profile(camera_id, profile)

    def policy_for(self, camera_id: str) -> ObservationPolicy:
        return self._policy

    # -- ingestión ----------------------------------------------------------
    def feed(
        self,
        camera_id: str,
        frame_index: int,
        metadata: Optional[Dict[str, Any]] = None,
        frame: Any = None,
    ) -> Optional[ActivityObservation]:
        """Ingiere un frame de una cámara lógica y devuelve la observación si
        el sampling la selecciona; None en caso contrario.

        `frame` se pasa al productor solo para análisis futuro (inferencia
        selectiva) y NUNCA se almacena ni se serializa. `metadata` no debe
        contener credenciales; si lo hiciera, to_dict() lo redacta.
        """
        with self._lock:
            self._require_camera(camera_id)
            if self._closed:
                raise ActivityError("ActivityLayer cerrado")
            fps = float(self._cameras[camera_id].get("fps", 0.0) or 0.0)
            self._counters[camera_id]["frames_seen"] += 1

        if not self._policy.should_analyze(camera_id, frame_index, fps):
            return None

        with self._lock:
            self._counters[camera_id]["samples_analyzed"] += 1

        # Aislamiento: el error del productor afecta solo a esta cámara.
        try:
            payload = self._producer(camera_id, frame_index, metadata)
        except Exception as exc:  # aislar: no bloquea otras cámaras
            with self._lock:
                self._counters[camera_id]["producer_errors"] += 1
                self._cameras[camera_id]["state"] = ERROR
            logger.error(
                "ACTIVITY_PRODUCER_FAILED camera_id=%s frame=%d err=%s",
                camera_id,
                frame_index,
                exc,
            )
            return None

        if payload is None:
            return None

        with self._lock:
            self._seq[camera_id] += 1
            observation = ActivityObservation(
                observation_id=f"OBS-{camera_id}-{self._seq[camera_id]:06d}",
                camera_id=camera_id,
                timestamp=self._clock(),
                observation_type=FRAME_SAMPLE,
                state=ACTIVE,
                payload=payload,
                confidence=payload.get("confidence") if isinstance(payload, dict) else None,
                origin="activity:sampler",
            )
            queue = self._queues[camera_id]
            queue.push(observation)
            if queue.dropped > 0:
                self._counters[camera_id]["observations_dropped"] = queue.dropped
            self._counters[camera_id]["observations_enqueued"] += 1
        logger.info(
            "ACTIVITY_OBSERVATION camera_id=%s frame=%d obs=%s",
            camera_id,
            frame_index,
            observation.observation_id,
        )
        return observation

    # -- consulta / consumo -------------------------------------------------
    def consume(self, camera_id: str, limit: Optional[int] = None) -> List[ActivityObservation]:
        with self._lock:
            self._require_camera(camera_id)
            return self._queues[camera_id].drain(limit=limit)

    def queued(self, camera_id: str) -> int:
        with self._lock:
            self._require_camera(camera_id)
            return len(self._queues[camera_id])

    def peek(self, camera_id: str) -> Optional[ActivityObservation]:
        with self._lock:
            self._require_camera(camera_id)
            return self._queues[camera_id].peek()

    def camera_state(self, camera_id: str) -> str:
        with self._lock:
            self._require_camera(camera_id)
            return self._cameras[camera_id]["state"]

    def stats(self) -> Dict[str, Dict[str, Any]]:
        """Estado auditable por cámara (sin credenciales)."""
        with self._lock:
            result: Dict[str, Dict[str, Any]] = {}
            for camera_id in sorted(self._cameras):
                counters = dict(self._counters[camera_id])
                counters["queued"] = len(self._queues[camera_id])
                counters["queue_dropped"] = self._queues[camera_id].dropped
                result[camera_id] = {
                    "fps": self._cameras[camera_id].get("fps", 0.0),
                    "state": self._cameras[camera_id]["state"],
                    "profile": self._policy.profile_for(camera_id),
                    "counters": counters,
                }
            return result

    # -- shutdown ------------------------------------------------------------
    def close(self) -> Dict[str, Dict[str, Any]]:
        """Shutdown limpio: devuelve stats finales y vacía las colas."""
        with self._lock:
            self._closed = True
            final_stats = self.stats()
            for queue in self._queues.values():
                queue.clear()
            logger.info(
                "ACTIVITY_LAYER_CLOSED cameras=%d",
                len(self._queues),
            )
            return final_stats

    # -- internos ------------------------------------------------------------
    def _require_camera(self, camera_id: str) -> None:
        if camera_id not in self._cameras:
            raise ActivityError(f"cámara no registrada: {camera_id}")

    @staticmethod
    def _default_producer(
        camera_id: str, frame_index: int, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Productor por defecto: observación determinista sin inferencia.

        No ejecuta YOLO: solo registra un muestreo de señal con metadatos
        acotados. El productor real (inferencia selectiva) se conecta en un
        PRODUCT ADVANCE posterior sobre este mismo contrato.
        """
        payload: Dict[str, Any] = {
            "frame_index": int(frame_index),
            "source": camera_id,
        }
        if isinstance(metadata, dict):
            for key in ("resolution", "fps", "source_type"):
                if key in metadata:
                    value = metadata[key]
                    if isinstance(value, str):
                        value = redact_rtsp_url(value)
                    payload[key] = value
        return payload