#!/usr/bin/env python3
"""Secure credential dialog and launcher for TukeVision.

Provides a one-click login experience:
1. Shows secure credential dialog (username/password masked)
2. Verifies the configured recorder endpoint (TCP 554)
3. Opens the certified RTSP source and waits for a real first frame
   (REAL_STREAM_OPEN + FIRST_FRAME is the definitive auth test — no
   parallel Digest implementation is needed)
4. Launches the main application with credentials in memory

The first-frame gate reuses the exact certified opener the runtime uses
(src.capture.live_sources.RTSPSource + src.capture.source_manager
CameraDescriptor.build_url), so the probe validates the same
endpoint/path/subtype the Command Center will consume.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import replace
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.domain.catalog import StoreCatalog


# Timeout constants (seconds)
TCP_CONNECT_TIMEOUT = 3
FIRST_FRAME_TIMEOUT = 10
TOTAL_LOGIN_TIMEOUT = 30


class CredentialDialog:
    """Secure credential dialog for TukeVision launcher."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_config()
        self.result: Optional[Tuple[str, str, str]] = None  # (store_id, username, password)
        self._cancelled = False
        self._probe_thread: Optional[threading.Thread] = None
        self._login_start_time: float = 0
        self._root: Optional[tk.Tk] = None

    def _load_config(self) -> dict:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_stores(self) -> list:
        """Get available stores from multistore config."""
        multistore = self.config.get('multistore', {})
        if not multistore.get('enabled', False):
            return []
        return multistore.get('stores', [])

    def _configured_endpoints(self, store_id: str) -> list:
        """Recorder endpoints configured for a store (config-driven only).

        The endpoint list comes exclusively from the recorder configuration;
        it never invents fallback IPs (e.g. the operator laptop is never a
        recorder).
        """
        stores = self._get_stores()
        for store in stores:
            if store['store_id'] == store_id:
                return [
                    {
                        'recorder_id': recorder['recorder_id'],
                        'host': recorder['host'],
                        'port': recorder.get('port', 554),
                        'vendor': recorder.get('vendor', ''),
                        'username_default': recorder.get('username_default', 'admin'),
                    }
                    for recorder in store.get('recorders', [])
                ]
        return []

    def show(self) -> Optional[Tuple[str, str, str]]:
        """Show dialog and return (store_id, username, password) or None if cancelled."""
        root = tk.Tk()
        self._root = root
        root.title("TukeVision - Inicio de Sesión")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center on screen
        root.update_idletasks()
        width = 420
        height = 320
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        # Style
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 9), foreground='#666')

        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="TukeVision", style='Title.TLabel').pack(pady=(0, 4))
        ttk.Label(main_frame, text="Ingrese credenciales del DVR/NVR", style='Subtitle.TLabel').pack(pady=(0, 16))

        # Store selector (if multiple stores)
        stores = self._get_stores()
        self.store_var = tk.StringVar()
        if len(stores) > 1:
            ttk.Label(main_frame, text="Tienda:").pack(anchor=tk.W, pady=(0, 4))
            store_combo = ttk.Combobox(
                main_frame,
                textvariable=self.store_var,
                values=[f"{s['store_name']} ({s['store_id']})" for s in stores],
                state='readonly',
                width=40
            )
            store_combo.pack(fill=tk.X, pady=(0, 12))
            store_combo.current(0)
            self.store_map = {f"{s['store_name']} ({s['store_id']})": s['store_id'] for s in stores}
        else:
            self.store_var.set(stores[0]['store_id'] if stores else "")
            self.store_map = {}
            if stores:
                ttk.Label(main_frame, text=f"Tienda: {stores[0]['store_name']}", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 12))

        # Username
        ttk.Label(main_frame, text="Usuario:").pack(anchor=tk.W, pady=(0, 4))
        self.username_var = tk.StringVar(value="admin")
        username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=40)
        username_entry.pack(fill=tk.X, pady=(0, 12))

        # Password
        ttk.Label(main_frame, text="Contraseña:").pack(anchor=tk.W, pady=(0, 4))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(main_frame, textvariable=self.password_var, width=40, show="•")
        password_entry.pack(fill=tk.X, pady=(0, 16))

        # Status label
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground='#cc0000', font=('Segoe UI', 8))
        self.status_label.pack(anchor=tk.W, pady=(0, 8))

        # Progress indicator
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(main_frame, textvariable=self.progress_var, font=('Segoe UI', 8), foreground='#666')
        self.progress_label.pack(anchor=tk.W, pady=(0, 8))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(btn_frame, text="INICIAR", command=self._on_start)
        self.start_btn.pack(side=tk.RIGHT, padx=(8, 0))

        cancel_btn = ttk.Button(btn_frame, text="CANCELAR", command=self._on_cancel)
        cancel_btn.pack(side=tk.RIGHT)

        # Focus username field
        username_entry.focus_set()

        # Bind Enter key
        root.bind('<Return>', lambda e: self._on_start())
        root.bind('<Escape>', lambda e: self._on_cancel())

        # Start total timeout watchdog
        self._login_start_time = time.time()
        self._schedule_timeout_check()

        root.mainloop()

        if self._cancelled:
            return None
        return self.result

    def _schedule_timeout_check(self):
        """Check if total login timeout exceeded."""
        if self._cancelled or self._root is None or not self._root.winfo_exists():
            return
        elapsed = time.time() - self._login_start_time
        if elapsed > TOTAL_LOGIN_TIMEOUT:
            self._schedule_ui(lambda: self._set_status(f"Tiempo de espera agotado ({TOTAL_LOGIN_TIMEOUT}s)"))
            self._schedule_ui(lambda: self._enable_start_btn())
            return
        # Update progress
        remaining = int(TOTAL_LOGIN_TIMEOUT - elapsed)
        self._schedule_ui(lambda r=remaining: self._set_progress(f"Tiempo restante: {r}s"))
        self._root.after(1000, self._schedule_timeout_check)

    def _set_progress(self, text: str):
        if hasattr(self, 'progress_var'):
            self.progress_var.set(text)

    def _on_start(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username:
            self._set_status("Ingrese usuario")
            return
        if not password:
            self._set_status("Ingrese contraseña")
            return

        store_id = self.store_var.get()
        if store_id in self.store_map:
            store_id = self.store_map[store_id]

        if not store_id:
            self._set_status("Seleccione una tienda")
            return

        # Test connection in background
        self.start_btn.config(state=tk.DISABLED)
        self._set_status("Probando conexión...", '#cc6600')
        self._set_progress("Iniciando...")

        self._login_start_time = time.time()
        self._cancelled = False
        self._probe_thread = threading.Thread(
            target=self._test_and_launch,
            args=(store_id, username, password),
            daemon=True
        )
        self._probe_thread.start()

    def _set_status(self, text: str, color: str = '#cc0000'):
        if hasattr(self, 'status_var'):
            self.status_var.set(text)
            if hasattr(self, 'status_label'):
                self.status_label.config(foreground=color)

    def _enable_start_btn(self):
        if hasattr(self, 'start_btn'):
            self.start_btn.config(state=tk.NORMAL)

    def _tcp_reachable(self, host: str, port: int, timeout: int) -> bool:
        """Fast pre-check that the recorder TCP port responds."""
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            return True
        except Exception:
            return False

    def _probe_first_frame(self, host: str, username: str, password: str) -> dict:
        """Open CAM-001 through the certified opener and require a real frame.

        The URL is built exactly like the runtime does (StoreCatalog ->
        CameraDescriptor.build_url -> build_rtsp_url), so the probe validates
        the same endpoint/path/subtype the Command Center will consume. The
        definitive auth test is REAL_STREAM_OPEN + FIRST_FRAME, not a parallel
        Digest implementation.

        Returns {"ok": bool, "resolution": str, "error": str}. Never prints
        or persists the password.
        """
        from src.capture.live_sources import RTSPSource

        try:
            catalog = StoreCatalog.from_dict(self.config)
            entries = catalog.camera_descriptors(
                max_width=640,
                process_every_n_frames=1,
                frame_stall_timeout_s=3.0,
                rtsp_open_timeout_ms=5000,
                credential_resolver=lambda ref: (username, password),
            )
            if not entries:
                return {"ok": False, "resolution": "", "error": "NO_CAMERAS"}
            descriptor = replace(
                entries[0].descriptor,
                username=username,
                password=password,
            )
            url = descriptor.build_url()
            source = RTSPSource(
                rtsp_url=url,
                max_width=640,
                max_reconnect_attempts=0,
                max_open_attempts=1,
                rtsp_open_timeout_ms=5000,
                frame_stall_timeout_s=3.0,
            )
            try:
                meta = source.open()
                return {
                    "ok": True,
                    "resolution": f"{meta.width}x{meta.height}",
                    "error": "",
                }
            except Exception as exc:
                return {
                    "ok": False,
                    "resolution": "",
                    "error": type(exc).__name__,
                }
            finally:
                try:
                    source.close()
                except Exception:
                    pass
        except Exception as exc:
            return {"ok": False, "resolution": "", "error": type(exc).__name__}

    def _test_and_launch(self, store_id: str, username: str, password: str):
        """Verify the configured recorder and open the first frame, then launch."""
        try:
            endpoints = self._configured_endpoints(store_id)
            if not endpoints:
                self._schedule_ui(lambda: self._set_status("No hay endpoints configurados"))
                self._schedule_ui(self._enable_start_btn)
                return

            self._schedule_ui(lambda: self._set_progress("Verificando conexión al DVR..."))

            # Test each configured endpoint: TCP 554 -> certified first frame
            for endpoint in endpoints:
                if self._cancelled:
                    return
                host = endpoint['host']
                port = endpoint['port']

                self._schedule_ui(lambda h=host, p=port: self._set_status(f"Conectando a {h}:{p}...", '#cc6600'))

                if not self._tcp_reachable(host, port, TCP_CONNECT_TIMEOUT):
                    self._schedule_ui(lambda h=host, p=port: self._set_status(f"{h}:{p} no responde"))
                    continue

                self._schedule_ui(lambda h=host: self._set_status(f"Abriendo video en {h}...", '#cc6600'))
                self._schedule_ui(lambda: self._set_progress(f"Esperando primer fotograma (máx {FIRST_FRAME_TIMEOUT}s)..."))

                result = self._probe_first_frame(host, username, password)
                if self._cancelled:
                    return

                if result.get("ok"):
                    self._schedule_ui(lambda r=result: self._set_status(
                        f"Conexión validada — video OK ({r.get('resolution', '')})", '#006600'))
                    self._schedule_ui(lambda: self._set_progress("Abriendo Command Center..."))
                    self._schedule_ui(lambda: self._launch_main_app(store_id, username, password))
                    return

                self._schedule_ui(lambda err=result.get('error', ''): self._set_status(
                    f"No se pudo abrir el video en {host} ({err})"))

            # All configured endpoints failed
            self._schedule_ui(lambda: self._set_status(
                "No se pudo conectar al DVR (revise red o credenciales)"))
            self._schedule_ui(self._enable_start_btn)

        except Exception as e:
            self._schedule_ui(lambda err=str(e): self._set_status(f"Error interno: {err[:60]}"))
            self._schedule_ui(self._enable_start_btn)

    def _launch_main_app(self, store_id: str, username: str, password: str):
        """Record success and close the login dialog (UI thread)."""
        self.result = (store_id, username, password)
        self._cancelled = False
        self._schedule_ui(self._enable_start_btn)
        self._schedule_ui(lambda: self._set_status("Conexión validada", '#006600'))
        self._schedule_ui(lambda: self._set_progress("Abriendo Command Center..."))
        # Brief delay to show success state
        if self._root:
            self._root.after(500, self._close_dialog)

    def _close_dialog(self):
        if self._root and self._root.winfo_exists():
            self._root.quit()
            self._root.destroy()

    def _schedule_ui(self, func):
        """Schedule function to run on UI thread."""
        if self._root and self._root.winfo_exists():
            self._root.after(0, func)

    def _on_cancel(self):
        self._cancelled = True
        self.result = None
        if self._root and self._root.winfo_exists():
            self._root.quit()
            self._root.destroy()

    def _spawn_runtime(self, store_id: str, username: str, password: str) -> int:
        """Launch the main application with credentials in memory (no CLI args).

        Credentials travel in the child process environment as a JSON blob,
        never on the command line and never persisted.

        Resolves RTSP_BACKEND from config before spawn and transmits it
        explicitly. Verifies the value received inside the child process.
        """
        env = os.environ.copy()
        env['ENV_DVR_PRINCIPAL_CREDS'] = json.dumps(
            {"username": username, "password": password}
        )
        env['TUKEVISION_STORE_ID'] = store_id

        # Resolve RTSP_BACKEND from config before spawning child
        rtsp_config = self.config.get("rtsp", {})
        requested_backend = rtsp_config.get("backend", "ffmpeg_supervised").strip().lower()
        if requested_backend not in ("ffmpeg", "ffmpeg_supervised", "ffmpeg-supervised"):
            requested_backend = "ffmpeg_supervised"

        env['RTSP_BACKEND'] = requested_backend
        env['RTSP_BACKEND_REQUESTED'] = requested_backend
        env['RTSP_BACKEND_SOURCE'] = "config.rtsp.backend"

        multi_script = BASE / "scripts" / "run_multicamera.py"
        venv_python = BASE / ".venv" / "Scripts" / "python.exe"

        try:
            proc = subprocess.Popen(
                [str(venv_python), str(multi_script)],
                env=env,
                cwd=str(BASE),
            )
            # Verify backend was received by logging in child (child will log RTSP_BACKEND_REQUESTED)
            logger = logging.getLogger("tukevision.launcher")
            pid = getattr(proc, "pid", 0) or 0
            logger.info("SPAWNED child_pid=%d RTSP_BACKEND=%s", pid, requested_backend)
            res = proc.wait() if hasattr(proc, "wait") else 0
            return res if isinstance(res, int) else 0
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la aplicación:\n{e}")
            return 1


def main():
    config_path = BASE / "config" / "multistore.active.json"

    if not config_path.exists():
        messagebox.showerror("Error", f"Configuración no encontrada: {config_path}")
        return 1

    dialog = CredentialDialog(config_path)
    result = dialog.show()

    if result is None:
        return 0  # User cancelled

    store_id, username, password = result
    return dialog._spawn_runtime(store_id, username, password)


if __name__ == "__main__":
    sys.exit(main())