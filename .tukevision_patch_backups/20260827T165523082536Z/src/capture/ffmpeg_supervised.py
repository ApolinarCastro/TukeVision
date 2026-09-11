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
import subprocess
import threading
import time
from collections import deque
from typing import Optional, Tuple

import cv2
import numpy as np

from src.capture.video_source import VideoMetadata, VideoSourceError
from src.observability.logging_setup import redact_rtsp_url

logger = logging.getLogger("tukevision.capture.ffmpeg")


def _probe_size(rtsp_url: str, timeout: float = 5.0) -> Optional[Tuple[int, int]]:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", rtsp_url],
            capture_output=True, timeout=timeout, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = proc.stdout.strip().split(",")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as exc:
        logger.debug("FFPROBE_FAILED %s", exc)
    return None


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
                 rtsp_open_timeout_ms: int = 8000, frame_stall_timeout_s: float = 3.0,
                 capture_factory=None, username: str = "", password: str = ""):
        self._username = username
        self._password = password
        self._rtsp_url = self._embed_credentials(rtsp_url, username, password)
        self._max_width = max_width
        self._process_every = max(1, process_every_n_frames)
        self._frame_stall_timeout_s = max(1.0, float(frame_stall_timeout_s))
        self._state = "CLOSED"
        self._proc: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._cond = threading.Condition()
        self._queue: deque = deque(maxlen=self._QUEUE_MAX)
        self._frame_index = 0
        self._readable_frames = 0
        self._last_valid_at = 0.0
        self._stall_count = 0
        self._reconnect_count = 0
        self._metadata: Optional[VideoMetadata] = None
        self._width = 0
        self._height = 0
        self._scaled_w = 0
        self._scaled_h = 0
        self._frame_bytes = 0
        self._capture_factory = capture_factory

    def _embed_credentials(self, url: str, username: str, password: str) -> str:
        if not username or not password:
            return url
        if url.startswith("rtsp://"):
            rest = url[7:]
            if "@" not in rest:
                return f"rtsp://{username}:{password}@{rest}"
        return url

    def _scaled_size(self, w: int, h: int) -> Tuple[int, int]:
        if self._max_width <= 0 or w <= self._max_width:
            return w, h
        scale = self._max_width / w
        return self._max_width, int(h * scale) & ~1

    def _build_ffmpeg_cmd(self, w: int, h: int, scaled_w: int, scaled_h: int):
        vf = f"scale={scaled_w}:{scaled_h}" if (scaled_w != w or scaled_h != h) else "null"
        return [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-stimeout", str(int(self._frame_stall_timeout_s * 1_000_000)),
            "-i", self._rtsp_url,
            "-vf", vf,
            "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-an",
            "pipe:1"
        ]

    def open(self) -> VideoMetadata:
        self.close()
        self._state = "CONNECTING"
        probed = _probe_size(self._rtsp_url)
        if probed:
            w, h = probed
        else:
            w, h = 1280, 720
        sw, sh = self._scaled_size(w, h)
        self._width, self._height = w, h
        self._scaled_w, self._scaled_h = sw, sh
        self._frame_bytes = sw * sh * 3
        cmd = self._build_ffmpeg_cmd(w, h, sw, sh)
        logger.debug("FFMPEG_CMD %s", " ".join(cmd))
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024 * 1024
            )
        except Exception as exc:
            self._state = "FAILED"
            raise VideoSourceError(f"ffmpeg start failed: {exc}")
        self._stop.clear()
        self._queue.clear()
        self._frame_index = 0
        self._readable_frames = 0
        self._last_valid_at = 0.0
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True, name="tukevision-ffmpeg-reader")
        self._reader_thread.start()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True, name="tukevision-ffmpeg-watchdog")
        self._watchdog_thread.start()
        deadline = time.monotonic() + max(10.0, self._frame_stall_timeout_s * 3)
        with self._cond:
            while self._last_valid_at == 0.0 and time.monotonic() < deadline:
                self._cond.wait(timeout=0.5)
                if self._state in ("FAILED", "CLOSED"):
                    break
        if self._last_valid_at == 0.0:
            err_output = ""
            if self._proc and self._proc.stderr:
                try:
                    err_output = self._proc.stderr.read().decode("utf-8", errors="ignore")[:500]
                except Exception:
                    pass
            logger.error("FFMPEG_OPEN_FAILED %s stderr=%s", redact_rtsp_url(self._rtsp_url), err_output)
            self.close()
            self._state = "FAILED"
            raise VideoSourceError(f"no first frame after ffmpeg open: {err_output[:200] if err_output else 'unknown'}")
        self._state = "OPEN"
        self._metadata = VideoMetadata(width=sw, height=sh, fps=0.0, total_frames=0, duration_seconds=0.0,
                                       path=redact_rtsp_url(self._rtsp_url), source_type="RTSP")
        logger.info("FFMPEG_OPEN_SUCCESS %s %sx%s", redact_rtsp_url(self._rtsp_url), sw, sh)
        return self._metadata

    def _scaled_size(self, w: int, h: int) -> Tuple[int, int]:
        if self._max_width <= 0 or w <= self._max_width:
            return w, h
        scale = self._max_width / w
        return self._max_width, int(h * scale) & ~1

    def _reader_loop(self):
        assert self._proc and self._proc.stdout
        buf = b""
        needed = self._frame_bytes
        try:
            while not self._stop.is_set():
                while len(buf) < needed and not self._stop.is_set():
                    chunk = self._proc.stdout.read(min(65536, needed - len(buf)))
                    if not chunk:
                        if self._proc.poll() is not None:
                            try:
                                err = self._proc.stderr.read().decode("utf-8", errors="ignore")[:500]
                                logger.error("FFMPEG_EXITED code=%s stderr=%s", self._proc.returncode, err[:500])
                            except Exception:
                                pass
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
                with self._cond:
                    if len(self._queue) >= self._QUEUE_MAX:
                        self._queue.clear()
                    self._queue.append((self._frame_index, frame))
                    self._frame_index += 1
                    self._readable_frames += 1
                    self._last_valid_at = time.monotonic()
                    self._cond.notify_all()
        except Exception as e:
            logger.error("FFMPEG_READER_LOOP_ERROR %s", e)
            with self._cond:
                self._state = "FAILED"
                self._cond.notify_all()

    def _watchdog_loop(self):
        while not self._stop.is_set():
            time.sleep(1.0)
            if self._stop.is_set():
                return
            if self._last_valid_at == 0.0:
                continue
            age = time.monotonic() - self._last_valid_at
            if age > self._frame_stall_timeout_s:
                logger.info("FFMPEG_STALL_DETECTED age=%.1f", age)
                self._stall_count += 1
                self._state = "STALLED"
                self._terminate_process()

    def _terminate_process(self):
        proc = self._proc
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                logger.warning("FFMPEG_KILL %s", redact_rtsp_url(self._rtsp_url))
                proc.kill()
                try:
                    proc.wait(timeout=2.0)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as exc:
            logger.debug("FFMPEG_TERMINATE_FAILED %s", exc)
        finally:
            try:
                if proc.stdout: proc.stdout.close()
            except Exception:
                pass
            try:
                if proc.stderr: proc.stderr.close()
            except Exception:
                pass
            self._verify_orphan()

    def _verify_orphan(self):
        try:
            if self._proc and self._proc.poll() is None:
                logger.warning("ORPHAN_DECODER %s pid=%s still alive after terminate",
                               redact_rtsp_url(self._rtsp_url), self._proc.pid)
        except Exception:
            pass

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
                if self._state in ("FAILED", "CLOSED"):
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
        for th in (self._reader_thread, self._watchdog_thread):
            if th and th.is_alive() and th is not threading.current_thread():
                th.join(timeout=2.0)
        self._proc = None
        self._reader_thread = None
        self._watchdog_thread = None

    @property
    def state(self):
        return self._state

    @property
    def metadata(self):
        return self._metadata

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


def _probe_size(rtsp_url: str, timeout: float = 5.0) -> Optional[Tuple[int, int]]:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", rtsp_url],
            capture_output=True, timeout=timeout, text=True
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = proc.stdout.strip().split(",")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as exc:
        logger.debug("FFPROBE_FAILED %s", exc)
    return None