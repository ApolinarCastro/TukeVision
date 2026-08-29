"""Dynamic grid layout computation for the operator UI.

Given N camera ids, produce a stable (rows, columns) grid and a stable
per-cell camera ordering supporting the certified layouts:

    1 -> 1x1
    4 -> 2x2
    6 -> 1 main + 5 aux (2x3 with main spanning 2 rows)
    9 -> 3x3
    16 -> 4x4
    N  -> square-ish rows x cols that never hides a camera

The layout is deterministic (no randomness) and purely presentational:
it never owns capture, frames or pipeline state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class GridCell:
    """A cell in the operator grid with optional spanning for GRID_6 main camera."""
    camera_id: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    is_main: bool = False
    is_empty: bool = False


_SUPPORTED = {1: (1, 1), 4: (2, 2), 9: (3, 3), 16: (4, 4)}


def grid_size(camera_count: int) -> Tuple[int, int]:
    """Rows and columns for a camera count.

    Supported presets map to the certified layouts; any other count maps
    to a square-ish grid (ceil(sqrt N) rows, ceil(N / rows) cols) so no
    camera is hidden.
    """
    if camera_count < 1:
        return (1, 1)
    if camera_count in _SUPPORTED:
        return _SUPPORTED[camera_count]
    rows = int(math.ceil(math.sqrt(camera_count)))
    cols = int(math.ceil(camera_count / rows))
    return (rows, cols)


def grid_capacity(camera_count: int) -> int:
    """Visual capacity of the natural grid for ``camera_count`` cameras.

    The capacity is the number of cells the grid renders: for a square-ish
    grid that is rows * cols, so 15 cameras render in a 4x4 grid with one
    empty cell. GRID_6 is its own 6-cell layout and has no empty cells.
    The capacity is never the physical camera count when the two differ
    (e.g. 15 physical cameras over a 16-cell grid).
    """
    count = max(0, int(camera_count))
    if count == 0:
        return 0
    if count == 6:
        return 6
    rows, cols = grid_size(count)
    return rows * cols


def grid_layout(camera_ids: Sequence[str]) -> List[List[str]]:
    """Row-major cell mapping for the given camera ids.

    For GRID_6 (6 cameras) the layout mirrors :func:`grid_cells`: main camera
    (ids[0]) occupies col 0 spanning rows 0-1, the five aux cameras fill the
    remaining cells, and every camera appears exactly once (no duplicated
    CAM-001, no omitted CAM-006). Spanned cells are represented by ``""``.
    """
    ids = list(camera_ids)
    if not ids:
        return []
    count = len(ids)
    if count == 6:
        # GRID_6: 1 main (2x2) at (0,0), 2 aux on right (col 2), 3 aux on bottom (row 2)
        # 100% space utilization, 0 dead slots, 0 distortion
        return [
            [ids[0], "", ids[1]],
            ["", "", ids[2]],
            [ids[3], ids[4], ids[5]],
        ]
    rows, cols = grid_size(count)
    layout: List[List[str]] = []
    for row in range(rows):
        start = row * cols
        end = min(start + cols, len(ids))
        cells = list(ids[start:end])
        if cells:
            layout.append(cells)
    return layout


GRID_PRESETS = (1, 4, 6, 9, 16)

EMPTY_SLOT_LABEL = "SIN CÁMARA"


def cycle_grid_preset(current, camera_count: int, capacity: int = 0) -> int:
    """Next grid preset in the 1/4/6/9/16 cycle for the catalog size.

    Presets are capped at the grid *capacity* (which may exceed the
    physical camera count, e.g. 15 physical cameras over a 16-cell grid) or
    at the number of available cameras when no capacity is given; ``None``
    starts the cycle at the smallest preset. Pure helper so preset
    switching is deterministic and unit-testable.
    """
    count = max(1, int(camera_count))
    cap = max(count, int(capacity or 0))
    presets = [n for n in GRID_PRESETS if n <= cap] or [1]
    if current is None or current not in presets:
        return presets[0]
    index = presets.index(current)
    return presets[(index + 1) % len(presets)]


def grid_cells(camera_ids: Sequence[str], capacity: int = 0) -> List[GridCell]:
    """Cell placements with row/col spanning for Tkinter grid geometry.

    For GRID_6: main camera at (0,0) with rowspan=2, colspan=2; 2 aux on right
    at (0,2) and (1,2); 3 aux on bottom at (2,0), (2,1), (2,2). 100% area utilization.
    For other counts: regular row-major grid. When ``capacity`` is greater
    than the number of cameras, the trailing positions become empty slots
    (``is_empty=True``, ``camera_id=""``) so the grid renders its full
    capacity (e.g. 15 cameras in a 4x4 grid leave one "SIN CÁMARA" slot).
    """
    ids = list(camera_ids)
    if not ids:
        return []
    count = len(ids)
    if count == 6:
        cells = [
            GridCell(camera_id=ids[0], row=0, col=0, rowspan=2, colspan=2, is_main=True),
            GridCell(camera_id=ids[1], row=0, col=2, rowspan=1, colspan=1),
            GridCell(camera_id=ids[2], row=1, col=2, rowspan=1, colspan=1),
            GridCell(camera_id=ids[3], row=2, col=0, rowspan=1, colspan=1),
            GridCell(camera_id=ids[4], row=2, col=1, rowspan=1, colspan=1),
            GridCell(camera_id=ids[5], row=2, col=2, rowspan=1, colspan=1),
        ]
        return cells
    cap = max(count, int(capacity or 0))
    rows, cols = grid_size(cap)
    cells: List[GridCell] = []
    for row in range(rows):
        for col in range(cols):
            idx = row * cols + col
            if idx < count:
                cells.append(GridCell(camera_id=ids[idx], row=row, col=col))
            elif idx < cap:
                cells.append(GridCell(camera_id="", row=row, col=col, is_empty=True))
    return cells


def focus_page(camera_ids: Sequence[str], focus_index: int, page_size: int) -> Tuple[int, int]:
    """Paginated browsing bounds (start, end) around a focused camera.

    Returns a page that includes ``camera_ids[focus_index]`` so operator
    next/previous navigation stays contiguous across the full catalog.
    """
    ids = list(camera_ids)
    count = len(ids)
    if count == 0:
        return (0, 0)
    focus_index = max(0, min(int(focus_index), count - 1))
    page_size = max(1, int(page_size))
    start = (focus_index // page_size) * page_size
    end = min(start + page_size, count)
    return (start, end)