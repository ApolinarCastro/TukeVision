"""CONFIGURACIÓN -> DISPOSITIVOS: operator admin view (MACRO-OC-02 BLOCKS M/N/O).

Rules enforced here:

  - No manual JSON editing: every change goes through
    ``src.deployment.device_config`` (save_store / save_recorder / save_camera /
    set_store_enabled / set_recorder_enabled), which validates, writes
    atomically, reloads StoreCatalog and confirms before returning.
  - Passwords are a ``credentials_ref`` and are NEVER persisted as plaintext;
    the password field is masked, kept in memory only and cleared after use.
  - Operator-visible gates (BLOCK O): explicit ``+ NUEVA TIENDA`` and
    ``+ NUEVO DISPOSITIVO`` buttons; cameras of the selected recorder are
    listed (nombre, canal, zona, enabled) and editable.
"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional
import tkinter as tk

from src.deployment.device_config import (
    read_recorders,
    read_stores,
    save_camera,
    save_recorder,
    save_store,
    set_recorder_enabled,
    set_store_enabled,
    tcp_reachable,
    probe_first_frame,
    primary_subtype_for,
)

RECORDER_TYPES = ("DVR", "NVR", "VMS_BRIDGE", "VIRTUAL_MATRIX")
PROFILES = ("main", "sub")
NEW_RECORDER = "++ Nuevo dispositivo ++"
NEW_STORE = "++ Nueva tienda ++"

_FIELD_LABELS = {
    "recorder_name": "Nombre dispositivo:",
    "recorder_type": "Tipo / Vendor:",
    "vendor": "Vendor:",
    "host": "IP / Host:",
    "port": "RTSP port:",
    "device_port": "Device port (opcional):",
    "username_default": "Usuario:",
    "password": "Contraseña:",
    "physical_channels": "Canales físicos:",
    "stream_profile": "Stream profile:",
}


class StoreEditorWindow(tk.Toplevel):
    """Add / edit a store through the safe backend (BLOCK M TIENDAS)."""

    def __init__(self, parent, config_path, store: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._config_path = Path(config_path)
        self._store = store
        self.title("Tienda · Nueva / Editar")
        self.geometry("420x300")
        self.resizable(False, False)
        self.transient(parent)
        self.configure(bg="#0F172A")
        self._build()

    def _entry(self, form, row, label, value):
        tk.Label(
            form, text=label, bg="#0F172A", fg="#94A3B8",
            font=("Segoe UI", 9),
        ).grid(row=row, column=0, sticky=tk.W, pady=4)
        var = tk.StringVar(value=value)
        widget = ttk.Entry(form, textvariable=var, width=32)
        widget.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=4)
        return var

    def _build(self) -> None:
        form = tk.Frame(self, bg="#0F172A")
        form.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        store = self._store or {}
        self._store_id = self._entry(
            form, 0, "store_id:", store.get("store_id", "")
        )
        if store:
            self._store_id.set(store["store_id"])
        self._store_name = self._entry(
            form, 1, "Nombre tienda:", store.get("store_name", "")
        )
        self._org_id = self._entry(
            form, 2, "organization_id:", store.get("organization_id", "org_default")
        )
        self._org_name = self._entry(
            form, 3, "organization_name:", store.get("organization_name", "")
        )
        self._timezone = self._entry(
            form, 4, "timezone:", store.get("timezone", "America/Santiago")
        )
        self._enabled = tk.BooleanVar(value=bool(store.get("enabled", True)))
        tk.Checkbutton(
            form, text="Habilitada (cámaras activas)", variable=self._enabled,
            bg="#0F172A", fg="#94A3B8", selectcolor="#0F172A",
            activebackground="#0F172A", activeforeground="#94A3B8",
            font=("Segoe UI", 9), cursor="hand2",
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        actions = tk.Frame(self, bg="#0F172A")
        actions.pack(fill=tk.X, padx=16, pady=(0, 12))
        tk.Button(
            actions, text="GUARDAR TIENDA", command=self._on_save,
            relief=tk.FLAT, bg="#1B3A5A", fg="#38BDF8",
            activebackground="#10192E", activeforeground="#38BDF8",
            font=("Segoe UI", 9, "bold"), padx=14, pady=4, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        ).pack(side=tk.LEFT)

    def _field(self, var) -> str:
        return (var.get() or "").strip()

    def _on_save(self) -> None:
        fields = {
            "store_id": self._field(self._store_id),
            "store_name": self._field(self._store_name),
            "organization_id": self._field(self._org_id),
            "organization_name": self._field(self._org_name),
            "timezone": self._field(self._timezone),
            "enabled": self._enabled.get(),
        }
        try:
            save_store(self._config_path, fields)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al guardar", str(exc), parent=self)
            return
        self.destroy()


class DeviceSettingsWindow(tk.Toplevel):
    """Admin form to add/edit stores, recorders and cameras (BLOCK M)."""

    def __init__(self, parent, config_path, config: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._config_path = Path(config_path)
        self._config = config if config is not None else self._load_config()
        self.title("Configuración · Dispositivos")
        self.geometry("680x760")
        self.resizable(True, True)
        self.transient(parent)
        self.configure(bg="#0F172A")
        self._busy = False
        self._build()

    def _load_config(self) -> dict:
        import json

        with open(self._config_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _stores(self) -> list:
        return [
            store.get("store_id", "")
            for store in self._config.get("multistore", {}).get("stores", [])
        ]

    def _store_detail(self, store_id: str) -> Optional[dict]:
        for store in read_stores(self._config_path):
            if store["store_id"] == store_id:
                return store
        return None

    def _recorders_for_store(self, store_id: str) -> list:
        return [
            r for r in read_recorders(self._config_path) if r["store_id"] == store_id
        ]

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        stores = self._stores()

        header = tk.Label(
            self, text="ADMIN · TIENDAS / DISPOSITIVOS / CÁMARAS",
            bg="#0F172A", fg="#38BDF8", font=("Segoe UI", 10, "bold"),
        )
        header.pack(fill=tk.X, padx=16, pady=(12, 4))

        # ---- TIENDAS ----
        store_row = tk.Frame(self, bg="#0F172A")
        store_row.pack(fill=tk.X, padx=16, pady=(0, 4))
        tk.Label(
            store_row, text="TIENDA", bg="#0F172A", fg="#38BDF8",
            font=("Segoe UI", 9, "bold"), width=10, anchor=tk.W,
        ).pack(side=tk.LEFT)
        self._store_var = tk.StringVar(value=stores[0] if stores else NEW_STORE)
        self._store_combo = ttk.Combobox(
            store_row, textvariable=self._store_var, values=stores or [NEW_STORE],
            state="readonly", width=26,
        )
        self._store_combo.pack(side=tk.LEFT, padx=(0, 8))
        self._store_combo.bind("<<ComboboxSelected>>", lambda e: self._on_store_change())
        tk.Button(
            store_row, text="+ NUEVA TIENDA", command=self._on_add_store,
            relief=tk.FLAT, bg="#1B3A5A", fg="#22C55E",
            activebackground="#10192E", activeforeground="#22C55E",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            store_row, text="EDITAR TIENDA", command=self._on_edit_store,
            relief=tk.FLAT, bg="#1B3A5A", fg="#38BDF8",
            activebackground="#10192E", activeforeground="#38BDF8",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            store_row, text="DESHABILITAR", command=self._on_disable_store,
            relief=tk.FLAT, bg="#3A1B2A", fg="#EF4444",
            activebackground="#2E1019", activeforeground="#EF4444",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#5E2E3D",
        ).pack(side=tk.LEFT, padx=2)

        # ---- DISPOSITIVO ----
        rec_row = tk.Frame(self, bg="#0F172A")
        rec_row.pack(fill=tk.X, padx=16, pady=(4, 4))
        tk.Label(
            rec_row, text="DISPOSITIVO", bg="#0F172A", fg="#38BDF8",
            font=("Segoe UI", 9, "bold"), width=10, anchor=tk.W,
        ).pack(side=tk.LEFT)
        self._recorder_var = tk.StringVar(value=NEW_RECORDER)
        self._recorder_combo = ttk.Combobox(
            rec_row, textvariable=self._recorder_var, values=[NEW_RECORDER],
            state="readonly", width=26,
        )
        self._recorder_combo.pack(side=tk.LEFT, padx=(0, 8))
        self._recorder_combo.bind("<<ComboboxSelected>>", lambda e: self._on_recorder_change())
        tk.Button(
            rec_row, text="+ NUEVO DISPOSITIVO", command=self._on_new_recorder,
            relief=tk.FLAT, bg="#1B3A5A", fg="#22C55E",
            activebackground="#10192E", activeforeground="#22C55E",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            rec_row, text="DESHABILITAR", command=self._on_disable_recorder,
            relief=tk.FLAT, bg="#3A1B2A", fg="#EF4444",
            activebackground="#2E1019", activeforeground="#EF4444",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#5E2E3D",
        ).pack(side=tk.LEFT, padx=2)

        # ---- Recorder form ----
        form = tk.Frame(self, bg="#0F172A")
        form.pack(fill=tk.X, padx=16, pady=(4, 4))
        self._entries: dict = {}
        row = 0
        for key, label in _FIELD_LABELS.items():
            tk.Label(
                form, text=label, bg="#0F172A", fg="#94A3B8",
                font=("Segoe UI", 9),
            ).grid(row=row, column=0, sticky=tk.W, pady=2)
            if key == "recorder_type":
                var = tk.StringVar(value="DVR")
                widget = ttk.Combobox(
                    form, textvariable=var, values=RECORDER_TYPES,
                    state="readonly", width=26,
                )
            elif key == "stream_profile":
                var = tk.StringVar(value="main")
                widget = ttk.Combobox(
                    form, textvariable=var, values=PROFILES, state="readonly", width=26
                )
            elif key == "physical_channels":
                var = tk.StringVar(value="15")
                widget = ttk.Spinbox(form, from_=1, to=128, textvariable=var, width=26)
            elif key == "password":
                var = tk.StringVar(value="")
                widget = ttk.Entry(form, textvariable=var, width=26, show="*")
            else:
                var = tk.StringVar(value="")
                widget = ttk.Entry(form, textvariable=var, width=26)
            widget.grid(row=row, column=1, sticky=tk.W, pady=2, padx=(8, 0))
            self._entries[key] = (var, widget)
            row += 1

        actions = tk.Frame(self, bg="#0F172A")
        actions.pack(fill=tk.X, padx=16, pady=(2, 6))
        self._save_btn = tk.Button(
            actions, text="GUARDAR", command=self._on_save,
            relief=tk.FLAT, bg="#1B3A5A", fg="#38BDF8",
            activebackground="#10192E", activeforeground="#38BDF8",
            font=("Segoe UI", 9, "bold"), padx=14, pady=4, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        )
        self._save_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._test_btn = tk.Button(
            actions, text="PROBAR CONEXIÓN", command=self._on_test,
            relief=tk.FLAT, bg="#1B3A5A", fg="#22C55E",
            activebackground="#10192E", activeforeground="#22C55E",
            font=("Segoe UI", 9, "bold"), padx=14, pady=4, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        )
        self._test_btn.pack(side=tk.LEFT)
        self._test_status = tk.StringVar(value="")
        tk.Label(
            actions, textvariable=self._test_status, bg="#0F172A", fg="#94A3B8",
            font=("Segoe UI", 8), wraplength=380, justify=tk.LEFT,
        ).pack(side=tk.LEFT, padx=(12, 0))

        # ---- CÁMARAS ----
        cam_frame = tk.Frame(self, bg="#0F172A")
        cam_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(2, 4))
        tk.Label(
            cam_frame, text="CÁMARAS DEL RECORDER",
            bg="#0F172A", fg="#38BDF8", font=("Segoe UI", 9, "bold"),
        ).pack(anchor=tk.W, pady=(0, 2))
        columns = ("channel", "camera_id", "camera_name", "zone", "enabled")
        self._cam_tree = ttk.Treeview(
            cam_frame, columns=columns, show="headings", height=8,
            selectmode="browse",
        )
        for col, title, width in (
            ("channel", "Canal", 46), ("camera_id", "ID", 70),
            ("camera_name", "Nombre", 130), ("zone", "Zona", 90),
            ("enabled", "Activa", 56),
        ):
            self._cam_tree.heading(col, text=title)
            self._cam_tree.column(col, width=width, anchor=tk.W)
        self._cam_tree.pack(fill=tk.BOTH, expand=True)
        self._cam_tree.bind("<<TreeviewSelect>>", lambda e: self._on_camera_select())

        edit_row = tk.Frame(cam_frame, bg="#0F172A")
        edit_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(
            edit_row, text="Nombre:", bg="#0F172A", fg="#94A3B8",
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT)
        self._cam_name_var = tk.StringVar(value="")
        ttk.Entry(edit_row, textvariable=self._cam_name_var, width=18).pack(
            side=tk.LEFT, padx=(4, 10)
        )
        tk.Label(
            edit_row, text="Zona:", bg="#0F172A", fg="#94A3B8",
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT)
        self._cam_zone_var = tk.StringVar(value="")
        ttk.Entry(edit_row, textvariable=self._cam_zone_var, width=12).pack(
            side=tk.LEFT, padx=(4, 10)
        )
        self._cam_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            edit_row, text="Activa", variable=self._cam_enabled_var,
            bg="#0F172A", fg="#94A3B8", selectcolor="#0F172A",
            activebackground="#0F172A", activeforeground="#94A3B8",
            font=("Segoe UI", 9), cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(
            edit_row, text="GUARDAR CÁMARA", command=self._on_save_camera,
            relief=tk.FLAT, bg="#1B3A5A", fg="#38BDF8",
            activebackground="#10192E", activeforeground="#38BDF8",
            font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2",
            borderwidth=1, highlightbackground="#2E3D5E",
        ).pack(side=tk.LEFT)

        self._on_store_change()

    # ---------------------------------------------------------------- helpers
    def _field(self, key: str) -> str:
        return (self._entries[key][0].get() or "").strip()

    def _set_status(self, text: str) -> None:
        self._test_status.set(text)

    def _reload(self) -> None:
        self._config = self._load_config()

    # -------------------------------------------------------------- stores
    def _on_add_store(self) -> None:
        StoreEditorWindow(self, self._config_path).wait_window()
        self._reload()
        self._on_store_change()

    def _on_edit_store(self) -> None:
        store_id = self._store_var.get()
        detail = self._store_detail(store_id) if store_id else None
        if detail is None:
            messagebox.showinfo("Tienda", "Seleccione una tienda existente", parent=self)
            return
        StoreEditorWindow(self, self._config_path, detail).wait_window()
        self._reload()
        self._on_store_change()

    def _on_disable_store(self) -> None:
        store_id = self._store_var.get()
        if not store_id or store_id == NEW_STORE:
            messagebox.showinfo("Tienda", "Seleccione una tienda", parent=self)
            return
        detail = self._store_detail(store_id)
        if detail is not None and not detail.get("enabled", True):
            messagebox.showinfo("Tienda", f"{store_id} ya está deshabilitada", parent=self)
            return
        if not messagebox.askyesno(
            "Deshabilitar tienda",
            f"¿Deshabilitar {store_id}? Sus cámaras dejarán de operar.",
            parent=self,
        ):
            return
        try:
            result = set_store_enabled(self._config_path, store_id, False)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._reload()
        self._on_store_change()
        self._set_status(f"Tienda {result['store_id']} deshabilitada.")

    # -------------------------------------------------------------- recorders
    def _on_new_recorder(self) -> None:
        self._recorder_var.set(NEW_RECORDER)
        self._populate_defaults()

    def _on_disable_recorder(self) -> None:
        store_id = self._store_var.get()
        recorder_id = self._recorder_var.get()
        if not store_id or not recorder_id or recorder_id == NEW_RECORDER:
            messagebox.showinfo("Dispositivo", "Seleccione un dispositivo", parent=self)
            return
        if not messagebox.askyesno(
            "Deshabilitar dispositivo",
            f"¿Deshabilitar {recorder_id}? Sus cámaras dejarán de operar.",
            parent=self,
        ):
            return
        try:
            result = set_recorder_enabled(self._config_path, store_id, recorder_id, False)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self._reload()
        self._on_store_change()
        self._set_status(f"Dispositivo {result['recorder_id']} deshabilitado.")

    # ------------------------------------------------------------------ events
    def _on_store_change(self) -> None:
        store_id = self._store_var.get()
        recorders = self._recorders_for_store(store_id) if store_id else []
        values = [r["recorder_id"] for r in recorders]
        self._recorder_combo.configure(values=values + [NEW_RECORDER])
        self._recorder_var.set(values[-1] if values else NEW_RECORDER)
        self._on_recorder_change()

    def _on_recorder_change(self) -> None:
        selected = self._recorder_var.get()
        store_id = self._store_var.get()
        recorder = None
        for r in self._recorders_for_store(store_id):
            if r["recorder_id"] == selected:
                recorder = r
                break
        if recorder is None:
            self._populate_defaults()
            self._render_cameras([])
            return
        self._entries["recorder_name"][0].set(recorder["recorder_name"])
        self._entries["recorder_type"][0].set(recorder["recorder_type"])
        self._entries["vendor"][0].set(recorder["vendor"])
        self._entries["host"][0].set(recorder["host"])
        self._entries["port"][0].set(recorder["port"])
        self._entries["device_port"][0].set(
            recorder["device_port"] if recorder["device_port"] else ""
        )
        self._entries["username_default"][0].set(recorder["username_default"])
        self._entries["physical_channels"][0].set(recorder["physical_channels"])
        self._entries["stream_profile"][0].set(recorder["stream_profile"])
        self._entries["password"][0].set("")
        self._set_status(f"Editando {selected}. La contraseña se mantiene segura.")
        self._render_cameras(self._cameras_for_recorder(store_id, selected))

    def _cameras_for_recorder(self, store_id: str, recorder_id: str) -> list:
        for r in self._recorders_for_store(store_id):
            if r["recorder_id"] == recorder_id:
                return list(r.get("camera_ids") or [])
        return []

    def _render_cameras(self, camera_ids: list) -> None:
        for item in self._cam_tree.get_children():
            self._cam_tree.delete(item)
        recorder_id = self._recorder_var.get()
        store_id = self._store_var.get()
        for r in self._recorders_for_store(store_id):
            if r["recorder_id"] != recorder_id:
                continue
            config_store = self._store_config(store_id)
            recorder_cfg = next(
                (rec for rec in config_store.get("recorders", [])
                 if rec.get("recorder_id") == recorder_id), None
            )
            if recorder_cfg is None:
                return
            for cam in recorder_cfg.get("cameras", []):
                self._cam_tree.insert(
                    "", "end", iid=cam.get("camera_id"),
                    values=(
                        cam.get("channel_number", ""),
                        cam.get("camera_id", ""),
                        cam.get("camera_name", ""),
                        cam.get("zone", ""),
                        "SÍ" if cam.get("enabled", True) else "NO",
                    ),
                )
            return

    def _store_config(self, store_id: str) -> Optional[dict]:
        for store in self._config.get("multistore", {}).get("stores", []):
            if store.get("store_id") == store_id:
                return store
        return None

    def _on_camera_select(self) -> None:
        selected = self._cam_tree.selection()
        if not selected:
            return
        camera_id = selected[0]
        store_id = self._store_var.get()
        recorder_id = self._recorder_var.get()
        store = self._store_config(store_id)
        if store is None:
            return
        for rec in store.get("recorders", []):
            if rec.get("recorder_id") != recorder_id:
                continue
            for cam in rec.get("cameras", []):
                if cam.get("camera_id") == camera_id:
                    self._cam_name_var.set(cam.get("camera_name", ""))
                    self._cam_zone_var.set(cam.get("zone", ""))
                    self._cam_enabled_var.set(bool(cam.get("enabled", True)))
                    return

    def _on_save_camera(self) -> None:
        selected = self._cam_tree.selection()
        if not selected:
            messagebox.showinfo("Cámara", "Seleccione una cámara", parent=self)
            return
        store_id = self._store_var.get()
        recorder_id = self._recorder_var.get()
        if not store_id or not recorder_id:
            messagebox.showinfo("Cámara", "Faltan tienda/dispositivo", parent=self)
            return
        fields = {
            "camera_name": self._cam_name_var.get(),
            "zone": self._cam_zone_var.get(),
            "enabled": self._cam_enabled_var.get(),
        }
        try:
            save_camera(self._config_path, store_id, recorder_id, selected[0], fields)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al guardar cámara", str(exc), parent=self)
            return
        self._reload()
        self._render_cameras(self._cameras_for_recorder(store_id, recorder_id))
        self._set_status(f"Cámara {selected[0]} guardada.")

    def _populate_defaults(self) -> None:
        for key in self._entries:
            if key in ("physical_channels",):
                self._entries[key][0].set("15")
            elif key == "stream_profile":
                self._entries[key][0].set("main")
            elif key == "recorder_type":
                self._entries[key][0].set("DVR")
            elif key == "password":
                self._entries[key][0].set("")
            else:
                self._entries[key][0].set("")

    # ---------------------------------------------------------------- actions
    def _on_save(self) -> None:
        store_id = self._store_var.get()
        if not store_id:
            messagebox.showerror("Error", "Seleccione una tienda", parent=self)
            return
        recorder_id = self._recorder_var.get()
        is_new = recorder_id == NEW_RECORDER
        if is_new:
            base = self._field("host") or "dvr"
            import re

            recorder_id = re.sub(r"[^A-Za-z0-9_-]", "_", base) or "dvr"
            if not recorder_id.startswith("dvr"):
                recorder_id = f"dvr_{recorder_id}"
        try:
            physical = int(self._field("physical_channels") or 0)
        except ValueError:
            messagebox.showerror("Error", "Canales físicos debe ser numérico", parent=self)
            return
        fields = {
            "recorder_id": recorder_id,
            "recorder_name": self._field("recorder_name") or recorder_id,
            "recorder_type": self._field("recorder_type") or "DVR",
            "vendor": self._field("vendor"),
            "host": self._field("host"),
            "port": self._field("port") or 554,
            "device_port": self._field("device_port") or None,
            "username_default": self._field("username_default") or "admin",
            "stream_profile": self._field("stream_profile") or "main",
            "physical_channels": physical,
        }
        try:
            saved = save_recorder(self._config_path, store_id, fields)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error al guardar", str(exc), parent=self)
            return
        # Password is never persisted: clear it from the widget.
        self._entries["password"][0].set("")
        self._reload()
        self._on_store_change()
        self._recorder_var.set(saved["recorder_id"])
        self._on_recorder_change()
        self._set_status(
            f"Guardado: {saved['recorder_id']} "
            f"({saved['physical_channels']} canales físicos). "
            "Credencial sin cambios (referencia segura)."
        )

    def _on_test(self) -> None:
        if self._busy:
            return
        host = self._field("host")
        if not host:
            messagebox.showerror("Error", "Indique IP / Host", parent=self)
            return
        try:
            port = int(self._field("port") or 554)
        except ValueError:
            messagebox.showerror("Error", "RTSP port inválido", parent=self)
            return
        username = self._field("username_default") or "admin"
        password = self._entries["password"][0].get()
        profile = self._field("stream_profile") or "main"
        subtype = primary_subtype_for(profile)
        self._busy = True
        self._test_btn.configure(state=tk.DISABLED)
        self._save_btn.configure(state=tk.DISABLED)
        self._set_status("Probando conexión (acotado)...")

        def worker() -> None:
            result = {"ok": False, "error": "NO_TCP"}
            if tcp_reachable(host, port, timeout=3.0):
                result = probe_first_frame(
                    host=host,
                    port=port,
                    channel=1,
                    subtype=subtype,
                    username=username,
                    password=password,
                    timeout_s=6.0,
                )
            self._finish_test(result)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_test(self, result: dict) -> None:
        try:
            self.after(0, lambda: self._apply_test_result(result))
        except tk.TclError:
            pass

    def _apply_test_result(self, result: dict) -> None:
        self._busy = False
        self._test_btn.configure(state=tk.NORMAL)
        self._save_btn.configure(state=tk.NORMAL)
        if result.get("ok"):
            self._set_status(f"OK · primer fotograma real {result['resolution']}")
            self._test_btn.configure(fg="#22C55E")
        else:
            self._set_status(f"Sin conexión: {result.get('error', 'NO_TCP')}")
            self._test_btn.configure(fg="#EF4444")


__all__ = ["DeviceSettingsWindow", "StoreEditorWindow"]