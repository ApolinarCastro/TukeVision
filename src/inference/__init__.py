"""Capa de inferencia selectiva y detección de eventos (LOOP-0018Q).

Arquitectura (continuación del pipeline del producto):

    CAMERA/SOURCE -> OBSERVATION -> POLICY -> SELECTIVE INFERENCE
                                          -> EVENT -> EVIDENCE_REFERENCE

Componentes:

  - contract: contrato mínimo de inferencia (InferenceEngine / InferenceResult),
    desacoplado de YOLO/OpenCV. El backend puede sustituirse sin tocar la
    Observation Layer.
  - engines: backends de inferencia. DeterministicInferenceEngine (backend
    determinista/fake para certificación y tests) y YoloInferenceEngine
    (backend real que REUTILIZA PersonDetector del BASE por composición).
  - events: evento canónico (InferenceEvent), EventDetector config-driven y
    cola acotada (BoundedEventQueue) con política de overflow explícita.
  - selective: SelectiveInferencePipeline, inferencia SELECTIVA gobernada por
    ObservationPolicy (QUALITY/BALANCED/ECONOMY), con métricas por cámara y
    total, aislamiento de fallos del backend y procesamiento acotado.

Reutilización (REUSE BEFORE NEW DEVELOPMENT, LOOP-0018N/P):

  - ObservationPolicy se REUTILIZA directamente desde src.observations.activity.
  - PersonDetector se REUTILIZA por composición (YoloInferenceEngine).
  - Patrón de cola acotada certificado (BOUNDED_QUEUE / BoundedObservationQueue)
    se adapta a BoundedEventQueue (REUSE_WITH_ADAPTATION, concepto).
  - redact_rtsp_url de src.observability (defensa en profundidad).
"""

from src.inference.contract import (
    InferenceDetection,
    InferenceEngine,
    InferenceError,
    InferenceConfigError,
    InferenceResult,
    InferenceValidationError,
)
from src.inference.engines import (
    DeterministicInferenceEngine,
    YoloInferenceEngine,
    build_engine,
)
from src.inference.events import (
    BoundedEventQueue,
    DROP_NEWEST,
    DROP_OLDEST,
    EventDetector,
    InferenceEvent,
)
from src.inference.selective import SelectiveInferencePipeline

__all__ = [
    "InferenceDetection",
    "InferenceEngine",
    "InferenceError",
    "InferenceConfigError",
    "InferenceResult",
    "InferenceValidationError",
    "DeterministicInferenceEngine",
    "YoloInferenceEngine",
    "build_engine",
    "BoundedEventQueue",
    "DROP_NEWEST",
    "DROP_OLDEST",
    "EventDetector",
    "InferenceEvent",
    "SelectiveInferencePipeline",
]