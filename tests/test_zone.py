"""Pruebas unitarias para src.context.zone (sin dependencias externas)."""

import unittest

from src.context.zone import (
    Zone,
    ZoneStatus,
    InvalidPolygonError,
    InvalidZoneDefinitionError,
    InvalidPointError,
)


class TestZone(unittest.TestCase):

    def setUp(self) -> None:
        self.polygon = [[100, 100], [540, 100], [540, 420], [100, 420]]
        self.zone = Zone(zone_id="ZONE-001", name="Zona piloto", polygon=self.polygon)

    def test_point_inside(self) -> None:
        """Verifica que un punto dentro es detectado."""
        self.assertTrue(self.zone.contains_point(300, 250))

    def test_point_outside(self) -> None:
        """Verifica que un punto fuera no es detectado."""
        self.assertFalse(self.zone.contains_point(50, 50))
        self.assertFalse(self.zone.contains_point(600, 500))

    def test_point_on_edge_counts_inside(self) -> None:
        """Verifica que un punto en el borde cuenta como dentro."""
        self.assertTrue(self.zone.contains_point(100, 250))

    def test_person_inside_uses_lower_center(self) -> None:
        """Verifica que la persona se evalúa por su punto inferior central."""
        # Caja con borde inferior dentro de la zona
        self.assertTrue(self.zone.contains_person(200, 300, 300, 400))
        # Caja totalmente encima de la zona (borde inferior y1 < 100)
        self.assertFalse(self.zone.contains_person(200, 10, 300, 90))

    def test_entry(self) -> None:
        """Verifica detección de entrada."""
        self.assertEqual(self.zone.update(1, 200, 300, 300, 400), "ENTERED")

    def test_remain(self) -> None:
        """Verifica detección de permanencia."""
        self.zone.update(1, 200, 300, 300, 400)
        self.assertEqual(self.zone.update(1, 210, 310, 310, 410), "REMAINED")

    def test_exit(self) -> None:
        """Verifica detección de salida."""
        self.zone.update(1, 200, 300, 300, 400)
        self.assertEqual(self.zone.update(1, 50, 500, 150, 600), "EXITED")

    def test_outside_remains_outside(self) -> None:
        """Verifica que permanecer fuera no produce transición."""
        self.assertEqual(self.zone.update(1, 50, 500, 150, 600), "OUTSIDE")

    def test_is_inside_state(self) -> None:
        """Verifica que el estado interno de presencia se actualiza."""
        self.assertFalse(self.zone.is_inside(1))
        self.zone.update(1, 200, 300, 300, 400)
        self.assertTrue(self.zone.is_inside(1))
        self.zone.update(1, 50, 500, 150, 600)
        self.assertFalse(self.zone.is_inside(1))

    def test_invalid_polygon_too_few_points(self) -> None:
        """Verifica rechazo de polígono con menos de 3 vértices."""
        with self.assertRaises(InvalidPolygonError):
            Zone("ZONE-X", "Zona", [[0, 0], [1, 1]])

    def test_invalid_polygon_zero_area(self) -> None:
        """Verifica rechazo de polígono sin área (colineal)."""
        with self.assertRaises(InvalidPolygonError):
            Zone("ZONE-X", "Zona", [[0, 0], [0, 10], [0, 20]])

    def test_invalid_polygon_bad_point(self) -> None:
        """Verifica rechazo de vértice mal formado."""
        with self.assertRaises(InvalidPolygonError):
            Zone("ZONE-X", "Zona", [[0, 0], ["a", 1], [2, 2]])

    def test_missing_zone_id(self) -> None:
        """Verifica rechazo de zona sin identificador."""
        with self.assertRaises(InvalidZoneDefinitionError):
            Zone("", "Zona piloto", self.polygon)

    def test_missing_name(self) -> None:
        """Verifica rechazo de zona sin nombre."""
        with self.assertRaises(InvalidZoneDefinitionError):
            Zone("ZONE-001", "", self.polygon)

    def test_invalid_point(self) -> None:
        """Verifica rechazo de punto inválido."""
        with self.assertRaises(InvalidPointError):
            self.zone.contains_point(None, 100)

    def test_properties(self) -> None:
        """Verifica que se exponen identificador y nombre."""
        self.assertEqual(self.zone.zone_id, "ZONE-001")
        self.assertEqual(self.zone.name, "Zona piloto")
        self.assertEqual(len(self.zone.polygon), 4)


if __name__ == "__main__":
    unittest.main()
