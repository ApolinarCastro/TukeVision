"""Vista Tkinter de la interfaz operativa local.

Responsabilidad única: presentar widgets y actualizarlos desde el hilo
principal (vía Tk.after()). Nunca modifica widgets desde el hilo de
trabajo. Convierte los frames del pipeline a PhotoImage usando
cv2.imencode (PNG), sin introducir dependencias nuevas.
"""

import os
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import cv2

from src.capture.rtsp_url import build_rtsp_url
from src.ui.state import AppStatus
from src.ui.multicamera import CAMERA_IDS, PANEL_LAYOUT


class TkApp:
    """Ventana principal de la interfaz operativa."""

    POLL_MS = 33

    def __init__(self, root: tk.Tk, controller) -> None:
        self._root = root
        self._controller = controller
        self._photo = None
        self._photos = {camera_id: None for camera_id in CAMERA_IDS}
        self._last_frame_index = -1
        self._build()

    def _build(self) -> None:
        self._root.title("TukeVision - Interfaz operativa local")
        self._root.geometry("1120x680")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Cabecera
        header = ttk.Frame(self._root, padding=(10, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="TukeVision", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)
        self._status_var = tk.StringVar(value="Estado: LISTA")
        ttk.Label(header, textvariable=self._status_var).pack(side=tk.RIGHT)

        body = ttk.Frame(self._root, padding=(10, 4))
        body.pack(fill=tk.BOTH, expand=True)

        # Panel video
        video_frame = ttk.LabelFrame(body, text="Video", padding=(6, 6))
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._video_labels = {}
        self._camera_state_vars = {}
        for row, columns in enumerate(PANEL_LAYOUT):
            video_frame.rowconfigure(row, weight=1)
            for column, camera_id in enumerate(columns):
                video_frame.columnconfigure(column, weight=1)
                panel = ttk.LabelFrame(video_frame, text=camera_id, padding=2)
                panel.grid(row=row, column=column, sticky="nsew", padx=2, pady=2)
                state_var = tk.StringVar(value="Estado: OFFLINE")
                self._camera_state_vars[camera_id] = state_var
                ttk.Label(panel, textvariable=state_var).pack(anchor=tk.W)
                label = ttk.Label(panel, text="Sin frame")
                label.pack(fill=tk.BOTH, expand=True)
                self._video_labels[camera_id] = label

        # Panel lateral de estado
        side = ttk.Frame(body, padding=(10, 0))
        side.pack(side=tk.RIGHT, fill=tk.Y)

        self._fuente_var = tk.StringVar(value="Fuente: -")
        self._conexion_var = tk.StringVar(value="Conexión: -")
        self._resolucion_var = tk.StringVar(value="Resolución: -")
        self._fps_var = tk.StringVar(value="FPS: -")
        self._track_var = tk.StringVar(value="Track ID: -")
        self._permanencia_var = tk.StringVar(value="Permanencia: -")
        self._riesgo_var = tk.StringVar(value="Riesgo: -")
        self._alertas_var = tk.StringVar(value="Alertas: -")
        self._evidencia_var = tk.StringVar(value="Evidencia: -")
        self._zona_var = tk.StringVar(value="Zona: -")

        self._make_panel(side, "Fuente", [
            self._fuente_var, self._conexion_var, self._resolucion_var,
            self._fps_var,
        ])
        self._make_panel(side, "Seguimiento", [
            self._track_var, self._permanencia_var, self._zona_var,
        ])
        self._make_panel(side, "Riesgo", [self._riesgo_var])
        self._make_panel(side, "Alertas", [self._alertas_var])
        self._make_panel(side, "Evidencia", [self._evidencia_var])

        # Controles
        controls = ttk.Frame(self._root, padding=(10, 8))
        controls.pack(fill=tk.X)
        controls.columnconfigure(1, weight=0)

        self._source_var = tk.StringVar(value="FILE")
        ttk.Label(controls, text="Fuente:").grid(row=0, column=0, sticky=tk.W)
        ttk.OptionMenu(
            controls, self._source_var, "FILE", "FILE", "WEBCAM", "RTSP",
            command=self._on_source_change,
        ).grid(row=0, column=1, padx=(4, 8), sticky=tk.W)

        # Campo libre usado por FILE (ruta) y WEBCAM (índice).
        self._input_var = tk.StringVar(value="")
        self._input_entry = ttk.Entry(controls, textvariable=self._input_var, width=34)
        self._input_entry.grid(row=0, column=2, padx=(0, 8), sticky=tk.W)

        # Campos RTSP separados: la contraseña va enmascarada (show="*")
        # y la URL con credenciales se construye en memoria al iniciar,
        # sin exponerla en pantalla (LOOP-0013-HOTFIX, SECURE_RTSP_UI_GAP).
        self._rtsp_host_var = tk.StringVar(value="rtsp://")
        self._rtsp_user_var = tk.StringVar(value="")
        self._rtsp_pass_var = tk.StringVar(value="")
        self._rtsp_frame = ttk.Frame(controls)
        self._rtsp_frame.grid(row=0, column=3, padx=(0, 8), sticky=tk.W)
        ttk.Label(self._rtsp_frame, text="Host:").pack(side=tk.LEFT)
        self._rtsp_host_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_host_var, width=22
        )
        self._rtsp_host_entry.pack(side=tk.LEFT, padx=(2, 6))
        ttk.Label(self._rtsp_frame, text="Usuario:").pack(side=tk.LEFT)
        self._rtsp_user_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_user_var, width=10
        )
        self._rtsp_user_entry.pack(side=tk.LEFT, padx=(2, 6))
        ttk.Label(self._rtsp_frame, text="Contraseña:").pack(side=tk.LEFT)
        self._rtsp_pass_entry = ttk.Entry(
            self._rtsp_frame, textvariable=self._rtsp_pass_var, width=10,
            show="*",
        )
        self._rtsp_pass_entry.pack(side=tk.LEFT, padx=(2, 6))

        self._file_btn = ttk.Button(
            controls, text="Seleccionar archivo", command=self._on_select_file
        )
        self._file_btn.grid(row=0, column=4, padx=(0, 8), sticky=tk.W)

        self._start_btn = ttk.Button(
            controls, text="Iniciar", command=self._on_start
        )
        self._start_btn.grid(row=0, column=5, padx=(0, 4), sticky=tk.W)

        self._stop_btn = ttk.Button(
            controls, text="Detener", command=self._on_stop, state=tk.DISABLED
        )
        self._stop_btn.grid(row=0, column=6, padx=(0, 8), sticky=tk.W)

        ttk.Button(
            controls, text="Abrir evidencia", command=self._on_open_evidence
        ).grid(row=0, column=7, sticky=tk.W)

        self._on_source_change("FILE")

        self._root.after(self.POLL_MS, self._poll)

    def _make_panel(self, parent, title, vars_):
        panel = ttk.LabelFrame(parent, text=title, padding=(8, 6))
        panel.pack(fill=tk.X, pady=(0, 8))
        for var in vars_:
            ttk.Label(panel, textvariable=var, wraplength=300).pack(
                fill=tk.X, anchor=tk.W
            )

    def _on_source_change(self, kind: str) -> None:
        if kind == "FILE":
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("")
            self._file_btn.configure(state=tk.NORMAL)
            self._input_entry.grid()
            self._rtsp_frame.grid_remove()
        elif kind == "WEBCAM":
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("0")
            self._file_btn.configure(state=tk.DISABLED)
            self._input_entry.grid()
            self._rtsp_frame.grid_remove()
        else:  # RTSP
            self._input_entry.grid_remove()
            self._file_btn.configure(state=tk.DISABLED)
            self._rtsp_frame.grid()

    def _on_select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")],
        )
        if path:
            self._input_var.set(path)

    def _on_start(self) -> None:
        kind = self._source_var.get()
        if kind == "RTSP":
            value = build_rtsp_url(
                self._rtsp_host_var.get(),
                self._rtsp_user_var.get(),
                self._rtsp_pass_var.get(),
            )
            if not value or not value.startswith("rtsp://"):
                messagebox.showwarning(
                    "Fuente", "Para RTSP ingrese una URL base válida"
                )
                return
        else:
            value = self._input_var.get()
            if kind == "FILE" and not value:
                messagebox.showwarning("Fuente", "Seleccione un archivo de video")
                return
        try:
            self._controller.start(kind, value)
        except ValueError as e:
            messagebox.showerror("Inicio", str(e))
            return
        self._start_btn.configure(state=tk.DISABLED)
        self._stop_btn.configure(state=tk.NORMAL)

    def _on_stop(self) -> None:
        self._controller.stop()
        self._start_btn.configure(state=tk.NORMAL)
        self._stop_btn.configure(state=tk.DISABLED)

    def _on_open_evidence(self) -> None:
        base = os.path.abspath("data/evidence")
        if os.path.isdir(base):
            os.startfile(base)
        else:
            messagebox.showinfo("Evidencia", "No existe carpeta de evidencia")

    def _on_close(self) -> None:
        try:
            self._controller.close()
        finally:
            self._root.destroy()

    def _poll(self) -> None:
        if not self._root.winfo_exists():
            return
        try:
            self._poll_once()
        finally:
            try:
                self._root.after(self.POLL_MS, self._poll)
            except tk.TclError:
                pass

    def _poll_once(self) -> None:
        state = self._controller.poll_state()
        self._render_video(state)
        self._render_panels(state)
        self._render_status(state)

    def _render_video(self, state: dict) -> None:
        if state["status"] == AppStatus.RUNNING:
            panels = self._controller.poll_multicamera()
            for camera_id in CAMERA_IDS:
                panel = panels[camera_id]
                self._camera_state_vars[camera_id].set(
                    f"Estado: {panel.source_state}"
                )
                if panel.frame is not None and panel.frame_index >= 0:
                    self._set_photo(camera_id, panel.frame, panel.frame_index)

    def _set_photo(self, camera_id, frame, frame_index) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ok, buf = cv2.imencode(".png", rgb)
        if not ok:
            return
        try:
            photo = tk.PhotoImage(data=buf.tobytes())
        except tk.TclError:
            return
        self._photos[camera_id] = photo
        self._video_labels[camera_id].configure(image=photo, text="")

    def _render_panels(self, state: dict) -> None:
        self._fuente_var.set(f"Fuente: {state['source_path_display'] or '-'}")
        self._conexion_var.set(f"Conexión: {state['source_state'] or '-'}")
        self._resolucion_var.set(f"Resolución: {state['resolution'] or '-'}")
        self._fps_var.set(f"FPS: {state['fps']:.1f}" if state["fps"] else "FPS: -")
        self._zona_var.set(f"Zona: {state['zone_id']} {state['zone_name']}")
        if state["followed_track"] is not None:
            self._track_var.set(f"Track ID: {state['followed_track']}")
            self._permanencia_var.set(
                f"Permanencia: {state['permanence_seconds']:.1f}s"
            )
        else:
            self._track_var.set("Track ID: -")
            self._permanencia_var.set("Permanencia: -")

        # Riesgo real del núcleo: score real si existe, si no el texto del núcleo, si no "—"
        risk = state["latest_risk_score"]
        if risk is not None:
            self._riesgo_var.set(f"Riesgo: {risk}/100")
        elif state["risk_text"]:
            self._riesgo_var.set(f"Riesgo: {state['risk_text']}")
        else:
            self._riesgo_var.set("Riesgo: —")

        if state["alert_log"]:
            last = state["alert_log"][-1]
            self._alertas_var.set(
                f"Alertas: {last['alert_id']} / evento {last['event_id']} / "
                f"riesgo {last['risk_score']} / {last['created_at']}"
            )
        else:
            self._alertas_var.set("Alertas: -")
        if state["evidence_paths"]:
            self._evidencia_var.set(
                f"Evidencia: {state['evidence_paths'][-1]}"
            )
        else:
            self._evidencia_var.set("Evidencia: -")

    def _render_status(self, state: dict) -> None:
        if state["status"] == AppStatus.RUNNING:
            text = "Estado: EN EJECUCIÓN"
            color = "#1a6b1a"
        elif state["error"]:
            text = f"Estado: ERROR - {state['error']}"
            color = "#b00000"
        else:
            text = f"Estado: DETENIDO ({state['final_status']})"
            color = "#555555"
        self._status_var.set(text)
        self._status_var_color(color)

    def _status_var_color(self, color: str) -> None:
        for w in self._root.winfo_children():
            for child in w.winfo_children():
                if isinstance(child, ttk.Label) and child.cget("textvariable") == str(self._status_var):
                    child.configure(foreground=color)
                    return

    def run(self) -> None:
        self._root.mainloop()
