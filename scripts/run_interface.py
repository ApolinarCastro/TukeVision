"""Interfaz operativa local de TukeVision.

Abre la aplicación de escritorio Tkinter. La selección de fuente
(FILE / WEBCAM / RTSP) se realiza dentro de la aplicación.

Uso:
    python scripts/run_interface.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk

from src.ui.controller import UiController
from src.ui.tk_view import TkApp


def main() -> None:
    controller = UiController()
    root = tk.Tk()
    app = TkApp(root, controller)
    app.run()


if __name__ == "__main__":
    main()
