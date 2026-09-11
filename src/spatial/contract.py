"""Spatial Scene Contract for Operational Intelligence.

Defines the mathematical, epistemic, and operational state of the physical store.
Coordinates are strictly local metric (meters) from a store-defined origin.
No global (WGS84/ECEF) coordinates are used for indoor retail.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict, Optional


class ObservationState(str, Enum):
    """Taxonomía epistémica: El grado de realidad de una observación."""
    LIVE_OBSERVED = "LIVE_OBSERVED"   # Visto ahora mismo por un detector en un frame fresco
    DELAYED = "DELAYED"               # Visto por un detector pero en un frame con retardo
    DERIVED = "DERIVED"               # Calculado matemáticamente (ej. homografía) pero anclado a evidencia real
    INFERRED = "INFERRED"             # Deducido lógicamente (ej. oclusión temporal corta)
    RECONSTRUCTED = "RECONSTRUCTED"   # Estimado a partir de trayectorias pasadas (handoff)
    UNAVAILABLE = "UNAVAILABLE"       # No existe información


class SpatialProvenance(str, Enum):
    """El origen del dato espacial."""
    CAMERA_PROJECTION = "CAMERA_PROJECTION"
    TRACKER_ESTIMATE = "TRACKER_ESTIMATE"
    TOPOLOGICAL_HANDOFF = "TOPOLOGICAL_HANDOFF"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    SYSTEM_UNKNOWN = "SYSTEM_UNKNOWN"


@dataclass(frozen=True)
class StoreCoordinate:
    """Sistema local métrico. origin = store-defined (0,0) en metros."""
    x: float
    y: float
    z: Optional[float] = None
    

@dataclass
class CameraCoverage:
    """Polígono de cobertura 2D sobre el plano de la tienda."""
    polygon_points: List[StoreCoordinate]
    is_active: bool = True


@dataclass
class CameraSpatialModel:
    """Modelo geométrico y de cobertura de una cámara física."""
    camera_id: str
    position_store: StoreCoordinate
    orientation_yaw_deg: float
    field_of_view_deg: float
    coverage: CameraCoverage
    calibration_version: str
    # Opcional: modelo de oclusión 2D (ej. polígonos ciegos)
    occlusion_model: Optional[List[List[StoreCoordinate]]] = None


@dataclass
class SpatialObservation:
    """Observación atómica posicionada en el espacio de la tienda."""
    observation_id: str
    entity_id: str
    camera_id: str
    
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    ground_point_px: Tuple[int, int] # x, y en pixeles (generalmente base del bbox)
    
    store_x: float
    store_y: float
    
    observed_at: str
    processed_at: str
    
    observation_state: ObservationState
    confidence: float
    source_generation: str
    provenance: SpatialProvenance


@dataclass
class SpatialTrajectoryPoint:
    """Punto histórico en la trayectoria de una entidad."""
    x: float
    y: float
    timestamp: str
    source_camera: str
    confidence: float
    observation_state: ObservationState


@dataclass
class SpatialEntityState:
    """Estado espacial actual de una entidad en la tienda."""
    entity_id: str
    
    current_store_position: StoreCoordinate
    previous_store_position: Optional[StoreCoordinate]
    
    velocity_vector: Tuple[float, float]  # vx, vy en metros/segundo
    direction_deg: float                  # 0-360 grados
    
    current_zone: Optional[str]
    previous_zone: Optional[str]
    
    active_camera: Optional[str]
    candidate_cameras: List[str]
    
    trajectory: List[SpatialTrajectoryPoint]
    
    observation_state: ObservationState
    confidence: float
    freshness: float
    
    last_observed_at: str


@dataclass
class StoreSceneState:
    """Estado general y mapa operativo de la tienda."""
    store_id: str
    timestamp: str
    
    cameras: Dict[str, CameraSpatialModel]
    entities: Dict[str, SpatialEntityState]
    coverage_gaps: List[List[StoreCoordinate]]
