"""TukeVisionReviewWindow — human review as product UI (DEF-UI-REVIEW-01).

Adapter over the existing QW-00 review logic, never a duplicate datastore:

  - the dataset is the canonical JSONL exported by ``BoundedReviewExporter``
    (``src/review``), located either via the provider (``review_target`` /
    ``review_records()``) or the canonical ``dataset_path`` discovery;
  - persistence reuses the existing atomic CSV matrix writer + metrics
    (``scripts.review_behavior_signals.save`` / ``write_metrics``), so the
    review state changes in the SAME files the operator tool used;
  - the 1..5 classifications are the existing semantic labels from
    ``src.review.contracts.ALLOWED_CLASSIFICATIONS`` (nothing invented).

The window is a Tk modal inside TukeVision. It never spawns a CMD console.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional
import tkinter as tk

from src.review.contracts import ALLOWED_CLASSIFICATIONS

EMPTY_STATE_TEXT = "No hay revisiones pendientes"
CLIP_UNAVAILABLE_TEXT = "Clip no disponible"
JPEG_UNAVAILABLE_TEXT = "JPEG no disponible"

CLASSIFICATIONS = tuple(
    item for item in ALLOWED_CLASSIFICATIONS if item != "NOT_REVIEWED"
)

_BG = "#0F172A"
_PANEL = "#192134"
_TEXT = "#E6E8EE"
_TEXT_DIM = "#94A3B8"
_BORDER = "#2E3D5E"
_ACCENT = "#38BDF8"


class TukeVisionReviewWindow(tk.Toplevel):
    """Modal review window bound to the existing QW-00 dataset and matrix."""

    def __init__(
        self,
        master,
        provider=None,
        *,
        records: Optional[List[dict]] = None,
        matrix_path=None,
        evidence_root=None,
        opener: Optional[Callable[[str], bool]] = None,
    ) -> None:
        super().__init__(master)
        self._provider = provider
        self._opener = opener or self._default_opener()
        self._explicit_matrix = matrix_path
        self._explicit_evidence_root = evidence_root
        self._records, self._records_source = self._load_records(records)
        self._matrix_path = self._resolve_matrix_path()
        self._existing = self._load_existing_matrix()
        self._session: dict = {}
        self._index = 0
        self._photo = None
        self.title("Revisión humana · QW-00")
        self.configure(bg=_BG)
        self.minsize(640, 520)
        if self._records and self._pending_ids():
            self._build_review()
            self._go_to(self._first_pending_index())
        else:
            self._build_empty()

    # ------------------------------------------------------------------
    # data access (adapter over existing review logic)
    # ------------------------------------------------------------------
    @staticmethod
    def _default_opener():
        startfile = getattr(os, "startfile", None)
        if startfile is not None:
            return lambda path: bool(startfile(path))
        return lambda path: False

    def _load_records(self, explicit):
        if explicit is not None:
            return list(explicit), None
        provider = self._provider
        if provider is not None:
            reader = getattr(provider, "review_records", None)
            if not callable(reader):
                reader = getattr(provider, "_review_records", None)
            if callable(reader):
                try:
                    loaded = tuple(reader())
                except Exception:  # noqa: BLE001 - provider failure
                    return [], None
                return list(loaded), None
        try:
            from scripts.review_behavior_signals import dataset_path
        except Exception:  # noqa: BLE001
            return [], None
        try:
            source = dataset_path()
        except Exception:  # noqa: BLE001
            return [], None
        if source is None:
            return [], None
        try:
            records = [
                json.loads(line)
                for line in source.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, ValueError):
            return [], None
        return records, Path(source)

    def _resolve_matrix_path(self):
        if self._explicit_matrix is not None:
            return Path(self._explicit_matrix)
        provider = self._provider
        if provider is not None:
            target = getattr(provider, "review_target", None)
            if target:
                return Path(target).parent / "human_review_matrix.csv"
        if self._records_source is not None:
            return self._records_source.parent / "human_review_matrix.csv"
        return None

    def _load_existing_matrix(self) -> dict:
        if self._matrix_path is None:
            return {}
        try:
            from scripts.review_behavior_signals import load_existing
        except Exception:  # noqa: BLE001
            return {}
        try:
            return dict(load_existing(self._matrix_path))
        except Exception:  # noqa: BLE001
            return {}

    def _evidence_root(self) -> Path:
        if self._explicit_evidence_root is not None:
            return Path(self._explicit_evidence_root)
        provider = self._provider
        if provider is not None:
            root = getattr(provider, "evidence_root", None)
            if root:
                return Path(root)
        return Path("data/runtime_evidence")

    def _resolve(self, reference: str) -> Optional[Path]:
        if not reference:
            return None
        try:
            from scripts.review_behavior_signals import resolve_evidence
        except Exception:  # noqa: BLE001
            return None
        try:
            return resolve_evidence(reference, self._evidence_root())
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # review state
    # ------------------------------------------------------------------
    def _classification_for(self, review_id: str) -> str:
        if review_id in self._session:
            return str(self._session[review_id].get("classification", ""))
        row = self._existing.get(review_id)
        if row:
            return str(row.get("classification", "") or "").upper()
        return ""

    def _pending_ids(self) -> list:
        pending = []
        for record in self._records:
            review_id = str(record.get("review_id", ""))
            if self._classification_for(review_id) in ("", "NOT_REVIEWED"):
                pending.append(review_id)
        return pending

    def _first_pending_index(self) -> int:
        pending = set(self._pending_ids())
        for index, record in enumerate(self._records):
            if record.get("review_id") in pending:
                return index
        return 0

    def _current(self) -> dict:
        return self._records[self._index]

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def _build_empty(self) -> None:
        body = tk.Frame(self, bg=_BG)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            body, text=EMPTY_STATE_TEXT, bg=_BG, fg=_TEXT_DIM,
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(120, 12))
        self._close_btn = tk.Button(
            body, text="CERRAR", command=self._close, relief=tk.FLAT,
            bg=_PANEL, fg=_TEXT, activebackground=_BORDER,
            activeforeground=_TEXT, font=("Segoe UI", 10, "bold"),
            padx=18, pady=6, borderwidth=1, highlightbackground=_BORDER,
        )
        self._close_btn.pack()

    def _build_review(self) -> None:
        header = tk.Frame(self, bg=_BG)
        header.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(
            header, text="REVISIÓN HUMANA · QW-00", bg=_BG, fg=_TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(side=tk.LEFT)
        self._counter_var = tk.StringVar(value="")
        tk.Label(
            header, textvariable=self._counter_var, bg=_BG, fg=_TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT)

        body = tk.Frame(self, bg=_PANEL, highlightbackground=_BORDER,
                        highlightthickness=1)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        info = tk.Frame(body, bg=_PANEL)
        info.pack(fill=tk.X, padx=10, pady=(8, 2))
        self._info_vars = {}
        for key, label in (
            ("camera", "CAMERA"),
            ("timestamp", "TIMESTAMP"),
            ("event", "EVENTO / TRACK"),
            ("classification", "CLASIFICACIÓN"),
            ("review_state", "REVIEW STATUS"),
            ("clip_status", "CLIP STATUS"),
        ):
            row = tk.Frame(info, bg=_PANEL)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label, bg=_PANEL, fg=_TEXT_DIM,
                     font=("Segoe UI", 8, "bold"), width=16, anchor=tk.W
                     ).pack(side=tk.LEFT)
            var = tk.StringVar(value="-")
            self._info_vars[key] = var
            tk.Label(row, textvariable=var, bg=_PANEL, fg=_TEXT,
                     font=("Segoe UI", 9), anchor=tk.W, justify=tk.LEFT
                     ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._jpeg_canvas = tk.Canvas(body, bg="#0A0F1E", height=210,
                                      highlightthickness=0)
        self._jpeg_canvas.pack(fill=tk.X, padx=10, pady=6)

        self._status_var = tk.StringVar(value="")
        tk.Label(body, textvariable=self._status_var, bg=_PANEL, fg=_ACCENT,
                 font=("Segoe UI", 9), anchor=tk.W
                 ).pack(fill=tk.X, padx=12, pady=(0, 4))

        controls = tk.Frame(self, bg=_BG)
        controls.pack(fill=tk.X, padx=12, pady=8)

        def nav_button(text, command):
            return tk.Button(
                controls, text=text, command=command, relief=tk.FLAT,
                bg=_PANEL, fg=_TEXT, activebackground=_BORDER,
                activeforeground=_TEXT, font=("Segoe UI", 9, "bold"),
                padx=12, pady=4, borderwidth=1, highlightbackground=_BORDER,
            )

        self._prev_btn = nav_button("ANTERIOR", self._on_prev)
        self._prev_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._next_btn = nav_button("SIGUIENTE", self._on_next)
        self._next_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._open_clip_btn = nav_button(
            "ABRIR / REPRODUCIR CLIP", self._on_open_clip
        )
        self._open_clip_btn.pack(side=tk.LEFT, padx=(0, 6))

        classify_row = tk.Frame(self, bg=_BG)
        classify_row.pack(fill=tk.X, padx=12, pady=(0, 6))
        self._classify_buttons = []
        for index, classification in enumerate(CLASSIFICATIONS, start=1):
            btn = tk.Button(
                classify_row, text=f"CLASIFICACIÓN {index} · {classification}",
                command=lambda c=classification: self._classify(c),
                relief=tk.FLAT, bg=_PANEL, fg=_ACCENT,
                activebackground=_BORDER, activeforeground=_TEXT,
                font=("Segoe UI", 8, "bold"), padx=8, pady=4,
                borderwidth=1, highlightbackground=_BORDER,
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._classify_buttons.append(btn)

        actions = tk.Frame(self, bg=_BG)
        actions.pack(fill=tk.X, padx=12, pady=(0, 10))
        self._save_btn = tk.Button(
            actions, text="GUARDAR", command=self._save, relief=tk.FLAT,
            bg=_ACCENT, fg="#0F172A", activebackground="#67D3FF",
            activeforeground="#0F172A", font=("Segoe UI", 10, "bold"),
            padx=20, pady=6, borderwidth=0,
        )
        self._save_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._close_btn = tk.Button(
            actions, text="CERRAR", command=self._close, relief=tk.FLAT,
            bg=_PANEL, fg=_TEXT, activebackground=_BORDER,
            activeforeground=_TEXT, font=("Segoe UI", 10, "bold"),
            padx=20, pady=6, borderwidth=1, highlightbackground=_BORDER,
        )
        self._close_btn.pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # navigation / actions
    # ------------------------------------------------------------------
    def _go_to(self, index: int) -> None:
        total = len(self._records)
        self._index = max(0, min(index, total - 1))
        self._refresh()

    def _on_prev(self) -> None:
        self._go_to(self._index - 1)

    def _on_next(self) -> None:
        self._go_to(self._index + 1)

    def _classify(self, classification: str) -> None:
        record = self._current()
        review_id = str(record.get("review_id", ""))
        static_ref = str((record.get("evidence_refs") or [""])[-1])
        clip_ref = str(record.get("clip_evidence_ref") or "")
        static_sufficient = "NOT_AVAILABLE"
        if self._resolve(static_ref) is not None:
            static_sufficient = ""
        temporal_sufficient = "NOT_AVAILABLE"
        if record.get("clip_available") and self._resolve(clip_ref) is not None:
            temporal_sufficient = ""
        self._session[review_id] = {
            "review_id": review_id,
            "signal_id": str(record.get("signal_id", "")),
            "camera_id": str(record.get("camera_id", "")),
            "track_id": str(
                record.get("track_id", "") or record.get("trajectory_id", "") or ""
            ),
            "classification": classification,
            "review_timestamp": datetime.now(timezone.utc).isoformat(),
            "evidence_ref": static_ref,
            "clip_evidence_ref": clip_ref,
            "clip_sha256": str(record.get("clip_sha256", "")),
            "static_evidence_sufficient": static_sufficient,
            "temporal_evidence_sufficient": temporal_sufficient,
            "comparison_notes": "",
        }
        self._set_status(f"Clasificación {classification} aplicada")
        self._refresh()

    def _save(self) -> None:
        if self._matrix_path is None:
            self._set_status("Destino de revisión no disponible")
            return
        rows = []
        for record in self._records:
            review_id = str(record.get("review_id", ""))
            if not review_id:
                continue
            if review_id in self._session:
                rows.append(self._session[review_id])
            elif review_id in self._existing:
                rows.append(self._existing[review_id])
        try:
            from scripts.review_behavior_signals import save, write_metrics
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Error de persistencia: {type(exc).__name__}")
            return
        try:
            save(self._matrix_path, rows)
            write_metrics(self._matrix_path, rows)
        except OSError as exc:
            self._set_status(f"Error al guardar: {exc}")
            return
        self._set_status(f"Review guardado · {len(rows)} registros")

    def _on_open_clip(self) -> None:
        record = self._current()
        clip_ref = str(record.get("clip_evidence_ref") or "")
        if not record.get("clip_available"):
            self._set_status(CLIP_UNAVAILABLE_TEXT)
            return
        path = self._resolve(clip_ref)
        if path is None:
            self._set_status(CLIP_UNAVAILABLE_TEXT)
            return
        try:
            if self._opener(str(path)):
                self._set_status(f"Clip abierto: {path.name}")
            else:
                self._set_status(CLIP_UNAVAILABLE_TEXT)
        except OSError:
            self._set_status(CLIP_UNAVAILABLE_TEXT)

    def _close(self) -> None:
        try:
            self.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # display
    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        total = len(self._records)
        self._counter_var.set(
            f"Registro {self._index + 1} / {total} · "
            f"Pendientes: {len(self._pending_ids())}"
        )
        record = self._current()
        classification = self._classification_for(str(record.get("review_id", "")))
        review_state = (
            "REVIEWED" if classification not in ("", "NOT_REVIEWED") else "PENDING"
        )
        track = str(
            record.get("track_id", "") or record.get("trajectory_id", "") or "-"
        )
        event = str(record.get("signal_type", "")) or "-"
        rule = str(record.get("rule_id", "")) or ""
        if rule:
            event = f"{event} · {rule}"
        self._info_vars["camera"].set(str(record.get("camera_id", "-")))
        self._info_vars["timestamp"].set(
            str(record.get("timestamp_start", "") or record.get("timestamp_end", "-"))
        )
        self._info_vars["event"].set(event)
        self._info_vars["classification"].set(
            classification if classification else "NOT_REVIEWED"
        )
        self._info_vars["review_state"].set(review_state)
        clip_ref = str(record.get("clip_evidence_ref") or "")
        clip_status = "Disponible"
        if not record.get("clip_available") or self._resolve(clip_ref) is None:
            clip_status = "No disponible"
        self._info_vars["clip_status"].set(clip_status)
        self._render_jpeg(record)

    def _render_jpeg(self, record: dict) -> None:
        canvas = self._jpeg_canvas
        canvas.delete("all")
        cw = max(canvas.winfo_width(), 320)
        ch = max(canvas.winfo_height(), 210)
        static_ref = str((record.get("evidence_refs") or [""])[-1])
        path = self._resolve(static_ref)
        if path is None:
            canvas.create_text(
                cw // 2, ch // 2, anchor=tk.CENTER, text=JPEG_UNAVAILABLE_TEXT,
                fill=_TEXT_DIM, font=("Segoe UI", 9),
            )
            return
        try:
            from PIL import Image, ImageTk
        except Exception:  # noqa: BLE001
            canvas.create_text(
                cw // 2, ch // 2, anchor=tk.CENTER, text=JPEG_UNAVAILABLE_TEXT,
                fill=_TEXT_DIM, font=("Segoe UI", 9),
            )
            return
        try:
            image = Image.open(str(path))
            image.thumbnail((cw, ch))
            photo = ImageTk.PhotoImage(image)
        except Exception:  # noqa: BLE001
            canvas.create_text(
                cw // 2, ch // 2, anchor=tk.CENTER, text=JPEG_UNAVAILABLE_TEXT,
                fill=_TEXT_DIM, font=("Segoe UI", 9),
            )
            return
        self._photo = photo
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor=tk.CENTER)

    def _set_status(self, text: str) -> None:
        if hasattr(self, "_status_var"):
            self._status_var.set(text)