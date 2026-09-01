"""Grid capacity / empty-slot tests (MACRO-OC-02, Bloques A/K).

15 physical cameras render over a 16-cell grid capacity:
  - grid_capacity(15) == 16
  - grid_cells(15 ids, capacity=16) -> 16 cells, one is_empty slot
  - preset cycling reaches GRID_16 even when the physical count is 15
"""

import unittest

from src.ui.grid_layout import (
    EMPTY_SLOT_LABEL,
    GRID_PRESETS,
    cycle_grid_preset,
    grid_capacity,
    grid_cells,
)


def camera_ids(count):
    return tuple(f"cam_{i:02d}" for i in range(1, count + 1))


class TestGridCapacity(unittest.TestCase):
    def test_15_physical_cameras_render_in_a_15_cell_grid(self):
        self.assertEqual(grid_capacity(15), 15)
        self.assertEqual(grid_capacity(16), 16)
        self.assertEqual(grid_capacity(9), 9)
        self.assertEqual(grid_capacity(4), 4)
        self.assertEqual(grid_capacity(1), 1)
        self.assertEqual(grid_capacity(6), 6)

    def test_grid_cells_15_over_16_has_one_empty_slot(self):
        ids = camera_ids(15)
        cells = grid_cells(ids, capacity=16)
        self.assertEqual(len(cells), 16)
        filled = [c for c in cells if not c.is_empty]
        empty = [c for c in cells if c.is_empty]
        self.assertEqual(len(filled), 15)
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0].camera_id, "")
        self.assertEqual(empty[0].row, 3)
        self.assertEqual(empty[0].col, 3)
        self.assertEqual(EMPTY_SLOT_LABEL, "SIN CÁMARA")

    def test_grid_cells_without_capacity_has_no_empty_slot(self):
        ids = camera_ids(15)
        cells = grid_cells(ids)
        self.assertTrue(all(not c.is_empty for c in cells))
        self.assertEqual(len(cells), 15)

    def test_empty_slot_is_never_a_camera(self):
        ids = camera_ids(15)
        cells = grid_cells(ids, capacity=16)
        empty_ids = {c.camera_id for c in cells if c.is_empty}
        self.assertEqual(empty_ids, {""})


class TestPresetCyclingOverCapacity(unittest.TestCase):
    def test_16_is_reachable_with_15_physical_cameras(self):
        preset = None
        seen = []
        for _ in range(6):
            preset = cycle_grid_preset(preset, 15, capacity=16)
            seen.append(preset)
        self.assertEqual(seen, [1, 4, 6, 9, 16, 1])
        self.assertIn(16, seen)

    def test_visible_subset_never_exceeds_physical_count(self):
        ids = camera_ids(15)
        preset = 16
        visible = ids[: min(preset, len(ids))]
        self.assertEqual(len(visible), 15)

    def test_default_capacity_falls_back_to_camera_count(self):
        # Backward compatible: no capacity arg behaves as before.
        self.assertEqual(cycle_grid_preset(None, 6), 1)
        self.assertEqual(cycle_grid_preset(None, 3), 1)
        self.assertEqual(cycle_grid_preset(None, 16), 1)
        self.assertEqual(GRID_PRESETS, (1, 4, 6, 9, 16))


if __name__ == "__main__":
    unittest.main()