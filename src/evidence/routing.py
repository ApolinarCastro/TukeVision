"""Multistore evidence routing (MACRO-OC-02, Bloque B).

Every store resolves its own context: ``organization_id``, ``store_id``,
``camera_id`` and ``evidence_namespace``.  Evidence is written under each
store's namespace so that ``STORE_A_EVIDENCE != STORE_B_EVIDENCE`` and
review/retention/locks are never shared across stores.

This module does NOT create a second EvidenceStore.  It routes the existing
certified stores (:class:`src.evidence.persistent.PersistentEvidenceStore`
and :class:`src.evidence.clips.EvidenceClipAdapter`) to per-store roots and
routes review export to per-store JSONL targets.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Optional, Sequence

from src.domain.catalog import StoreCatalog
from src.evidence.clips import EvidenceClipAdapter
from src.evidence.persistent import PersistentEvidenceStore
from src.review.exporter import BoundedReviewExporter


class EvidenceRoutingError(Exception):
    """Invalid routing configuration or unresolved evidence context."""


@dataclass(frozen=True)
class StoreEvidenceContext:
    """Immutable per-store evidence context."""
    organization_id: str
    store_id: str
    store_name: str
    namespace: str
    root: Path

    def relative(self, reference: str) -> str:
        """POSIX relative reference under this store root (no escape)."""
        ref = PurePosixPath(str(reference).replace("\\", "/"))
        if ref.is_absolute() or ".." in ref.parts:
            raise EvidenceRoutingError("evidence reference escapes the store root")
        return ref.as_posix()


def _resolve_namespace(base: Path, namespace: str) -> Path:
    """Resolve a catalog namespace under the evidence base, rejecting escapes."""
    raw = str(namespace or "").strip().replace("\\", "/")
    if not raw:
        raise EvidenceRoutingError("evidence_namespace vacío para la tienda")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts:
        raise EvidenceRoutingError(f"evidence_namespace inválido: {raw!r}")
    return (base / path).resolve()


class StoreEvidenceRouter:
    """Routes evidence/JPEG/MP4/sidecar/review per store using catalog namespaces.

    Reuses the existing PersistentEvidenceStore / EvidenceClipAdapter /
    BoundedReviewExporter per store root.  Routing is resolved lazily and
    cached per store.
    """

    def __init__(
        self,
        catalog: StoreCatalog,
        *,
        evidence_base: str | Path,
        review_base: str | Path | None = None,
        evidence_config: Optional[Dict[str, Any]] = None,
        clip_config: Optional[Dict[str, Any]] = None,
        review_config: Optional[Dict[str, Any]] = None,
        id_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        if not isinstance(catalog, StoreCatalog):
            raise EvidenceRoutingError("router requiere un StoreCatalog")
        self._catalog = catalog
        self._evidence_base = Path(evidence_base).resolve()
        self._review_base = (
            Path(review_base).resolve() if review_base is not None else self._evidence_base
        )
        self._evidence_config = dict(evidence_config or {})
        self._clip_config = dict(clip_config or {})
        self._review_config = dict(review_config or {})
        self._id_factory = id_factory
        self._stores: Dict[str, PersistentEvidenceStore] = {}
        self._adapters: Dict[str, EvidenceClipAdapter] = {}
        self._review: Dict[str, BoundedReviewExporter] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------
    def context_for_store(self, store_id: str) -> StoreEvidenceContext:
        try:
            store = self._catalog.store(store_id)
        except Exception as exc:
            raise EvidenceRoutingError(
                f"tienda no encontrada para evidencia: {store_id}"
            ) from exc
        root = _resolve_namespace(self._evidence_base, store.evidence_namespace)
        return StoreEvidenceContext(
            organization_id=store.organization_id,
            store_id=store.store_id,
            store_name=store.store_name,
            namespace=store.evidence_namespace,
            root=root,
        )

    def context_for_camera(self, camera_id: str) -> StoreEvidenceContext:
        try:
            camera = self._catalog.camera(camera_id)
        except Exception as exc:
            raise EvidenceRoutingError(
                f"cámara no encontrada para evidencia: {camera_id}"
            ) from exc
        return self.context_for_store(camera.store_id)

    def root_for_store(self, store_id: str) -> Path:
        return self.context_for_store(store_id).root

    def review_target_for(self, store_id: str) -> Path:
        context = self.context_for_store(store_id)
        return self._review_base / "review" / context.store_id / "signal_review_records.jsonl"

    # ------------------------------------------------------------------
    # Persistent JPEG evidence (existing store, per-store root)
    # ------------------------------------------------------------------
    def persistent_store_for(self, camera_id: str) -> PersistentEvidenceStore:
        context = self.context_for_camera(camera_id)
        return self._persistent_by_store(context.store_id)

    def _persistent_by_store(self, store_id: str) -> PersistentEvidenceStore:
        with self._lock:
            store = self._stores.get(store_id)
            if store is not None:
                return store
            context = self.context_for_store(store_id)
            review_target = self.review_target_for(store_id)
            store = PersistentEvidenceStore(
                root=str(context.root),
                max_per_camera=int(self._evidence_config.get("max_per_camera", 32)),
                jpeg_quality=int(self._evidence_config.get("jpeg_quality", 90)),
                id_factory=self._id_factory,
                review_target=review_target,
                store_id=context.store_id,
                organization_id=context.organization_id,
            )
            self._stores[store_id] = store
            return store

    # ------------------------------------------------------------------
    # Temporal clips (existing adapter, per-store root + review target)
    # ------------------------------------------------------------------
    def clip_adapter_for(self, camera_id: str) -> EvidenceClipAdapter:
        context = self.context_for_camera(camera_id)
        return self._adapter_by_store(context.store_id)

    def _adapter_by_store(self, store_id: str) -> EvidenceClipAdapter:
        with self._lock:
            adapter = self._adapters.get(store_id)
            if adapter is not None:
                return adapter
            context = self.context_for_store(store_id)
            review_target = self.review_target_for(store_id)
            adapter = EvidenceClipAdapter(
                root=str(context.root),
                max_clips_per_camera=int(self._clip_config.get("max_clips_per_camera", 32)),
                max_clip_duration_seconds=float(
                    self._clip_config.get("max_clip_duration_seconds", 10.0)
                ),
                frame_rate=float(self._clip_config.get("buffer_fps", 5.0)),
                container=str(self._clip_config.get("container", "mp4")),
                codec=str(self._clip_config.get("codec", "mpeg4")),
                review_target=review_target,
                store_id=context.store_id,
                organization_id=context.organization_id,
            )
            self._adapters[store_id] = adapter
            return adapter

    # ------------------------------------------------------------------
    # Review export (existing exporter, per-store JSONL target)
    # ------------------------------------------------------------------
    def review_exporter(self) -> "RoutingReviewExporter":
        """Duck-typed BoundedReviewExporter routing records per store."""
        return RoutingReviewExporter(self)

    def clip_adapter(self, **kwargs: Any) -> "RoutingEvidenceClipAdapter":
        """Duck-typed EvidenceClipAdapter routing clips per store."""
        return RoutingEvidenceClipAdapter(self, **kwargs)

    def review_exporter_for(self, camera_id: str) -> BoundedReviewExporter:
        context = self.context_for_camera(camera_id)
        return self._review_by_store(context.store_id)

    def _review_by_store(self, store_id: str) -> BoundedReviewExporter:
        with self._lock:
            exporter = self._review.get(store_id)
            if exporter is not None:
                return exporter
            cfg = self._review_config
            exporter = BoundedReviewExporter(
                max_records_total=int(cfg.get("max_records_total", 8)),
                max_records_per_camera=int(cfg.get("max_records_per_camera", 2)),
                max_records_per_signal_type=int(cfg.get("max_records_per_signal_type", 4)),
                max_records_per_rule=int(cfg.get("max_records_per_rule", 4)),
                max_candidates=int(cfg.get("max_candidates", 64)),
            )
            self._review[store_id] = exporter
            return exporter

    # ------------------------------------------------------------------
    # Operator evidence opening (exact artifact within the store root)
    # ------------------------------------------------------------------
    def resolve_evidence(self, reference: str, camera_id: str) -> Optional[str]:
        """Absolute path of an exact evidence artifact in the camera's store."""
        if not reference:
            return None
        context = self.context_for_camera(camera_id)
        try:
            relative = context.relative(reference)
        except EvidenceRoutingError:
            return None
        candidate = (context.root / relative).resolve()
        try:
            candidate.relative_to(context.root)
        except ValueError:
            return None
        return str(candidate) if candidate.is_file() else None

    def routing_summary(self) -> Dict[str, Any]:
        """Auditable routing map without secrets (camera -> store namespace)."""
        return {
            "organization_id": self._catalog.organization.organization_id,
            "routing": self._catalog.evidence_routing(),
            "stores": [
                {
                    "store_id": store.store_id,
                    "root": str(self.context_for_store(store.store_id).root),
                    "review_target": str(self.review_target_for(store.store_id)),
                }
                for store in self._catalog.stores()
            ],
        }


class RoutingEvidenceClipAdapter:
    """Duck-typed EvidenceClipAdapter that routes per camera to its store.

    The TemporalClipCoordinator only calls ``create_clip``, ``unavailable``,
    ``enforce_retention`` and ``retention_status``; this wrapper dispatches
    each to the existing per-store EvidenceClipAdapter.
    """

    def __init__(
        self,
        router: StoreEvidenceRouter,
        *,
        max_clip_duration_seconds: float = 10.0,
    ) -> None:
        self._router = router
        self.max_clip_duration_seconds = float(max_clip_duration_seconds)

    def _adapter(self, camera_id: str) -> EvidenceClipAdapter:
        return self._router.clip_adapter_for(camera_id)

    def create_clip(self, **kwargs: Any) -> Dict[str, Any]:
        camera_id = str(kwargs.get("camera_id") or "")
        return self._adapter(camera_id).create_clip(**kwargs)

    def unavailable(self, **kwargs: Any) -> Dict[str, Any]:
        camera_id = str(kwargs.get("camera_id") or "")
        return self._adapter(camera_id).unavailable(**kwargs)

    def enforce_retention(self, camera_id: str) -> str:
        return self._adapter(camera_id).enforce_retention(camera_id)

    def retention_status(self, camera_id: str) -> str:
        return self._adapter(camera_id).retention_status(camera_id)


class RoutingReviewExporter:
    """Duck-typed BoundedReviewExporter routing records to per-store targets.

    Each store owns its exporter and its JSONL review file, so a review of
    Store A can never lock, retain or mutate Store B review/evidence state.
    """

    def __init__(self, router: StoreEvidenceRouter) -> None:
        self._router = router

    def _exporter(self, camera_id: str) -> BoundedReviewExporter:
        return self._router.review_exporter_for(camera_id)

    def offer(self, record: Any) -> bool:
        camera_id = str(getattr(record, "camera_id", "") or "")
        return self._exporter(camera_id).offer(record)

    def select(self) -> tuple:
        selected = []
        for exporter in self._router_exports():
            selected.extend(exporter.select())
        return tuple(selected)

    def candidates(self) -> tuple:
        candidates = []
        for exporter in self._router_exports():
            candidates.extend(exporter.candidates())
        return tuple(candidates)

    def stats(self) -> Dict[str, Any]:
        stores = {}
        totals = {"total_available": 0, "selected": 0, "duplicates": 0}
        for store_id, exporter in self._router_exports_by_store().items():
            stats = exporter.stats()
            stores[store_id] = stats
            totals["total_available"] += int(stats.get("total_available", 0))
            totals["selected"] += int(stats.get("selected", 0))
            totals["duplicates"] += int(stats.get("duplicates", 0))
        return {"stores": stores, **totals}

    def export_jsonl(self, target: Any = None) -> Dict[str, Any]:
        """Export review records to JSONL targets.

        When ``target`` is provided (the runtime always passes its own store
        target) only that store is written, so concurrent per-store workers
        never open or rewrite another store's review file.  Without a target
        every store is exported (aggregate use by tests/operators).
        """
        if target is not None:
            wanted = str(Path(target))
            for store_id in self._router._catalog.store_ids():
                store_target = self._router.review_target_for(store_id)
                if wanted == str(store_target):
                    exporter = self._router._review_by_store(store_id)
                    return {store_id: exporter.export_jsonl(store_target)}
        results = {}
        for store_id, exporter in self._router_exports_by_store().items():
            store_target = self._router.review_target_for(store_id)
            results[store_id] = exporter.export_jsonl(store_target)
        return results

    def _router_exports(self) -> Sequence[BoundedReviewExporter]:
        return tuple(self._router_exports_by_store().values())

    def _router_exports_by_store(self) -> Dict[str, BoundedReviewExporter]:
        return {store.store_id: self._router._review_by_store(store.store_id)
                for store in self._router._catalog.stores()}


class RoutingEvidenceStore:
    """Duck-typed PersistentEvidenceStore routing per camera to its store.

    Exposes the same interface used by AdvanceChain: ``persist_selected``,
    ``link``, ``resolve``, ``verify``, ``enforce_retention``,
    ``retention_status``.  Each store uses the existing persistent store
    rooted at its own namespace.
    """

    def __init__(self, router: StoreEvidenceRouter) -> None:
        self._router = router

    def _store(self, camera_id: str) -> PersistentEvidenceStore:
        return self._router.persistent_store_for(camera_id)

    def persist_selected(
        self,
        frame: Any,
        *,
        camera_id: str,
        timestamp: str,
        producer: str,
        observation_ref: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        return self._store(camera_id).persist_selected(
            frame,
            camera_id=camera_id,
            timestamp=timestamp,
            producer=producer,
            observation_ref=observation_ref,
        )

    def link(
        self,
        evidence_ref: str,
        *,
        inference_ref: Optional[str] = None,
        event_ref: Optional[str] = None,
        track_ref: Optional[str] = None,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not camera_id:
            raise EvidenceRoutingError("link requiere camera_id para resolver la tienda")
        return self._store(camera_id).link(
            evidence_ref,
            inference_ref=inference_ref,
            event_ref=event_ref,
            track_ref=track_ref,
        )

    def resolve(self, evidence_ref: str, camera_id: Optional[str] = None) -> Path:
        if not camera_id:
            raise EvidenceRoutingError("resolve requiere camera_id para resolver la tienda")
        return self._store(camera_id).resolve(evidence_ref)

    def verify(self, evidence_ref: str, camera_id: Optional[str] = None) -> bool:
        if not camera_id:
            raise EvidenceRoutingError("verify requiere camera_id para resolver la tienda")
        return self._store(camera_id).verify(evidence_ref)

    def enforce_retention(self, camera_id: str) -> str:
        return self._store(camera_id).enforce_retention(camera_id)

    def retention_status(self, camera_id: str) -> str:
        return self._store(camera_id).retention_status(camera_id)