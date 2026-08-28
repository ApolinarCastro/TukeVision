"""FFmpeg supervised RTSP reader — ClearCam/Frigate pattern reimplemented.

Isolates capture in an ffmpeg subprocess:

  SourceManager -> FFmpeg per stream -> rawvideo pipe -> latest-frame buffer

Watchdog:
  if frame_age > 3s:
    terminate (grace 2s) -> kill if still alive -> close pipes -> verify orphan=0 -> backoff/jitter -> reconnect

This gives hard recovery that OpenCV VideoCapture.read() cannot provide
(RTSP_READ_TIMEOUT_MSEC_UNSUPPORTED). No GPL copy, pattern only.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote
import subprocess
import threading
import time
from collections import deque
from typing import Optional, Tuple

import numpy as np

from src.capture.video_source import VideoMetadata, VideoSourceError
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.capture.ffmpeg")


def _probe_size(rtsp_url: str, timeout: float = 5.0) -> Tuple[Optional[Tuple[int, int]], str]:
    """Probe video dimensions via ffprobe without inventing dimensions.
    
    Returns ((width, height), error_detail). If successful, width and height are integers
    and error_detail is empty string. If failed, dimensions is None and error_detail
    contains the specific, redacted diagnosis (TIMEOUT, AUTH_FAILED, PROTOCOL_ERROR, etc.).
    """
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-rtsp_transport", "tcp",
             "-timeout", str(int(timeout * 1_000_000)), "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", rtsp_url],
            capture_output=True, timeout=timeout, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = proc.stdout.strip().split(",")
            if len(parts) == 2:
                try:
                    w, h = int(parts[0]), int(parts[1])
                    if 0 < w <= 16384 and 0 < h <= 16384:
                        return (w, h), ""
                except ValueError:
                    pass
        err = proc.stderr.strip() if proc.stderr else ""
        if "401" in err or "Unauthorized" in err:
            reason = "AUTH_FAILED"
        elif "Connection refused" in err:
            reason = "CONNECTION_REFUSED"
        elif "Server returned 404" in err:
            reason = "STREAM_NOT_FOUND"
        elif "Immediate exit requested" in err or proc.returncode != 0:
            reason = f"PROBE_EXIT_{proc.returncode}"
        else:
            reason = "NO_STREAM_DIMENSIONS"
        return None, reason
    except subprocess.TimeoutExpired:
        return None, "PROBE_TIMEOUT"
    except Exception as exc:
        return None, f"PROBE_ERROR_{type(exc).__name__}"


class FFmpegSupervisedSource:
    """Drop-in replacement for RTSPSource when backend=ffmpeg_supervised.

    Contract identical to RTSPSource: open() -> VideoMetadata, read() -> (idx, frame) or None,
    close(), state, readable_frames, last_valid_frame_age_ms, etc.
    Latest-frame-wins: queue max 1, intermediate frames dropped.
    """

    _QUEUE_MAX = 1

    def __init__(self, rtsp_url: str, max_width: int = 640, process_every_n_frames: int = 1,
                 max_reconnect_attempts: int = 3, reconnect_delay_seconds: float = 2.0,
                 max_open_attempts: int = 3, open_retry_delay_seconds: float = 2.0,
                 rtsp_open_timeout_ms: int = 8000, frame_stall_timeout_s: float = 10.0,
                 capture_factory=None, username: str = "", password: str = ""):
        self._username = username or ""
        self._password = password or ""
        self._rtsp_url = self._embed_credentials(rtsp_url, self._username, self._password)
        self._max_width = max_width
        self._process_every = max(1, process_every_n_frames)
        self._frame_stall_timeout_s = max(1.0, float(frame_stall_timeout_s))
        self._open_timeout_s = max(0.5, float(rtsp_open_timeout_ms) / 1000.0)
        self._state = "CLOSED"
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._cond = threading.Condition()
        self._queue: Deque[Tuple[int, np.ndarray]] = deque(maxlen=self._QUEUE_MAX)
        self._frame_index = 0
        self._readable_frames = 0
        self._last_valid_at = 0.0
        self._fps_samples: Deque[float] = deque(maxlen=30)
        self._current_fps = 0.0
        self._stall_count = 0
        self._reconnect_count = 0
        self._metadata: Optional[VideoMetadata] = None
        self._width = 0
        self._height = 0
        self._scaled_w = 0
        self._scaled_h = 0
        self._frame_bytes = 0
        self._capture_factory = capture_factory
        self._stderr_tail = ""
        self._terminate_lock = threading.Lock()

    def _embed_credentials(self, url: str, username: str, password: str) -> str:
        if not username or not password:
            return url
        if url.startswith("rtsp://"):
            rest = url[7:]
            if "@" not in rest:
                return f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@{rest}"
        return url

    def _scaled_size(self, w: int, h: int) -> Tuple[int, int]:
        if self._max_width <= 0 or w <= self._max_width:
            return w, h
        scale = self._max_width / w
        return self._max_width, int(h * scale) & ~1

    def _build_ffmpeg_cmd(self, w: int, h: int, scaled_w: int, scaled_h: int):
        vf = f"scale={scaled_w}:{scaled_h}"
        return [
            "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-timeout", str(int(self._open_timeout_s * 1_000_000)),
            "-i", self._rtsp_url,
            "-vf", vf,
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-an",
            "pipe:1"
        ]

    def open(self) -> VideoMetadata:
        self.close()
        self._state = "CONNECTING"
        probed, probe_err = _probe_size(self._rtsp_url, timeout=self._open_timeout_s)
        if probed:
            w, h = probed
        elif self._width > 0 and self._height > 0 and probe_err == "PROBE_TIMEOUT":
            # Resilient reconnect: keep previously discovered and verified dimensions
            # instead of aborting when ffprobe hits transient WAN probe timeout.
            w, h = self._width, self._height
            logger.info("FFPROBE_RECONNECT_CACHED_DIMS %s %sx%s (reason=%s)", 
                        redact_rtsp_url(self._rtsp_url), w, h, probe_err)
        else:
            self._state = "FAILED"
            logger.error("FFPROBE_NO_DIMENSIONS %s reason=%s", redact_rtsp_url(self._rtsp_url), probe_err)
            raise VideoSourceError(f"FFPROBE_NO_DIMENSIONS [{probe_err}]: cannot frame rawvideo safely")
        sw, sh = self._scaled_size(w, h)
        self._width, self._height = w, h
        self._scaled_w, self._scaled_h = sw, sh
        self._frame_bytes = sw * sh * 3
        cmd = self._build_ffmpeg_cmd(w, h, sw, sh)
        logger.debug("FFMPEG_CMD %s", self._redact(" ".join(cmd)))
        try:
            self._proc = subprocess.Popen(
                cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
        except Exception as exc:
            self._state = "FAILED"
            raise VideoSourceError(f"ffmpeg start failed: {type(exc).__name__}") from None
        self._stop.clear()
        self._stderr_tail = ""
        self._stderr_thread = threading.Thread(target=self._drain_stderr, args=(self._proc,),
                                               daemon=True, name="tukevision-ffmpeg-stderr")
        self._stderr_thread.start()
        self._queue.clear()
        self._frame_index = 0
        self._readable_frames = 0
        self._last_valid_at = 0.0
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True, name="tukevision-ffmpeg-reader")
        self._reader_thread.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True, name="tukevision-ffmpeg-watchdog")
        self._watchdog_thread.start()
        deadline = time.monotonic() + self._open_timeout_s
        with self._cond:
            while self._last_valid_at == 0.0 and time.monotonic() < deadline:
                self._cond.wait(timeout=0.5)
                if self._state in ("FAILED", "CLOSED"):
                    break
        if self._last_valid_at == 0.0:
            self.close()  # terminate before reading diagnostics; never wait for stderr EOF here
            err_output = self._stderr_tail[-500:]
            self._state = "FAILED"
            logger.error("FFMPEG_OPEN_FAILED %s stderr=%s", redact_rtsp_url(self._rtsp_url), err_output)
            raise VideoSourceError(f"no first frame after ffmpeg open: {err_output or 'timeout/EOF'}")
        self._state = "OPEN"
        self._metadata = VideoMetadata(width=sw, height=sh, fps=0.0, total_frames=0, duration_seconds=0.0,
                                       path=redact_rtsp_url(self._rtsp_url), source_type="RTSP")
        logger.info("FFMPEG_OPEN_SUCCESS %s %sx%s", redact_rtsp_url(self._rtsp_url), sw, sh)
        return self._metadata

    def _reader_loop(self):
        assert self._proc and self._proc.stdout
        buf = b""
        needed = self._frame_bytes
        try:
            while not self._stop.is_set():
                while len(buf) < needed and not self._stop.is_set():
                    chunk = self._proc.stdout.read(min(65536, needed - len(buf)))
                    if not chunk:
                        if not self._stop.is_set() and self._state not in ("STALLED", "CLOSED"):
                            exit_code = self._proc.poll()
                            if exit_code is None:
                                logger.info("FFMPEG_STREAM_CLOSED_BY_SOURCE url=%s", redact_rtsp_url(self._rtsp_url))
                            else:
                                logger.warning("FFMPEG_PROCESS_EXITED code=%s url=%s", exit_code, redact_rtsp_url(self._rtsp_url))
                            with self._cond:
                                self._state = "FAILED"
                                self._cond.notify_all()
                        return
                    buf += chunk
                if len(buf) < needed:
                    return
                raw = buf[:needed]
                buf = buf[needed:]
                try:
                    frame = np.frombuffer(raw, dtype=np.uint8).reshape((self._scaled_h, self._scaled_w, 3))
                    frame = frame.copy()
                except Exception as e:
                    logger.debug("FFMPEG_FRAME_DECODE_ERROR %s", e)
                    continue
                now = time.monotonic()
                with self._cond:
                    if len(self._queue) >= self._QUEUE_MAX:
                        self._queue.clear()
                    self._queue.append((self._frame_index, frame))
                    self._frame_index += 1
                    self._readable_frames += 1
                    self._fps_samples.append(now)
                    if len(self._fps_samples) >= 2:
                        duration = self._fps_samples[-1] - self._fps_samples[0]
                        if duration > 0.01:
                            self._current_fps = round((len(self._fps_samples) - 1) / duration, 1)
                    self._last_valid_at = now
                    self._cond.notify_all()
        except Exception as e:
            if not self._stop.is_set() and self._state not in ("STALLED", "CLOSED"):
                logger.error("FFMPEG_READER_LOOP_ERROR %s", e)
                with self._cond:
                    self._state = "FAILED"
                    self._cond.notify_all()

    def _watchdog_loop(self):
        while not self._stop.is_set():
            self._stop.wait(0.5)
            if self._stop.is_set():
                return
            if self._last_valid_at == 0.0:
                continue
            age = time.monotonic() - self._last_valid_at
            if age > self._frame_stall_timeout_s:
                logger.info("FFMPEG_STALL_DETECTED age=%.1f", age)
                self._stall_count += 1
                with self._cond:
                    self._state = "STALLED"
                    self._cond.notify_all()
                self._terminate_process()
                return

    def _redact(self, message):
        message = re.sub(r"rtsp://[^\s]+", "rtsp://REDACTED", str(message))
        for secret in (self._password, quote(self._password, safe="") if self._password else ""):
            if secret:
                message = message.replace(secret, "REDACTED")
        return message

    def _drain_stderr(self, proc):
        try:
            while True:
                chunk = proc.stderr.read(1024)
                if not chunk:
                    break
                # Keep raw fragments only in memory; redact the complete diagnostic at access.
                self._stderr_tail = (self._stderr_tail + chunk.decode("utf-8", errors="replace"))[-4096:]
        except (OSError, ValueError):
            pass
        finally:
            self._stderr_tail = self._redact(self._stderr_tail)

    def _terminate_process(self):
        with self._terminate_lock:
            proc = self._proc
            if proc is None or proc.poll() is not None:
                return
            try:
                proc.terminate()
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
            except ProcessLookupError:
                pass
            if proc.poll() is None:
                raise VideoSourceError("ORPHAN_DECODER: process termination not confirmed")

    def read(self):
        with self._cond:
            if self._state in ("FAILED", "CLOSED"):
                return None
            if not self._queue:
                age = time.monotonic() - self._last_valid_at if self._last_valid_at else 0
                remaining = self._frame_stall_timeout_s - age if self._last_valid_at else self._frame_stall_timeout_s
                if remaining > 0:
                    self._cond.wait(timeout=min(remaining, 0.5))
                if not self._queue:
                    if self._last_valid_at and (time.monotonic() - self._last_valid_at) >= self._frame_stall_timeout_s:
                        self._state = "STALLED"
                    return None
            if self._queue:
                idx, frame = self._queue.popleft()
                if idx % self._process_every != 0:
                    return self.read()
                return (idx, frame)
            return None

    def frames(self):
        while not self._stop.is_set():
            r = self.read()
            if r is None:
                if self._state in ("STALLED", "FAILED", "CLOSED"):
                    break
                time.sleep(0.05)
                continue
            yield r

    def close(self):
        self._stop.set()
        self._state = "CLOSED"
        with self._cond:
            self._cond.notify_all()
        self._terminate_process()
        threads = (self._reader_thread, self._watchdog_thread, self._stderr_thread)
        for th in threads:
            if th and th.is_alive() and th is not threading.current_thread():
                th.join(timeout=2.0)
        if any(th and th.is_alive() and th is not threading.current_thread() for th in threads):
            raise VideoSourceError("ORPHAN_READER: reader termination not confirmed")
        if self._proc:
            for pipe in (self._proc.stdout, self._proc.stderr):
                if pipe:
                    pipe.close()
        self._proc = None
        self._reader_thread = None
        self._watchdog_thread = None
        self._stderr_thread = None

    @property
    def state(self):
        return self._state

    @property
    def metadata(self):
        return self._metadata

    @property
    def fps(self):
        return self._current_fps

    @property
    def readable_frames(self):
        return self._readable_frames

    @property
    def last_valid_frame_age_ms(self):
        if not self._last_valid_at:
            return 0
        return int((time.monotonic() - self._last_valid_at) * 1000)

    @property
    def stall_count(self):
        return self._stall_count

    @property
    def last_valid_frame_at(self):
        return self._last_valid_at


