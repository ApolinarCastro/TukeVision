"""Real per-store edge runtime (MACRO-OC-02, Bloque D).

Each store runs its OWN SourceManager + OperationalPipeline +
RuntimeQw04Integration + SystemHealthSampler in its own worker thread, with
per-store evidence/review isolation via the StoreEvidenceRouter.  One store
failing (start, stop, source failure) never stops another store.

The existing EdgeCaptureService (OC-18 placeholder) delegates to a real
StoreEdgeRuntime when one is attached.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.app.advance_chain import AdvanceChain
from src.app.operational_pipeline import OperationalPipeline
from src.app.runtime_qw04 import RuntimeQw04Integration
from src.app.runtime_wiring import RuntimeWiring, _zone_configs_from_config
from src.capture.source_manager import SourceManager
from src.domain.catalog import StoreCatalog
from src.evidence.routing import (
    RoutingEvidenceClipAdapter,
    RoutingEvidenceStore,
    StoreEvidenceRouter,
)
from src.observability.system_health import SystemHealthSampler

logger = logging.getLogger("tukevision.edge_runtime")


class EdgeRuntimeError(Exception):
    """Operación inválida del runtime de edge."""


OnResult = Callable[[str, str, Dict[str, Any], Dict[str, Any]], None]


class StoreEdgeRuntime:
    """Composed capture->pipeline->qw04->health runtime for ONE store."""

    def __init__(
        self,
        *,
        store_id: str,
        config: Dict[str, Any],
        manager: SourceManager,
        pipeline: OperationalPipeline,
        qw04: RuntimeQw04Integration,
        health: SystemHealthSampler,
        evidence_root: str,
        review_target: str,
        on_result: Optional[OnResult] = None,
    ) -> None:
        self.store_id = store_id
        self._config = config
        self._manager = manager
        self._pipeline = pipeline
        self._qw04 = qw04
        self._health = health
        self.evidence_root = evidence_root
        self.review_target = review_target
        self._on_result = on_result
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._started_at = ""
        self._processed = 0

    @classmethod
    def build(
        cls,
        config: Dict[str, Any],
        catalog: StoreCatalog,
        *,
        store_id: str,
        source_factory: Optional[Callable[..., object]] = None,
        credential_resolver: Optional[Callable[[str], tuple]] = None,
        router: Optional[StoreEvidenceRouter] = None,
        on_result: Optional[OnResult] = None,
        evidence_base: str = "",
        review_base: str = "",
        sample_interval_seconds: float = 3.0,
    ) -> "StoreEdgeRuntime":
        store = catalog.store(store_id)
        entries = [
            entry for entry in catalog.camera_descriptors(
                credential_resolver=credential_resolver
            )
            if entry.store_id == store_id
        ]
        if not entries:
            raise EdgeRuntimeError(f"tienda sin cámaras habilitadas: {store_id}")

        manager = SourceManager(source_factory=source_factory)
        for entry in entries:
            manager.register_source(entry.descriptor)

        if router is None:
            base = evidence_base or "data/runtime_evidence"
            router = StoreEvidenceRouter(
                catalog,
                evidence_base=base,
                review_base=review_base or base,
                evidence_config=config.get("evidence", {}),
                clip_config=config.get("clips", {}),
                review_config=config.get("review_export", {}),
            )
        evidence_root = str(router.root_for_store(store_id))
        review_target = str(router.review_target_for(store_id))

        evidence_store = RoutingEvidenceStore(router)
        chain = AdvanceChain.build(
            config, manager, evidence_store=evidence_store
        )
        pipeline = OperationalPipeline(config, manager, chain=chain)
        qw04 = RuntimeQw04Integration.from_config(
            config,
            evidence_root=evidence_root,
            review_target=review_target,
            router=router,
        )
        camera_ids = tuple(entry.camera_id for entry in entries)
        health = SystemHealthSampler(
            manager,
            camera_ids,
            sample_interval_seconds=sample_interval_seconds,
            disk_path=str(Path(evidence_root)),
            catalog=catalog,
        )
        return cls(
            store_id=store_id,
            config=config,
            manager=manager,
            pipeline=pipeline,
            qw04=qw04,
            health=health,
            evidence_root=evidence_root,
            review_target=review_target,
            on_result=on_result,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            raise EdgeRuntimeError(f"tienda ya en ejecución: {self.store_id}")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"tukevision-edge-{self.store_id}",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info("EDGE_STORE_STARTED store_id=%s", self.store_id)

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=15)
        self._running = False
        logger.info("EDGE_STORE_STOPPED store_id=%s", self.store_id)

    def restart(self) -> None:
        was_running = self._running
        if was_running:
            self.stop()
        self.start()

    def close(self) -> None:
        self.stop()
        try:
            self._qw04.close()
        except Exception as exc:
            logger.error("EDGE_STORE_QW04_CLOSE_FAILED store_id=%s error=%s",
                         self.store_id, type(exc).__name__)
        try:
            self._pipeline.close()
        except Exception as exc:
            logger.error("EDGE_STORE_PIPELINE_CLOSE_FAILED store_id=%s error=%s",
                         self.store_id, type(exc).__name__)
        logger.info("EDGE_STORE_CLOSED store_id=%s", self.store_id)

    def _run(self) -> None:
        def on_result(camera_id: str, snapshot: Dict[str, Any], result: Dict[str, Any]) -> None:
            try:
                self._qw04.ingest(
                    camera_id,
                    float(snapshot.get("timestamp") or 0.0),
                    snapshot.get("frame"),
                    int(snapshot.get("frame_index") or -1),
                    result,
                )
            except Exception as exc:
                logger.error("EDGE_STORE_QW04_INGEST_FAILED store_id=%s camera_id=%s error=%s",
                             self.store_id, camera_id, type(exc).__name__)
            if self._on_result is not None:
                self._on_result(camera_id, snapshot, result)

        try:
            summary = self._pipeline.run(self._stop.is_set, on_result)
            self._processed = int(summary.frames_processed)
        except Exception as exc:
            logger.error("EDGE_STORE_RUN_FAILED store_id=%s error=%s",
                         self.store_id, type(exc).__name__)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def store_summary(self) -> Dict[str, Any]:
        running = self.running
        health = None
        try:
            health = self._health.snapshot(runtime_running=running)
        except Exception as exc:
            logger.error("EDGE_STORE_HEALTH_FAILED store_id=%s error=%s",
                         self.store_id, type(exc).__name__)
        qw04 = {}
        try:
            qw04 = self._qw04.summary()
        except Exception as exc:
            logger.error("EDGE_STORE_QW04_SUMMARY_FAILED store_id=%s error=%s",
                         self.store_id, type(exc).__name__)
        return {
            "store_id": self.store_id,
            "running": running,
            "processed_frames": self._processed,
            "system_health": health,
            "qw04": qw04,
            "evidence_root": self.evidence_root,
            "review_target": self.review_target,
        }


class EdgeRuntimeManager:
    """Lifecycle manager for one StoreEdgeRuntime per store (multistore).

    Per-store isolation: start/stop/restart of one store never affects
    another store's worker.  All stores share the same evidence router so
    namespaces and routing stay consistent, but each store owns its roots,
    review targets and locks.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        catalog: StoreCatalog,
        *,
        source_factory: Optional[Callable[..., object]] = None,
        credential_resolver: Optional[Callable[[str], tuple]] = None,
        evidence_base: str = "",
        review_base: str = "",
        on_result: Optional[OnResult] = None,
        sample_interval_seconds: float = 3.0,
        auto_start: bool = False,
    ) -> None:
        self._config = config
        self._catalog = catalog
        self._source_factory = source_factory
        self._credential_resolver = credential_resolver
        base = evidence_base or "data/runtime_evidence"
        self.router = StoreEvidenceRouter(
            catalog,
            evidence_base=base,
            review_base=review_base or base,
            evidence_config=config.get("evidence", {}),
            clip_config=config.get("clips", {}),
            review_config=config.get("review_export", {}),
        )
        self._on_result = on_result
        self._sample_interval_seconds = sample_interval_seconds
        self._runtimes: Dict[str, StoreEdgeRuntime] = {}
        self._wirings: Dict[str, RuntimeWiring] = {}
        self._lock = threading.RLock()
        if auto_start:
            self.start_all()

    def _require_store(self, store_id: str) -> StoreEdgeRuntime:
        runtime = self._runtimes.get(store_id)
        if runtime is not None and runtime.running:
            return runtime
        if runtime is not None:
            # Stale runtime whose first run already closed the pipeline (stop,
            # worker failure or restart). Release it and build a fresh
            # manager/pipeline/QW-04/health stack for a clean restart.
            try:
                runtime.close()
            except Exception as exc:
                logger.error("EDGE_RUNTIME_STALE_CLOSE_FAILED store_id=%s error=%s",
                             store_id, type(exc).__name__)
            self._runtimes.pop(store_id, None)
        store = self._catalog.store(store_id)
        wiring = self._wirings.get(store_id)
        if wiring is None:
            wiring = RuntimeWiring(
                organization_id=store.organization_id,
                store_id=store_id,
                zone_configs=_zone_configs_from_config(self._config),
                dataset_root=str(Path(self._config.get("learning", {}).get(
                    "dataset_root", "data/learning/datasets"
                ))),
                policy_root=str(Path(self._config.get("learning", {}).get(
                    "policy_root", "data/learning/policies"
                ))),
            )
            self._wirings[store_id] = wiring
        on_result = self._make_on_result(store_id, wiring)
        runtime = StoreEdgeRuntime.build(
            self._config,
            self._catalog,
            store_id=store_id,
            source_factory=self._source_factory,
            credential_resolver=self._credential_resolver,
            router=self.router,
            on_result=on_result,
            sample_interval_seconds=self._sample_interval_seconds,
        )
        self._runtimes[store_id] = runtime
        return runtime

    def _make_on_result(
        self, store_id: str, wiring: RuntimeWiring
    ) -> OnResult:
        def on_result(camera_id: str, snapshot: Dict[str, Any], result: Dict[str, Any]) -> None:
            wiring.ingest_result(camera_id, snapshot, result)
            if self._on_result is not None:
                self._on_result(store_id, camera_id, snapshot, result)
        return on_result

    def store_ids(self) -> List[str]:
        return self._catalog.store_ids()

    def prepare_store(self, store_id: str) -> StoreEdgeRuntime:
        """Build or return the unstarted runtime used by deployment wiring."""
        with self._lock:
            return self._require_store(store_id)

    def start_store(self, store_id: str) -> StoreEdgeRuntime:
        with self._lock:
            runtime = self._require_store(store_id)
            if runtime.running:
                return runtime
            runtime.start()
            return runtime

    def stop_store(self, store_id: str) -> None:
        with self._lock:
            runtime = self._runtimes.get(store_id)
            if runtime is not None:
                runtime.stop()

    def restart_store(self, store_id: str) -> StoreEdgeRuntime:
        with self._lock:
            runtime = self._runtimes.get(store_id)
            if runtime is not None:
                try:
                    runtime.close()
                except Exception as exc:
                    logger.error("EDGE_RUNTIME_RESTART_CLOSE_FAILED store_id=%s error=%s",
                                 store_id, type(exc).__name__)
                self._runtimes.pop(store_id, None)
            return self.start_store(store_id)

    def start_all(self) -> List[str]:
        started = []
        for store_id in [store.store_id for store in self._catalog.active_stores()]:
            self.start_store(store_id)
            started.append(store_id)
        return started

    def stop_all(self) -> None:
        for store_id in tuple(self._runtimes):
            self.stop_store(store_id)

    def close(self) -> None:
        for store_id in tuple(self._runtimes):
            runtime = self._runtimes.pop(store_id)
            try:
                runtime.close()
            except Exception as exc:
                logger.error("EDGE_RUNTIME_CLOSE_FAILED store_id=%s error=%s",
                             store_id, type(exc).__name__)

    def runtime(self, store_id: str) -> Optional[StoreEdgeRuntime]:
        return self._runtimes.get(store_id)

    def wiring(self, store_id: str) -> Optional[RuntimeWiring]:
        return self._wirings.get(store_id)

    def summary(self) -> Dict[str, Any]:
        return {
            "stores": [
                self._runtimes[store_id].store_summary()
                for store_id in self._catalog.store_ids()
                if store_id in self._runtimes
            ],
            "wiring": [
                self._wirings[store_id].summary()
                for store_id in self._catalog.store_ids()
                if store_id in self._wirings
            ],
            "routing": self.router.routing_summary(),
        }
