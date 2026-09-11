"""TukeVision multistore domain package.

Contratos de dominio aprobados (AG-02 MULTISTORE_ARCHITECTURE_CONTRACT,
baseline 61d7ab38516d9da656a53c71d919f9857eda50d4):

    ORGANIZATION -> STORE -> RECORDER -> CAMERA

Este paquete NO sustituye SourceManager ni EvidenStore: solo modela la
configuración estática del catálogo multitienda y la convierte en
descriptores que el núcleo certificado ya sabe consumir.
"""

from src.domain.models import (
    CameraConfig,
    CameraHealthState,
    OrganizationConfig,
    PTZConfig,
    RecorderConfig,
    SourceType,
    StoreConfig,
    ZoneRole,
)
from src.domain.catalog import StoreCatalog

__all__ = [
    "CameraConfig",
    "CameraHealthState",
    "OrganizationConfig",
    "PTZConfig",
    "RecorderConfig",
    "SourceType",
    "StoreConfig",
    "StoreCatalog",
    "ZoneRole",
]