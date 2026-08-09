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

from src.ui.state import AppStatus


class TkApp:
    """Ventana principal de la interfaz operativa."""

    POLL_MS = 33

    def __init__(self, root: tk.Tk, controller) -> None:
        self._root = root
        self._controller = controller
        self._photo = None
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
        self._video_label = ttk.Label(video_frame)
        self._video_label.pack(fill=tk.BOTH, expand=True)

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

        self._source_var = tk.StringVar(value="FILE")
        ttk.Label(controls, text="Fuente:").pack(side=tk.LEFT)
        ttk.OptionMenu(
            controls, self._source_var, "FILE", "FILE", "WEBCAM", "RTSP",
            command=self._on_source_change,
        ).pack(side=tk.LEFT, padx=(4, 8))

        self._input_var = tk.StringVar(value="")
        self._input_entry = ttk.Entry(controls, textvariable=self._input_var, width=34)
        self._input_entry.pack(side=tk.LEFT, padx=(0, 8))

        self._file_btn = ttk.Button(
            controls, text="Seleccionar archivo", command=self._on_select_file
        )
        self._file_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._start_btn = ttk.Button(
            controls, text="Iniciar", command=self._on_start
        )
        self._start_btn.pack(side=tk.LEFT, padx=(0, 4))

        self._stop_btn = ttk.Button(
            controls, text="Detener", command=self._on_stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            controls, text="Abrir evidencia", command=self._on_open_evidence
        ).pack(side=tk.LEFT)

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
        elif kind == "WEBCAM":
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("0")
            self._file_btn.configure(state=tk.DISABLED)
        else:  # RTSP
            self._input_entry.configure(state=tk.NORMAL)
            self._input_var.set("")
            self._file_btn.configure(state=tk.DISABLED)

    def _on_select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar video",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv"), ("Todos", "*.*")],
        )
        if path:
            self._input_var.set(path)

    def _on_start(self) -> None:
        kind = self._source_var.get()
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
            snapshot = self._controller.poll_visual()
            if snapshot is not None and snapshot.frame_index != self._last_frame_index:
                self._last_frame_index = snapshot.frame_index
                self._set_photo(snapshot.frame)

    def _set_photo(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ok, buf = cv2.imencode(".png", rgb)
        if not ok:
            return
        try:
            self._photo = tk.PhotoImage(data=buf.tobytes())
        except tk.TclError:
            return
        self._video_label.configure(image=self._photo)

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
