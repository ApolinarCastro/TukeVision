"""Zona de observación configurable.

Responsabilidad única: representar una zona poligonal de la tienda y
determinar si una persona (identificada por su punto inferior central)
se encuentra dentro, así como registrar entrada, permanencia y salida.
"""

from dataclasses import dataclass
from typing import List, Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class ZoneStatus:
    """Estado de una persona respecto a la zona."""
    track_id: int
    in_zone: bool


class ZoneError(Exception):
    """Excepción base para errores de zona."""
    pass


class InvalidPolygonError(ZoneError):
    """El polígono definido no es válido."""
    pass


class InvalidZoneDefinitionError(ZoneError):
    """Falta identificador o nombre de la zona."""
    pass


class InvalidPointError(ZoneError):
    """El punto de evaluación no es válido."""
    pass


class Zone:
    """Zona poligonal configurable de observación."""

    def __init__(
        self,
        zone_id: str,
        name: str,
        polygon: List[List[int]],
    ) -> None:
        if not zone_id or not zone_id.strip():
            raise InvalidZoneDefinitionError("El identificador de la zona es obligatorio")
        if not name or not name.strip():
            raise InvalidZoneDefinitionError("El nombre de la zona es obligatorio")
        self._zone_id = zone_id
        self._name = name
        self._polygon = self._validate_polygon(polygon)
        self._inside_tracks = set()

    @property
    def zone_id(self) -> str:
        return self._zone_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def polygon(self) -> List[List[int]]:
        return [[int(pt[0][0]), int(pt[0][1])] for pt in self._polygon]

    def _validate_polygon(self, polygon: List[List[int]]) -> np.ndarray:
        if polygon is None or len(polygon) < 3:
            raise InvalidPolygonError(
                "El polígono debe tener al menos 3 vértices"
            )
        pts = []
        for pt in polygon:
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise InvalidPolygonError("Cada vértice debe ser [x, y]")
            x, y = pt
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise InvalidPolygonError("Cada coordenada debe ser numérica")
            pts.append([int(x), int(y)])
        arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
        area = cv2.contourArea(arr)
        if area <= 0:
            raise InvalidPolygonError("El polígono no forma un área válida")
        return arr

    def _validate_point(self, x: float, y: float) -> None:
        if x is None or y is None:
            raise InvalidPointError("El punto debe incluir coordenadas x e y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise InvalidPointError("Las coordenadas deben ser numéricas")

    def contains_point(self, x: float, y: float) -> bool:
        """Determina si un punto está dentro del polígono."""
        self._validate_point(x, y)
        point = (float(x), float(y))
        result = cv2.pointPolygonTest(
            self._polygon, point, measureDist=False
        )
        return result >= 0

    def contains_person(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Determina si el punto inferior central de una persona está dentro."""
        cx = (x1 + x2) / 2.0
        cy = y2
        return self.contains_point(cx, cy)

    def update(self, track_id: int, x1: int, y1: int, x2: int, y2: int) -> str:
        """Actualiza el estado de una persona y devuelve la transición.

        Returns:
            'ENTERED' si la persona acaba de entrar.
            'REMAINED' si la persona continúa dentro.
            'EXITED' si la persona acaba de salir.
            'OUTSIDE' si la persona sigue fuera.
        """
        inside = self.contains_person(x1, y1, x2, y2)
        was_inside = track_id in self._inside_tracks

        if inside and not was_inside:
            self._inside_tracks.add(track_id)
            return "ENTERED"
        if inside and was_inside:
            return "REMAINED"
        if not inside and was_inside:
            self._inside_tracks.discard(track_id)
            return "EXITED"
        return "OUTSIDE"

    def is_inside(self, track_id: int) -> bool:
        """Indica si una trayectoria se encuentra actualmente dentro."""
        return track_id in self._inside_tracks

    def clear(self) -> None:
        """Limpia el estado interno de presencias."""
        self._inside_tracks.clear()
