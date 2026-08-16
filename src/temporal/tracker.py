"""Motor de tracking LOCAL y actividad temporal (LOOP-0018R).

    EVENT -> LOCAL TRACK -> TEMPORAL ACTIVITY -> OPERATIONAL EVIDENCE

LocalTracker consume eventos canónicos (duck-typing compatible con
InferenceEvent) y los asocia a tracks LOCALES por cámara usando señales
deterministas: misma cámara, mismo tipo/clase, proximidad temporal y,
cuando el bbox esté disponible, IoU mínima (criterio espacial sencillo).

Ciclo de vida: STARTED -> ACTIVE -> ENDED.

  - Un evento compatible dentro de la ventana temporal actualiza el track.
  - Un track que supera `track_timeout_ms` se cierra (ENDED).
  - Un evento posterior compatible crea un NUEVO track (no resucita el anterior).

Retención BOUNDED (config-driven): active tracks por cámara, historial de
completados, refs de eventos por track y refs de evidencia (first/latest/best).

Aislamiento por cámara: cada cámara mantiene su propio espacio de estado;
una excepción/estado corrupto de CAM-X no afecta a CAM-Y.

NO correlación cross-camera de identidad: `track_id` es LOCAL a una cámara.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.temporal.contract import (
    ACTIVE,
    ENDED,
    OBJECT_PRESENCE,
    PERSON_PRESENCE,
    STARTED,
    LocalTrack,
    TemporalActivity,
    TemporalConfigError,
    TemporalError,
    TemporalValidationError,
    duration_ms,
    parse_iso_utc,
)

logger = logging.getLogger("tukevision.temporal")

# Defaults conservadores (config-driven; nunca dispersos en el código).
_DEFAULT_ASSOCIATION_WINDOW_MS = 2000
_DEFAULT_TRACK_TIMEOUT_MS = 5000
_DEFAULT_IOU_THRESHOLD = 0.05
_DEFAULT_MAX_ACTIVE_TRACKS = 8
_DEFAULT_MAX_COMPLETED_HISTORY = 32
_DEFAULT_MAX_EVENT_REFS = 16
_DEFAULT_MAX_EVIDENCE_REFS = 3


def _default_clock() -> str:
    from src.temporal.contract import _utc_now_iso

    return _utc_now_iso()


def compute_iou(
    a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]
) -> float:
    """IoU entre dos bbox (x1, y1, x2, y2). Devuelve 0.0 si no se intersectan."""
    x1a, y1a, x2a, y2a = a
    x1b, y1b, x2b, y2b = b
    xi1 = max(x1a, x1b)
    yi1 = max(y1a, y1b)
    xi2 = min(x2a, x2b)
    yi2 = min(y2a, y2b)
    inter_w = max(0, xi2 - xi1)
    inter_h = max(0, yi2 - yi1)
    inter = inter_w * inter_h
    area_a = max(0, x2a - x1a) * max(0, y2a - y1a)
    area_b = max(0, x2b - x1b) * max(0, y2b - y1b)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


class LocalTracker:
    """Tracker LOCAL determinista por cámara con actividad temporal acotada.

    El estado por cámara es independiente (sin memoria compartida entre
    cámaras). Todas las decisiones son deterministas bajo los mismos eventos
    y timestamps.
    """

    def __init__(
        self,
        association_window_ms: int = _DEFAULT_ASSOCIATION_WINDOW_MS,
        track_timeout_ms: int = _DEFAULT_TRACK_TIMEOUT_MS,
        iou_threshold: float = _DEFAULT_IOU_THRESHOLD,
        max_active_tracks: int = _DEFAULT_MAX_ACTIVE_TRACKS,
        max_completed_history: int = _DEFAULT_MAX_COMPLETED_HISTORY,
        max_event_refs: int = _DEFAULT_MAX_EVENT_REFS,
        max_evidence_refs: int = _DEFAULT_MAX_EVIDENCE_REFS,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        if association_window_ms < 0:
            raise TemporalConfigError("association_window_ms no puede ser negativo")
        if track_timeout_ms < 0:
            raise TemporalConfigError("track_timeout_ms no puede ser negativo")
        if not (0.0 <= iou_threshold <= 1.0):
            raise TemporalConfigError("iou_threshold debe estar entre 0 y 1")
        if max_active_tracks < 1:
            raise TemporalConfigError("max_active_tracks debe ser >= 1")
        if max_completed_history < 0:
            raise TemporalConfigError("max_completed_history no puede ser negativo")
        if max_event_refs < 1:
            raise TemporalConfigError("max_event_refs debe ser >= 1")
        if max_evidence_refs < 1 or max_evidence_refs > 3:
            raise TemporalConfigError("max_evidence_refs debe estar entre 1 y 3")

        self._association_window_ms = int(association_window_ms)
        self._track_timeout_ms = int(track_timeout_ms)
        self._iou_threshold = float(iou_threshold)
        self._max_active_tracks = int(max_active_tracks)
        self._max_completed_history = int(max_completed_history)
        self._max_event_refs = int(max_event_refs)
        self._max_evidence_refs = int(max_evidence_refs)
        self._clock = clock or _default_clock

        # Estado por cámara (aislado).
        self._cameras: Dict[str, Dict[str, Any]] = {}

        # Métricas acotadas (totales y por cámara).
        self._totals: Dict[str, int] = {
            "events_received": 0,
            "tracks_started": 0,
            "tracks_updated": 0,
            "tracks_ended": 0,
            "activities_started": 0,
            "activities_ended": 0,
            "association_misses": 0,
            "errors": 0,
        }

    # -- configuración y registro ------------------------------------------
    @property
    def association_window_ms(self) -> int:
        return self._association_window_ms

    @property
    def track_timeout_ms(self) -> int:
        return self._track_timeout_ms

    def register_camera(self, camera_id: str) -> str:
        camera_id = (camera_id or "").strip()
        if not camera_id:
            raise TemporalError("camera_id vacío")
        if camera_id not in self._cameras:
            self._cameras[camera_id] = self._new_camera_state()
        return camera_id

    def unregister_camera(self, camera_id: str) -> None:
        self._cameras.pop(camera_id, None)

    def _new_camera_state(self) -> Dict[str, Any]:
        return {
            "active_tracks": {},  # track_id -> LocalTrack
            "active_activities": {},  # track_id -> TemporalActivity
            "completed": {},  # track_id -> dict(ended_at, track, activity)
            "completion_order": [],  # track_ids en orden de cierre (bounded)
            "best_confidence": {},  # track_id -> confianza que fijó evidence "best"
            "seq_track": 0,
            "seq_activity": 0,
            "metrics": {
                "events_received": 0,
                "tracks_started": 0,
                "tracks_updated": 0,
                "tracks_ended": 0,
                "activities_started": 0,
                "activities_ended": 0,
                "association_misses": 0,
                "errors": 0,
            },
        }

    # -- procesamiento -------------------------------------------------------
    def ingest(
        self,
        event: Any,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[LocalTrack]:
        """Asocia un evento canónico a un track LOCAL y devuelve el track.

        `event` debe exponer: event_id, camera_id, timestamp (UTC Z),
        event_type, confidence (o None), evidence_ref (o None),
        inference_ref (o None). Compatible por duck-typing con InferenceEvent.
        """
        camera_id = (getattr(event, "camera_id", "") or "").strip()
        if not camera_id:
            raise TemporalValidationError("camera_id del evento es obligatorio")

        if camera_id not in self._cameras:
            self.register_camera(camera_id)

        state = self._cameras[camera_id]
        state["metrics"]["events_received"] += 1
        self._totals["events_received"] += 1

        try:
            track = self._associate(event, bbox, state)
            return track
        except Exception as exc:  # aislamiento por cámara
            state["metrics"]["errors"] += 1
            self._totals["errors"] += 1
            logger.error(
                "TEMPORAL_INGEST_ERROR camera_id=%s event=%s err=%s",
                camera_id,
                getattr(event, "event_id", "?"),
                exc,
            )
            return None

    def _associate(
        self, event: Any, bbox: Optional[Tuple[int, int, int, int]], state: Dict[str, Any]
    ) -> Optional[LocalTrack]:
        camera_id = event.camera_id
        timestamp = event.timestamp
        object_type = self._object_type_for(event)
        event_ref = getattr(event, "event_id", None)
        confidence = getattr(event, "confidence", None)
        evidence_ref = getattr(event, "evidence_ref", None)

        # 1) Cierre por timeout de tracks activos vencidos.
        self._close_expired(state, timestamp, camera_id)

        # 2) Asociación: candidato compatible dentro de la ventana temporal.
        candidate_id = self._find_candidate(
            state, object_type, timestamp, bbox, camera_id
        )

        if candidate_id is not None:
            track = self._update_track(
                state,
                candidate_id,
                timestamp,
                confidence,
                bbox,
                event_ref,
                evidence_ref,
                camera_id,
            )
            return track

        # 3) Sin candidato: cierre de tracks activos que superaron la ventana
        #    sin ser resucitados y creación de un NUEVO track.
        had_window_candidate = self._has_window_candidate(
            state, object_type, timestamp, camera_id
        )
        self._close_window_expired(state, timestamp, camera_id, object_type)

        if len(state["active_tracks"]) >= self._max_active_tracks:
            self._evict_oldest_active(state, timestamp, camera_id)

        if had_window_candidate:
            # Existía un candidato temporal dentro de la ventana que fue
            # rechazado por IoU/espacio: asociación perdida (metric).
            state["metrics"]["association_misses"] += 1
            self._totals["association_misses"] += 1

        track = self._start_track(
            state, camera_id, object_type, timestamp, confidence, bbox,
            event_ref, evidence_ref,
        )
        return track

    @staticmethod
    def _object_type_for(event: Any) -> str:
        """Clasifica el tipo de objeto desde el evento sin inventar semántica."""
        event_type = str(getattr(event, "event_type", "") or "").upper()
        if event_type == "PERSON_DETECTED":
            return "person"
        return "object"

    def _activity_type_for(self, object_type: str) -> str:
        if object_type == "person":
            return PERSON_PRESENCE
        return OBJECT_PRESENCE

    def _find_candidate(
        self,
        state: Dict[str, Any],
        object_type: str,
        timestamp: str,
        bbox: Optional[Tuple[int, int, int, int]],
        camera_id: str,
    ) -> Optional[str]:
        """Elige el mejor track activo compatible (determinista).

        Criterios: mismo tipo, dentro de `association_window_ms`, y si hay
        bbox, IoU >= umbral con la mayor IoU (espacial mínima). Sin bbox se
        usa el más reciente dentro de la ventana (temporal).
        """
        event_time = parse_iso_utc(timestamp)
        best_id: Optional[str] = None
        best_score = float("-inf")
        for track_id, track in state["active_tracks"].items():
            if track.object_type != object_type:
                continue
            if track.status == ENDED:
                continue
            gap_ms = int(
                (event_time - parse_iso_utc(track.last_seen_at)).total_seconds() * 1000.0
            )
            if gap_ms > self._association_window_ms:
                continue
            score = 0.0
            if bbox is not None and track.last_bbox is not None:
                iou = compute_iou(bbox, track.last_bbox)
                if iou < self._iou_threshold:
                    continue
                score = iou
            elif bbox is not None:
                # No hay bbox previo: aceptar por ventana temporal (score bajo
                # para no favorecerlo sobre asociaciones con IoU).
                score = 0.0
            else:
                score = -gap_ms / 1000.0  # más reciente gana (determinista)
            if score > best_score:
                best_score = score
                best_id = track_id
        return best_id

    def _update_track(
        self,
        state: Dict[str, Any],
        track_id: str,
        timestamp: str,
        confidence: Optional[float],
        bbox: Optional[Tuple[int, int, int, int]],
        event_ref: Optional[str],
        evidence_ref: Optional[str],
        camera_id: str,
    ) -> LocalTrack:
        track = state["active_tracks"][track_id]
        track.last_seen_at = timestamp
        track.status = ACTIVE
        track.event_count += 1
        if confidence is not None:
            track.confidence = (
                confidence
                if track.confidence is None
                else max(track.confidence, confidence)
            )
        if bbox is not None:
            track.last_bbox = bbox
        if event_ref:
            refs = list(track.event_refs)
            refs.append(event_ref)
            track.event_refs = tuple(refs[-self._max_event_refs:])
        self._update_evidence_refs(
            track.evidence_refs, state, track_id, evidence_ref, confidence
        )

        activity = state["active_activities"][track_id]
        activity.last_seen_at = timestamp
        activity.status = ACTIVE
        activity.event_count = track.event_count
        activity.confidence = track.confidence
        self._update_evidence_refs(
            activity.evidence_refs, state, track_id, evidence_ref, confidence,
            key_prefix="activity",
        )

        state["metrics"]["tracks_updated"] += 1
        self._totals["tracks_updated"] += 1
        return track

    def _start_track(
        self,
        state: Dict[str, Any],
        camera_id: str,
        object_type: str,
        timestamp: str,
        confidence: Optional[float],
        bbox: Optional[Tuple[int, int, int, int]],
        event_ref: Optional[str],
        evidence_ref: Optional[str],
    ) -> LocalTrack:
        state["seq_track"] += 1
        track_id = f"TRK-{camera_id}-{state['seq_track']:06d}"
        track = LocalTrack(
            track_id=track_id,
            camera_id=camera_id,
            object_type=object_type,
            started_at=timestamp,
            last_seen_at=timestamp,
            status=STARTED,
            event_count=1,
            confidence=confidence,
            last_bbox=bbox,
            event_refs=tuple([event_ref]) if event_ref else (),
        )
        self._update_evidence_refs(
            track.evidence_refs, state, track_id, evidence_ref, confidence
        )

        state["seq_activity"] += 1
        activity_id = f"ACT-{camera_id}-{state['seq_activity']:06d}"
        activity = TemporalActivity(
            activity_id=activity_id,
            track_id=track_id,
            source_id=camera_id,
            activity_type=self._activity_type_for(object_type),
            started_at=timestamp,
            last_seen_at=timestamp,
            status=STARTED,
            event_count=1,
            confidence=confidence,
        )
        self._update_evidence_refs(
            activity.evidence_refs, state, track_id, evidence_ref, confidence,
            key_prefix="activity",
        )

        state["active_tracks"][track_id] = track
        state["active_activities"][track_id] = activity
        state["metrics"]["tracks_started"] += 1
        state["metrics"]["activities_started"] += 1
        self._totals["tracks_started"] += 1
        self._totals["activities_started"] += 1
        return track

    def _update_evidence_refs(
        self,
        refs: Dict[str, Optional[str]],
        state: Dict[str, Any],
        track_id: str,
        evidence_ref: Optional[str],
        confidence: Optional[float],
        key_prefix: str = "track",
    ) -> None:
        """Estrategia first/latest/best (acotada, sin inventar paths).

        - first: primera evidence_reference observada (si existe).
        - latest: la más reciente.
        - best: la del evento con mayor confidence (empate: la primera).
        Solo se conservan references existentes; nunca se fabrican paths.
        La confianza de referencia se trackea por contrato (track vs activity)
        para no compartir estado entre ambos.
        """
        if not evidence_ref:
            return
        state_key = f"{key_prefix}:{track_id}"
        if refs["first"] is None:
            refs["first"] = evidence_ref
        refs["latest"] = evidence_ref
        best_conf = state["best_confidence"].get(state_key)
        if best_conf is None or (
            confidence is not None and confidence > best_conf
        ):
            state["best_confidence"][state_key] = confidence if confidence is not None else 0.0
            refs["best"] = evidence_ref
        elif best_conf == (confidence if confidence is not None else 0.0):
            # Empate: conservar la primera referencia con esa confianza.
            if refs["best"] is None:
                refs["best"] = evidence_ref

    def _close_expired(
        self, state: Dict[str, Any], now: str, camera_id: str
    ) -> None:
        now_dt = parse_iso_utc(now)
        for track_id in list(state["active_tracks"]):
            track = state["active_tracks"][track_id]
            gap_ms = int(
                (now_dt - parse_iso_utc(track.last_seen_at)).total_seconds() * 1000.0
            )
            if gap_ms > self._track_timeout_ms:
                self._end_track(state, track_id, now, camera_id)

    def _has_window_candidate(
        self,
        state: Dict[str, Any],
        object_type: str,
        timestamp: str,
        camera_id: str,
    ) -> bool:
        """True si existe un track activo del mismo tipo dentro de la ventana."""
        event_time = parse_iso_utc(timestamp)
        for track in state["active_tracks"].values():
            if track.object_type != object_type:
                continue
            if track.status == ENDED:
                continue
            gap_ms = int(
                (event_time - parse_iso_utc(track.last_seen_at)).total_seconds() * 1000.0
            )
            if gap_ms <= self._association_window_ms:
                return True
        return False

    def _close_window_expired(
        self, state: Dict[str, Any], now: str, camera_id: str, object_type: str
    ) -> None:
        """Cierra tracks activos del mismo tipo que superaron la ventana."""
        now_dt = parse_iso_utc(now)
        for track_id in list(state["active_tracks"]):
            track = state["active_tracks"][track_id]
            if track.object_type != object_type:
                continue
            gap_ms = int(
                (now_dt - parse_iso_utc(track.last_seen_at)).total_seconds() * 1000.0
            )
            if gap_ms > self._association_window_ms:
                self._end_track(state, track_id, now, camera_id)

    def _end_track(
        self, state: Dict[str, Any], track_id: str, now: str, camera_id: str
    ) -> None:
        track = state["active_tracks"].pop(track_id, None)
        activity = state["active_activities"].pop(track_id, None)
        if track is None:
            return
        track.status = ENDED
        track.last_seen_at = now
        if activity is not None:
            activity.status = ENDED
            activity.ended_at = now
            activity.last_seen_at = now
            activity.duration_ms = duration_ms(activity.started_at, now)
            state["metrics"]["activities_ended"] += 1
            self._totals["activities_ended"] += 1
        state["metrics"]["tracks_ended"] += 1
        self._totals["tracks_ended"] += 1
        # Historial acotado de completados.
        completed = state["completed"]
        completed[track_id] = {
            "ended_at": now,
            "track": track,
            "activity": activity,
        }
        state["completion_order"].append(track_id)
        while len(state["completion_order"]) > self._max_completed_history:
            oldest = state["completion_order"].pop(0)
            completed.pop(oldest, None)

    def _evict_oldest_active(
        self, state: Dict[str, Any], now: str, camera_id: str
    ) -> None:
        """Evicta el track activo más antiguo para respetar max_active_tracks."""
        if not state["active_tracks"]:
            return
        oldest_id = min(
            state["active_tracks"], key=lambda tid: state["active_tracks"][tid].started_at
        )
        self._end_track(state, oldest_id, now, camera_id)

    # -- consulta ------------------------------------------------------------
    def active_tracks(self, camera_id: str) -> List[LocalTrack]:
        state = self._camera_state(camera_id)
        return [state["active_tracks"][tid] for tid in sorted(state["active_tracks"])]

    def active_activities(self, camera_id: str) -> List[TemporalActivity]:
        state = self._camera_state(camera_id)
        return [
            state["active_activities"][tid] for tid in sorted(state["active_activities"])
        ]

    def completed(self, camera_id: str) -> List[LocalTrack]:
        state = self._camera_state(camera_id)
        return [state["completed"][tid]["track"] for tid in state["completion_order"]]

    def completed_activities(self, camera_id: str) -> List[TemporalActivity]:
        state = self._camera_state(camera_id)
        out = []
        for tid in state["completion_order"]:
            activity = state["completed"][tid]["activity"]
            if activity is not None:
                out.append(activity)
        return out

    def find_track(self, camera_id: str, track_id: str) -> Optional[LocalTrack]:
        state = self._camera_state(camera_id)
        if track_id in state["active_tracks"]:
            return state["active_tracks"][track_id]
        entry = state["completed"].get(track_id)
        return entry["track"] if entry else None

    def find_activity(self, camera_id: str, track_id: str) -> Optional[TemporalActivity]:
        state = self._camera_state(camera_id)
        if track_id in state["active_activities"]:
            return state["active_activities"][track_id]
        entry = state["completed"].get(track_id)
        return entry["activity"] if entry else None

    def active_count(self, camera_id: str) -> int:
        state = self._camera_state(camera_id)
        return len(state["active_tracks"])

    def completed_count(self, camera_id: str) -> int:
        state = self._camera_state(camera_id)
        return len(state["completed"])

    def metrics(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        if camera_id is not None:
            state = self._camera_state(camera_id)
            return {
                "camera_id": camera_id,
                **dict(state["metrics"]),
                "active_tracks": len(state["active_tracks"]),
                "completed_tracks": len(state["completed"]),
            }
        return dict(self._totals)

    def _camera_state(self, camera_id: str) -> Dict[str, Any]:
        if camera_id not in self._cameras:
            raise TemporalError(f"cámara no registrada: {camera_id}")
        return self._cameras[camera_id]

    def close(self) -> Dict[str, int]:
        """Cierra todos los tracks/actividades activos (ENDED) y limpia estado."""
        now = self._clock()
        for camera_id in list(self._cameras):
            state = self._cameras[camera_id]
            for track_id in list(state["active_tracks"]):
                self._end_track(state, track_id, now, camera_id)
        return dict(self._totals)


def build_tracker(config: Optional[Dict[str, Any]]) -> LocalTracker:
    """Construye LocalTracker desde el bloque `temporal` de la configuración.

    Fail-safe explícito: valores inválidos producen TemporalConfigError (nunca
    un fallback silencioso peligroso). Si el bloque está ausente se usan los
    defaults conservadores documentados.
    """
    if config is None:
        return LocalTracker()
    if not isinstance(config, dict):
        raise TemporalConfigError("Config de temporal inválida: no es dict")
    params = {}
    try:
        params["association_window_ms"] = int(
            config.get("association_window_ms", _DEFAULT_ASSOCIATION_WINDOW_MS)
        )
        params["track_timeout_ms"] = int(
            config.get("track_timeout_ms", _DEFAULT_TRACK_TIMEOUT_MS)
        )
        params["iou_threshold"] = float(config.get("iou_threshold", _DEFAULT_IOU_THRESHOLD))
        params["max_active_tracks"] = int(
            config.get("max_active_tracks", _DEFAULT_MAX_ACTIVE_TRACKS)
        )
        params["max_completed_history"] = int(
            config.get("max_completed_history", _DEFAULT_MAX_COMPLETED_HISTORY)
        )
        params["max_event_refs"] = int(
            config.get("max_event_refs", _DEFAULT_MAX_EVENT_REFS)
        )
        params["max_evidence_refs"] = int(
            config.get("max_evidence_refs", _DEFAULT_MAX_EVIDENCE_REFS)
        )
    except (TypeError, ValueError) as exc:
        raise TemporalConfigError(f"Config de temporal inválida: {exc}") from exc
    return LocalTracker(**params)