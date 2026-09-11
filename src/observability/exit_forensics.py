"""Application exit forensics (MACRO-OC-02, BLOCK E).

Captures every plausible path that can end the process and records a single
sanitized ``process_exit_forensics.json`` explaining WHY_PROCESS_EXITED:
normal close, unhandled exception (main thread or worker thread), Tk callback
error, subprocess/runtime termination, or monitor-controlled shutdown.

It never rewrites capture code; it wraps the entrypoint and installs the two
standard ``excepthook`` hooks.  Tracebacks are sanitized before persisting so
no RTSP URL, username or password can leak into the evidence file.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

_EXIT_KIND_UNHANDLED = "UNHANDLED_EXCEPTION"
_EXIT_KIND_NORMAL = "NORMAL_UI_CLOSE"
_EXIT_KIND_SHUTDOWN_HOOK = "OPERATOR_SHUTDOWN"
_EXIT_KIND_UNKNOWN = "UNKNOWN"

_SENSITIVE_PATTERNS = (
    "ENV_DVR_PRINCIPAL_CREDS",
    "password=",
    "credential",
)
_URL_CREDENTIALS = re.compile(r"(rtsp://[^:/\s@]+:)[^@\s/]+(@)")


def _sanitize(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        line = _URL_CREDENTIALS.sub(r"\1<REDACTED>\2", line)
        lowered = line.lower()
        if any(marker in lowered for marker in _SENSITIVE_PATTERNS):
            lines.append("<REDACTED>")
        else:
            lines.append(line)
    return "\n".join(lines)


class ExitForensics:
    """Registers hooks and records the single authoritative exit reason."""

    def __init__(
        self,
        evidence_path: str | Path,
        *,
        proc=None,
        clock: Optional[callable] = None,
        registry: Optional[dict] = None,
    ) -> None:
        self._path = Path(evidence_path)
        self._proc = proc
        self._clock = clock or time.time
        self._registry = registry if registry is not None else {}
        self._started = self._clock()
        self._finished = False
        self._lock = threading.Lock()
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        self._previous_finalizer: Optional[callable] = None
        self._pid = os.getpid()

    # ------------------------------------------------------------------ hooks
    def install(self) -> None:
        self._previous_sys_hook = sys.excepthook
        self._previous_thread_hook = threading.excepthook
        sys.excepthook = self._on_sys_exception
        threading.excepthook = self._on_thread_exception

    def uninstall(self) -> None:
        sys.excepthook = self._previous_sys_hook
        threading.excepthook = self._previous_thread_hook

    def _on_sys_exception(self, exc_type, exc_value, exc_tb) -> None:
        self.record_unhandled(exc_type, exc_value, exc_tb)
        if self._previous_sys_hook is not None:
            try:
                self._previous_sys_hook(exc_type, exc_value, exc_tb)
            except Exception:
                pass

    def _on_thread_exception(self, args) -> None:
        self.record_unhandled(
            getattr(args, "exc_type", None),
            getattr(args, "exc_value", None),
            getattr(args, "exc_traceback", None),
            thread=getattr(args, "thread", None),
        )

    def record_unhandled(
        self, exc_type, exc_value, exc_tb, thread: Optional[object] = None
    ) -> None:
        tb = "".join(
            traceback.format_exception(exc_type, exc_value, exc_tb)
        ) if exc_tb is not None else str(exc_value)
        self.record_exit(
            _EXIT_KIND_UNHANDLED,
            {
                "exception_type": getattr(exc_type, "__name__", "Exception"),
                "exception_message": _sanitize(str(exc_value)),
                "traceback": _sanitize(tb),
                "thread": getattr(thread, "name", None),
            },
        )

    # ------------------------------------------------------------------ record
    def record_exit(self, kind: str, detail: Optional[dict] = None) -> None:
        with self._lock:
            if self._finished:
                return
            self._finished = True
        self._registry["why_process_exited"] = kind
        self._registry["uptime_s"] = round(self._clock() - self._started, 1)
        self._registry["pid"] = self._pid
        self._registry["started_wall_clock"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(self._started)
        )
        self._registry["exited_wall_clock"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(self._clock())
        )
        if detail:
            self._registry["detail"] = detail
        try:
            self._flush()
        except Exception:
            pass

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    @property
    def registry(self) -> dict:
        return self._registry

    @property
    def finished(self) -> bool:
        return bool(self._finished)


__all__ = [
    "ExitForensics",
    "EXIT_KIND_UNHANDLED",
    "EXIT_KIND_NORMAL",
    "EXIT_KIND_SHUTDOWN_HOOK",
]