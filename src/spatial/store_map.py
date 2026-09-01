"""Store Operational Map (Slice 7).

Consolidates camera coverage, gaps, and spatial entities into a single
StoreSceneState representation. Acts as an observer/aggregator decoupled
from the hot inference path.
"""

from typing import Dict, Any, Optional
import datetime
import logging

from src.spatial.contract import StoreSceneState
from src.spatial.viewshed import ViewshedEngine
from src.spatial.entity_state import SpatialStateManager

logger = logging.getLogger("tukevision.spatial.store_map")

class StoreOperationalMap:
    """Aggregates spatial and topological data into a unified Operational Map."""

    def __init__(
        self,
        store_id: str,
        viewshed_engine: ViewshedEngine,
        spatial_manager: SpatialStateManager
    ):
        self._store_id = store_id
        self._viewshed = viewshed_engine
        self._spatial = spatial_manager
        
    def generate_scene_state(self) -> StoreSceneState:
        """Generates the current operational snapshot of the store."""
        
        # Get all cameras
        cameras = dict(self._viewshed._cameras)
        
        # Calculate gaps
        coverage_gaps = self._viewshed.get_coverage_gaps()
        
        # Get active entities
        # Assuming we have a way to filter stale entities, or we just snapshot all
        entities = dict(self._spatial._states)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        state = StoreSceneState(
            store_id=self._store_id,
            timestamp=timestamp,
            cameras=cameras,
            entities=entities,
            coverage_gaps=coverage_gaps
        )
        
        return state

    def update_from_event(self, event_type: str, payload: Dict[str, Any]):
        """
        Optional: Allows the map to be updated via an Event bus (Observer pattern)
        without being tightly coupled to AdvanceChain.
        """
        if event_type == "SPATIAL_OBSERVATION_GENERATED":
            # Just an example of how it could passively consume
            pass
        elif event_type == "CAMERA_CALIBRATION_UPDATED":
            pass
