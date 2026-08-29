"""Adaptador/wiring mínimo de la cadena 2.2 (LOOP-0018T, C1).

Composición de las capas certificadas del PRODUCT ADVANCE usando
EXCLUSIVAMENTE sus contratos existentes (ninguna capa se reimplementa):

    SourceManager -> ActivityLayer -> SelectiveInferencePipeline -> LocalTracker

Puentes utilizados:
  - ActivityLayer.register_from_source_manager(source_manager)
  - SelectiveInferencePipeline.register_from_source_manager(source_manager)
  - LocalTracker.register_camera(camera_id)  (composición manual: LocalTracker
    no expone register_from_source_manager; el contrato es por cámara)

Este módulo NO abre cámaras, NO ejecuta YOLO por sí mismo y NO almacena
frames: delega en el pipeline selectivo configurado (deterministic o yolo)
y en la política de observación. Su único propósito es dar un llamador en
runtime a la composición que LOOP-0018S marcó como H1 (sin llamador).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pathlib import PurePosixPath
from collections import deque
import time

from src.observations.activity import ActivityLayer

logger = logging.getLogger("tukevision.advance_chain")


class AdvanceChainError(Exception):
    """Error de composición de la cadena 2.2."""


class AdvanceChain:
    """Composición de SourceManager -> ActivityLayer -> SelectiveInference -> LocalTracker.

    Uso típico:

        chain = AdvanceChain.build(config, source_manager)
        chain.register_from_source_manager()
        # por cada frame por cámara (desde SourceManager.snapshot):
        result = chain.feed(camera_id, frame_index, fps, frame, metadata=metadata)
        ...
        summary = chain.summary()
        chain.close()
    """

    def __init__(
        self,
        source_manager: Any,
        activity_layer: ActivityLayer,
        selective_pipeline: Any,
        tracker: Any,
        evidence_store: Any = None,
        correlator: Any = None,
        behavior_engine: Any = None,
    ) -> None:
        self._source_manager = source_manager
        self._activity = activity_layer
        self._selective = selective_pipeline
        self._tracker = tracker
        self._evidence_store = evidence_store
        self._correlator = correlator
        self._behavior = behavior_engine
        self._closed = False
        
        # SLICE 1: Frame Buffer & Bundle Selector
        self._frame_buffer = {}
        from src.evidence.bundle import EvidenceBundleStore, EvidenceSelector
        self._bundle_store = None
        self._bundle_selector = None
        if self._evidence_store is not None:
            self._bundle_store = EvidenceBundleStore(self._evidence_store)
            self._bundle_selector = EvidenceSelector(self._bundle_store)

    # ------------------------------------------------------------------
    # Fábrica config-driven
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        config: Dict[str, Any],
        source_manager: Any,
        evidence_store: Any = None,
        review_target: Any = None,
    ) -> "AdvanceChain":
        """Construye la cadena desde la configuración del producto.

        - `config`: dict completo del producto (debe contener los bloques
          `observation`, `inference` y `temporal` según los contratos).
        - `source_manager`: instancia de SourceManager (o duck-typed que
          exponga list_sources()/health()) ya registrada con sus cámaras.

        Fail-safe: config inválida produce AdvanceChainError explícito
        (nunca silencio peligroso).
        """
        if not isinstance(config, dict):
            raise AdvanceChainError("Config de AdvanceChain inválida: no es dict")

        from src.inference.selective import build_pipeline
        from src.temporal.tracker import build_tracker

        inference_cfg = config.get("inference")
        if not isinstance(inference_cfg, dict):
            raise AdvanceChainError(
                "AdvanceChain requiere config.inference (dict con backend)"
            )

        activity_layer = ActivityLayer(config=config)
        selective_pipeline = build_pipeline(inference_cfg)
        tracker = build_tracker(config.get("temporal"))
        from src.evidence.persistent import PersistentEvidenceStore

        if evidence_store is None:
            evidence_store = PersistentEvidenceStore.from_config(
                config, review_target=review_target
            )
        from src.correlation.correlator import build_correlator
        correlator = build_correlator(config)
        from src.behavior import build_behavior_engine
        behavior_engine = build_behavior_engine(config)

        return cls(
            source_manager=source_manager,
            activity_layer=activity_layer,
            selective_pipeline=selective_pipeline,
            tracker=tracker,
            evidence_store=evidence_store,
            correlator=correlator,
            behavior_engine=behavior_engine,
        )

    # ------------------------------------------------------------------
    # Composición de cámaras
    # ------------------------------------------------------------------
    def register_from_source_manager(self) -> List[str]:
        """Registra las cámaras del SourceManager en las 3 capas.

        Cierra el gap H1 de LOOP-0018S: da llamador en runtime a los
        `register_from_source_manager` existentes (Activity + Selective) y
        compone LocalTracker por cámara (register_camera).
        """
        registered: List[str] = []
        sources = list(self._source_manager.list_sources())
        for item in sources:
            camera_id = item.get("camera_id")
            if camera_id:
                registered.append(camera_id)
        self._activity.register_from_source_manager(self._source_manager)
        self._selective.register_from_source_manager(self._source_manager)
        for camera_id in registered:
            self._tracker.register_camera(camera_id)
            if camera_id not in self._frame_buffer:
                self._frame_buffer[camera_id] = deque(maxlen=30)  # 30 frames buffer
        logger.info("ADVANCE_CHAIN_CAMERAS registered=%d", len(registered))
        return registered

    def list_cameras(self) -> List[str]:
        return sorted(set(self._activity.list_cameras()))

    # ------------------------------------------------------------------
    # Flujo de un frame (cadena 2.2)
    # ------------------------------------------------------------------
    def feed(
        self,
        camera_id: str,
        frame_index: int,
        fps: float,
        frame: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Ingiere un frame a través de toda la cadena 2.2.

        ActivityLayer.feed -> (observación si el sampling la selecciona)
        -> SelectiveInference.feed (observation_ref si existe) -> evento
        -> LocalTracker.ingest(evento) -> track.

        Devuelve un dict JSON-serializable con lo producido por cada capa
        (obs/event/track pueden ser None por política o falta de detección).
        """
        if self._closed:
            raise AdvanceChainError("AdvanceChain cerrado")

        observation = self._activity.feed(
            camera_id=camera_id,
            frame_index=frame_index,
            metadata=metadata,
            frame=frame,
        )

        # SLICE 1: Buffering frame
        now_ts = time.time()
        # Intentamos usar el timestamp real de la observación si es posible
        if observation is not None and hasattr(observation, "timestamp"):
            try:
                from datetime import datetime, timezone
                obs_ts = datetime.fromisoformat(observation.timestamp.replace("Z", "+00:00")).timestamp()
                now_ts = obs_ts
            except Exception:
                pass
        self._frame_buffer[camera_id].append((now_ts, frame))

        observation_ref = None
        evidence = None
        evidence_ref = None
        if observation is not None:
            observation_ref = getattr(observation, "observation_id", None)
            if self._evidence_store is not None:
                evidence = self._evidence_store.persist_selected(
                    frame,
                    camera_id=camera_id,
                    timestamp=getattr(observation, "timestamp", ""),
                    producer="activity-policy",
                    observation_ref=observation_ref,
                )
                if evidence is not None:
                    evidence_ref = evidence["relative_path"]
            elif self._bundle_selector is not None:
                bundle = self._bundle_selector.select(
                    camera_id=camera_id,
                    frames_buffer=list(self._frame_buffer[camera_id]),
                    detections=[],
                    tracks=[],
                    target_timestamp=now_ts
                )
                if bundle is not None:
                    evidence_ref = PurePosixPath(bundle.key_frame_path).parent.as_posix() if bundle.key_frame_path else bundle.bundle_id
                    evidence = {
                        "relative_path": evidence_ref,
                        "bundle": bundle,
                        "event_ref": None,
                        "track_ref": None,
                        "inference_ref": None,
                        "sha256": bundle.hashes.get("key_frame.jpg", "")
                    }

        event = self._selective.feed(
            camera_id=camera_id,
            frame_index=frame_index,
            fps=fps,
            frame=frame,
            observation_ref=observation_ref,
            evidence_ref=evidence_ref,
            metadata=metadata,
        )

        track = None
        temporal_activity = None
        correlation = None
        behavior = None
        if event is not None:
            primary_bbox = (getattr(event, "metadata", None) or {}).get(
                "primary_bbox"
            )
            bbox = None
            if isinstance(primary_bbox, (list, tuple)) and len(primary_bbox) == 4:
                bbox = tuple(int(value) for value in primary_bbox)
            track = self._tracker.ingest(event, bbox=bbox)
            temporal_activity = next(
                (
                    activity
                    for activity in self._tracker.active_activities(camera_id)
                    if activity.track_id == getattr(track, "track_id", None)
                ),
                None,
            )
            if evidence is not None:
                if self._evidence_store is not None:
                    linked = self._evidence_store.link(
                        evidence_ref,
                        inference_ref=getattr(event, "inference_ref", None),
                        event_ref=getattr(event, "event_id", None),
                        track_ref=getattr(track, "track_id", None),
                        camera_id=camera_id,
                    )
                    if linked:
                        evidence = linked
                if evidence is not None and isinstance(evidence, dict):
                    evidence["inference_ref"] = getattr(event, "inference_ref", None)
                    evidence["event_ref"] = getattr(event, "event_id", None)
                    evidence["track_ref"] = getattr(track, "track_id", None)
            if self._correlator is not None:
                correlation = self._correlator.ingest(
                    track, activity=temporal_activity, metadata=metadata
                )
            if self._behavior is not None:
                behavior = self._behavior.evaluate(
                    observation=observation, event=event, track=track,
                    activity=temporal_activity,
                    trajectory=getattr(correlation, "trajectory", None),
                    metadata=metadata,
                )

        return {
            "camera_id": camera_id,
            "frame_index": frame_index,
            "observation": observation,
            "event": event,
            "track": track,
            "temporal_activity": temporal_activity,
            "correlation": correlation,
            "behavior": behavior,
            "evidence": evidence,
        }

    # ------------------------------------------------------------------
    # Estado / auditoría
    # ------------------------------------------------------------------
    def summary(self) -> Dict[str, Any]:
        """Estado auditable agregado de la cadena (sin secretos ni frames)."""
        summary = {
            "cameras": self.list_cameras(),
            "activity": self._activity.stats(),
            "inference": {
                "metrics": self._selective.metrics(),
                "totals": self._selective.totals(),
            },
            "temporal": self._tracker.metrics(),
        }
        if self._correlator is not None:
            summary["correlation"] = self._correlator.metrics()
        if self._behavior is not None:
            summary["behavior"] = self._behavior.metrics()
        return summary

    # ------------------------------------------------------------------
    # Shutdown limpio
    # ------------------------------------------------------------------
    def close(self) -> Dict[str, Any]:
        """Cierra en orden inverso (tracker -> selective -> activity)."""
        if self._closed:
            return {"already_closed": True}
        self._closed = True
        if self._correlator is not None:
            self._correlator.close()
        behavior_totals = self._behavior.close() if self._behavior is not None else None
        tracker_totals = self._tracker.close()
        selective_totals = self._selective.close()
        activity_stats = self._activity.close()
        logger.info(
            "ADVANCE_CHAIN_CLOSED tracks=%s events=%s",
            tracker_totals,
            selective_totals,
        )
        return {
            "tracker": tracker_totals,
            "selective": selective_totals,
            "activity": activity_stats,
            "behavior": behavior_totals,
        }
