"""Process-wide shared Tk root for GUI tests.

The bundled Tcl/Tk on Windows is fragile when many ``tk.Tk()`` roots are
created and destroyed inside a single pytest process (intermittent
``ttk::LoadThemes`` TclError). All GUI tests therefore reuse ONE root
created lazily and destroyed once at interpreter exit.
"""

import atexit
import tkinter as tk

_shared_root = None


def shared_root() -> tk.Tk:
    global _shared_root
    if _shared_root is None or not _shared_root.winfo_exists():
        _shared_root = tk.Tk()
        _shared_root.withdraw()
    return _shared_root


def destroy_shared_root() -> None:
    global _shared_root
    if _shared_root is not None:
        try:
            _shared_root.destroy()
        except tk.TclError:
            pass
        _shared_root = None


atexit.register(destroy_shared_root)