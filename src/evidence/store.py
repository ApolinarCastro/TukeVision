"""Almacén de evidencia local.

Responsabilidad única: guardar un fotograma y sus metadatos de forma
inmutable bajo data/evidence/<alert_id>/. No sobrescribe evidencia
existente ni modifica archivos previos.
"""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.evidence.models import EvidenceMetadata


class EvidenceError(Exception):
    """Excepción base para errores del almacén de evidencia."""
    pass


class EvidenceExistsError(EvidenceError):
    """La evidencia solicitada ya existe."""
    pass


class InvalidEvidenceError(EvidenceError):
    """Datos insuficientes o inválidos para guardar evidencia."""
    pass


class EvidenceStore:
    """Guarda evidencia local inmutable."""

    def __init__(self, base_dir: str = "data/evidence") -> None:
        self._base_dir = Path(base_dir)

    def _frame_sha256(self, frame_path: Path) -> str:
        with frame_path.open("rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def _target_dir(self, alert_id: str) -> Path:
        return self._base_dir / alert_id

    def exists(self, alert_id: str) -> bool:
        """Indica si ya existe evidencia para la alerta."""
        target = self._target_dir(alert_id)
        return target.exists()

    def save(
        self,
        frame: np.ndarray,
        metadata: EvidenceMetadata,
    ) -> Path:
        """Guarda fotograma y metadatos de forma inmutable.

        Args:
            frame: Fotograma BGR.
            metadata: Metadatos asociados a la evidencia.

        Returns:
            Ruta relativa del directorio de la evidencia.

        Raises:
            EvidenceExistsError: Si la evidencia ya existe.
            InvalidEvidenceError: Si el fotograma o metadatos son inválidos.
        """
        if frame is None or frame.size == 0:
            raise InvalidEvidenceError("El fotograma es obligatorio")
        if metadata is None or not metadata.alert_id:
            raise InvalidEvidenceError(
                "Los metadatos con alert_id son obligatorios"
            )

        if self.exists(metadata.alert_id):
            raise EvidenceExistsError(
                f"La evidencia ya existe para {metadata.alert_id}"
            )

        target = self._target_dir(metadata.alert_id)
        target.mkdir(parents=True, exist_ok=False)

        frame_path = target / "frame.jpg"
        ok = cv2.imwrite(str(frame_path), frame)
        if not ok:
            raise InvalidEvidenceError(
                "No se pudo guardar el fotograma de evidencia"
            )

        sha256 = self._frame_sha256(frame_path)
        metadata_dict = asdict(metadata)
        metadata_dict["frame_sha256"] = sha256
        metadata_dict["observation_ids"] = list(metadata.observation_ids)

        with (target / "metadata.json").open("w", encoding="utf-8") as fh:
            json.dump(metadata_dict, fh, ensure_ascii=False, indent=2)

        return target.relative_to(self._base_dir.parent)

    def load_metadata(self, alert_id: str) -> Optional[dict]:
        """Carga los metadatos de una evidencia existente."""
        meta_path = self._target_dir(alert_id) / "metadata.json"
        if not meta_path.exists():
            return None
        with meta_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
