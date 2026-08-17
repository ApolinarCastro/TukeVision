"""Operational SourceManager -> AdvanceChain runtime adapter."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.app.advance_chain import AdvanceChain


@dataclass(frozen=True)
class OperationalSummary:
    frames_processed: int
    final_status: str
    chain: Dict[str, Any]


class OperationalPipeline:
    """Poll distinct SourceManager snapshots and feed the certified chain."""

    def __init__(
        self,
        config: Dict[str, Any],
        source_manager: Any,
        chain: Optional[AdvanceChain] = None,
        poll_interval_s: float = 0.01,
    ) -> None:
        self._manager = source_manager
        self._chain = chain or AdvanceChain.build(config, source_manager)
        self._poll_interval_s = max(0.001, float(poll_interval_s))
        self._last_frame: Dict[str, int] = {}
        self._closed = False

    def start(self) -> None:
        for camera_id in self._chain.register_from_source_manager():
            self._manager.start(camera_id)

    def process_available(self, camera_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self._manager.snapshot(camera_id)
        if not snapshot:
            return None
        frame_index = int(snapshot["frame_index"])
        if frame_index <= self._last_frame.get(camera_id, -1):
            return None
        self._last_frame[camera_id] = frame_index
        metadata = {
            "source_state": snapshot.get("state", "OPEN"),
            "resolution": snapshot.get("resolution", ""),
        }
        return self._chain.feed(
            camera_id=camera_id,
            frame_index=frame_index,
            fps=float(snapshot.get("fps", 0.0) or 0.0),
            frame=snapshot["frame"],
            metadata=metadata,
        )

    def run(
        self,
        stop_requested: Callable[[], bool],
        on_result: Optional[Callable[[str, dict, Dict[str, Any]], None]] = None,
    ) -> OperationalSummary:
        processed = 0
        self.start()
        try:
            while not stop_requested():
                active = False
                for item in self._manager.list_sources():
                    camera_id = item["camera_id"]
                    snapshot = self._manager.snapshot(camera_id)
                    result = self.process_available(camera_id)
                    if result is not None:
                        active = True
                        processed += 1
                        if on_result is not None:
                            on_result(camera_id, snapshot, result)
                if not active:
                    if not any(item.get("running") for item in self._manager.list_sources()):
                        break
                    time.sleep(self._poll_interval_s)
            return OperationalSummary(processed, "STOPPED", self._chain.summary())
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._chain.close()
        self._manager.close_all()
