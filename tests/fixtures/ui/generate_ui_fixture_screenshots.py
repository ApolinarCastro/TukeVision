import json
import os
from pathlib import Path
import sys
import time
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
sys.path.insert(0, os.getcwd())

from src.localization.i18n import I18n, _
from src.ui.design_tokens import DesignTokens
from src.ui.tk_operational_panels import (
    OperationalCommandCenterModes,
    OperationalPanelsController,
)
from src.visualization.operational_intelligence import (
    EvidenceBundleViewItem,
    GovernedActionViewItem,
    InvestigationViewItem,
    OperationalIntelligenceViewModel,
    OperatorTimelineEvent,
    SituationViewItem,
)


FIXTURE_DIR = Path("tests/fixtures/ui/golden")
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_color(c: str, default: str = "#F9FAFB") -> str:
    if not c or str(c).lower().startswith("system") or str(c).lower() in ("current", ""):
        return default
    return c


def capture_canvas_to_image(canvas: tk.Canvas, filepath: Path, cw: int, ch: int):
    """Render canvas elements directly onto a PNG image fixture."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (cw, ch), color="#0B0F19")
    draw = ImageDraw.Draw(img)

    for item in canvas.find_all():
        itype = canvas.type(item)
        coords = canvas.coords(item)
        if itype == "rectangle" and len(coords) == 4:
            raw_fill = canvas.itemcget(item, "fill")
            raw_outline = canvas.itemcget(item, "outline")
            fill = sanitize_color(raw_fill, None) if raw_fill else None
            outline = sanitize_color(raw_outline, None) if raw_outline else None
            draw.rectangle([coords[0], coords[1], coords[2], coords[3]], fill=fill, outline=outline)
        elif itype == "text" and len(coords) == 2:
            txt = canvas.itemcget(item, "text")
            raw_fill = canvas.itemcget(item, "fill")
            fill = sanitize_color(raw_fill, "#F9FAFB")
            anchor = canvas.itemcget(item, "anchor") or "center"
            draw.text((coords[0], coords[1]), txt, fill=fill, anchor=("la" if anchor == "w" else "ra" if anchor == "e" else "mm"))
        elif itype == "line" and len(coords) == 4:
            raw_fill = canvas.itemcget(item, "fill")
            fill = sanitize_color(raw_fill, "#374151")
            draw.line([coords[0], coords[1], coords[2], coords[3]], fill=fill, width=1)

    img.save(filepath)


def generate_ui_fixtures():
    root = tk.Tk()
    root.geometry("1280x720")
    root.withdraw()

    cw, ch = 1200, 600
    canvas = tk.Canvas(root, width=cw, height=ch, bg=DesignTokens.COLORS["bg"])
    canvas.pack(fill="both", expand=True)

    vm = OperationalIntelligenceViewModel()
    controller = OperationalPanelsController(root, view_model=vm)

    state = {
        "store_id": "TIENDA PRINCIPAL",
        "fps": 25.0,
        "evidence_paths": [Path("evidence/BND-001.json")],
        "agent_state": "OBSERVANDO",
        "autonomy_level": "AUTONOMÍA: NO CERTIFICADA",
    }

    class MockPanel:
        def __init__(self, cid):
            self.camera_id = cid
            self.source_state = "OPEN"
            self.fps = 25.0
            self.resolution = "1920x1080"
            self.generation = 1
            self.frame_index = 100
            self.situation = None
            self.event = None
            self.evidence = None

    panels = {f"cam_{i:02d}": MockPanel(f"cam_{i:02d}") for i in range(1, 16)}

    # 1. Resumen
    controller.render_view(OperationalCommandCenterModes.OVERVIEW, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "01_resumen.png", cw, ch)

    # 2. Situaciones
    controller.render_view(OperationalCommandCenterModes.SITUATIONS, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "02_situaciones.png", cw, ch)

    # 3. Investigaciones
    controller.render_view(OperationalCommandCenterModes.INVESTIGATIONS, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "03_investigaciones.png", cw, ch)

    # 4. Evidencia
    controller.render_view(OperationalCommandCenterModes.EVIDENCE, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "04_evidencia.png", cw, ch)

    # 5. Mapa
    controller.render_view(OperationalCommandCenterModes.MAP, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "05_mapa.png", cw, ch)

    # 6. Sistema
    controller.render_view(OperationalCommandCenterModes.SYSTEM, canvas, cw, ch, state, panels)
    root.update_idletasks()
    capture_canvas_to_image(canvas, FIXTURE_DIR / "06_sistema.png", cw, ch)

    manifest = {
        "evidence_type": "UI_GOLDEN",
        "synthetic": True,
        "description": "Visual golden fixtures for UI regression validation",
        "timestamp": time.time(),
    }
    with open(FIXTURE_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    root.destroy()
    print("UI Golden fixtures generated in:", FIXTURE_DIR)


if __name__ == "__main__":
    generate_ui_fixtures()
