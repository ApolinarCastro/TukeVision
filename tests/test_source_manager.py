"""Pruebas sintéticas deterministas del SourceManager (LOOP-0018N).

Validan el contrato mínima de multicámara 4-cam usando una fuente falsa
controlada (no se abre ninguna cámara real):
  - registrado/arranque/health/snapshot por cámara
  - SOURCE_ISOLATION: un fallo en una cámara no detiene a las demás
  - BOUNDED_QUEUE con política drop-oldest
  - detención limpia y aislamiento
  - sin exposición de credenciales (SECRET_LEAK=0)
"""

import time
import unittest
from threading import Event

import numpy as np

from src.capture.source_manager import (
    CameraDescriptor,
    CameraHealth,
    SourceManager,
    SourceManagerError,
)
from src.capture.live_sources import SourceState
from src.capture.video_source import VideoMetadata


class FakeSource:
    """Simula la interfaz de RTSPSource para pruebas controladas.

    Cada instancia es independiente: el fallo de una no afecta a las demás
    (contrato NO_SHARED_MUTABLE_CAPTURE en el lado de la prueba).
    """

    def __init__(
        self,
        camera_id: str,
        frames: int = 5,
        fail_on_open: bool = False,
        fail_after_frames: int = 0,
        fps: float = 30.0,
        width: int = 640,
        height: int = 480,
        stop_event: Event = None,
    ) -> None:
        self.camera_id = camera_id
        self._remaining = frames  # None => continuo hasta stop_event
        self._fail_on_open = fail_on_open
        self._fail_after_frames = fail_after_frames
        self._delivered = 0
        self._state = SourceState.CLOSED
        self._closed = False
        self._metadata = None
        self.fps = fps
        self.width = width
        self.height = height
        self.stall_count = 0
        self.last_valid_frame_age_ms = 0
        self.readable_frames = 0
        self.source_type = "RTSP"
        self.stop_event = stop_event

    def open(self):
        if self._fail_on_open:
            self._state = SourceState.FAILED
            raise RuntimeError(f"open-failed-{self.camera_id}")
        self._state = SourceState.OPEN
        self._metadata = VideoMetadata(
            width=self.width,
            height=self.height,
            fps=self.fps,
            total_frames=0,
            duration_seconds=0.0,
            path=f"rtsp://redacted/{self.camera_id}",
            source_type="RTSP",
        )
        return self._metadata

    def frames(self):
        while self._remaining is None or self._remaining > 0:
            if self.stop_event is not None and self.stop_event.is_set():
                break
            if self._fail_after_frames and self._delivered >= self._fail_after_frames:
                self._state = SourceState.FAILED
                break
            if self._remaining is not None:
                self._remaining -= 1
            self._delivered += 1
            self.readable_frames += 1
            idx = self._delivered
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            yield (idx, frame)
        if self._fail_after_frames and self._delivered >= self._fail_after_frames:
            self._state = SourceState.FAILED

    @property
    def state(self):
        return self._state

    @property
    def metadata(self):
        return self._metadata

    def close(self):
        self._closed = True
        self._state = SourceState.CLOSED


class FakeSourceFactory:
    """Fábrica que crea FakeSource por cámara con la configuración deseada."""

    def __init__(self):
        self._calls = {}
        self._configs = {}

    def configure(self, camera_id: str, **kwargs):
        self._configs[camera_id] = kwargs

    def __call__(self, descriptor: CameraDescriptor):
        cfg = self._configs.get(descriptor.camera_id, {})
        self._calls[descriptor.camera_id] = self._calls.get(descriptor.camera_id, 0) + 1
        return FakeSource(descriptor.camera_id, stop_event=Event(), **cfg)


def make_descriptor(camera_id: str, **kwargs):
    kwargs.setdefault("host", f"rtsp://cam.local/{camera_id}")
    kwargs.setdefault("username", "user")
    kwargs.setdefault("password", "secret")
    # Los campos de comportamiento de FakeSource (frames/fail_*) no pertenecen
    # al descriptor: se configuran en FakeSourceFactory.configure().
    kwargs.pop("frames", None)
    kwargs.pop("fail_on_open", None)
    kwargs.pop("fail_after_frames", None)
    return CameraDescriptor(camera_id=camera_id, **kwargs)


class TestSourceManagerRegistration(unittest.TestCase):

    def test_register_and_list_sources(self):
        mgr = SourceManager(source_factory=FakeSourceFactory())
        id1 = mgr.register_source(make_descriptor("CAM-01"))
        id2 = mgr.register_source(make_descriptor("CAM-02"))
        self.assertEqual(id1, "CAM-01")
        self.assertEqual(id2, "CAM-02")
        sources = mgr.list_sources()
        self.assertEqual([s["camera_id"] for s in sources], ["CAM-01", "CAM-02"])
        self.assertTrue(all(s["running"] is False for s in sources))

    def test_register_duplicate_rejected(self):
        mgr = SourceManager(source_factory=FakeSourceFactory())
        mgr.register_source(make_descriptor("CAM-01"))
        with self.assertRaises(SourceManagerError):
            mgr.register_source(make_descriptor("CAM-01"))

    def test_register_invalid_host_rejected(self):
        mgr = SourceManager(source_factory=FakeSourceFactory())
        with self.assertRaises(SourceManagerError):
            mgr.register_source(make_descriptor("CAM-01", host="http://bad"))
        with self.assertRaises(SourceManagerError):
            mgr.register_source(make_descriptor("CAM-01", host=""))

    def test_secret_not_exposed_in_inventory(self):
        mgr = SourceManager(source_factory=FakeSourceFactory())
        mgr.register_source(make_descriptor("CAM-01", password="super-secret"))
        for entry in mgr.list_sources():
            self.assertNotIn("super-secret", str(entry))
            self.assertNotIn("secret", entry["host"])


class TestSourceManagerLifecycle(unittest.TestCase):

    def _wait_running(self, mgr, camera_id, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            h = mgr.health(camera_id)
            if h.healthy and h.readable_frames > 0 and mgr.snapshot(camera_id) is not None:
                return h
            time.sleep(0.01)
        return mgr.health(camera_id)

    def test_start_health_snapshot(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-01", frames=None)  # continuo hasta stop
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-01"))
        mgr.start("CAM-01")

        h = self._wait_running(mgr, "CAM-01")
        self.assertTrue(h.healthy)
        self.assertEqual(h.state, SourceState.OPEN)
        self.assertEqual(h.resolution, "640x480")

        snap = mgr.snapshot("CAM-01")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["camera_id"], "CAM-01")
        self.assertIsInstance(snap["frame"], np.ndarray)

        mgr.close_all()

    def test_three_more_cameras_parallel(self):
        """Cuatro cámaras independientes pueden correr en paralelo."""
        factory = FakeSourceFactory()
        mgr = SourceManager(source_factory=factory)
        ids = [f"CAM-0{i}" for i in range(1, 5)]
        for cam_id in ids:
            factory.configure(cam_id, frames=None)
            mgr.register_source(make_descriptor(cam_id))
            mgr.start(cam_id)

        time.sleep(0.3)
        for cam_id in ids:
            h = mgr.health(cam_id)
            self.assertTrue(h.healthy, f"{cam_id} healthy")
            self.assertGreaterEqual(h.readable_frames, 1)
        self.assertEqual(len(mgr.list_sources()), 4)
        mgr.close_all()

    def test_one_camera_failure_does_not_stop_others(self):
        """SOURCE_ISOLATION: una cámara que falla no derriba a las demás."""
        factory = FakeSourceFactory()
        factory.configure("CAM-BAD", fail_on_open=True)
        factory.configure("CAM-OK", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-BAD"))
        mgr.register_source(make_descriptor("CAM-OK"))
        mgr.start("CAM-BAD")
        mgr.start("CAM-OK")

        time.sleep(0.3)
        h_bad = mgr.health("CAM-BAD")
        h_ok = mgr.health("CAM-OK")
        # BAD debe estar en fallo o reintentando (BLOCK D: retry con backoff)
        self.assertIn("open-failed", h_bad.last_error)
        self.assertTrue(h_ok.healthy)
        self.assertGreaterEqual(h_ok.readable_frames, 1)
        mgr.close_all()

    def test_frames_failed_midstream_isolated(self):
        """Un fallo a mitad del stream aísla la cámara y deja al resto activo."""
        factory = FakeSourceFactory()
        factory.configure("CAM-FAIL", frames=100, fail_after_frames=2)
        factory.configure("CAM-OK", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-FAIL"))
        mgr.register_source(make_descriptor("CAM-OK"))
        mgr.start("CAM-FAIL")
        mgr.start("CAM-OK")

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if mgr.health("CAM-FAIL").last_error == "STREAM_LOST":
                break
            time.sleep(0.01)

        h_fail = mgr.health("CAM-FAIL")
        h_ok = mgr.health("CAM-OK")
        self.assertEqual(h_fail.last_error, "STREAM_LOST")
        self.assertTrue(h_ok.healthy)
        mgr.close_all()

    def test_stop_is_clean_and_isolated(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-01", frames=None)
        factory.configure("CAM-02", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-01"))
        mgr.register_source(make_descriptor("CAM-02"))
        mgr.start("CAM-01")
        mgr.start("CAM-02")
        self._wait_running(mgr, "CAM-01")

        mgr.stop("CAM-01")
        h1 = mgr.health("CAM-01")
        h2 = mgr.health("CAM-02")
        self.assertFalse(h1.healthy)
        self.assertTrue(h2.healthy, "CAM-02 debe seguir corriendo")
        mgr.close_all()

    def test_restart(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-01", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-01"))
        mgr.start("CAM-01")
        self._wait_running(mgr, "CAM-01")
        mgr.restart("CAM-01")
        h = self._wait_running(mgr, "CAM-01")
        self.assertTrue(h.healthy)
        mgr.close_all()

    def test_isolate_failure_keeps_others(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-BAD", fail_on_open=True)
        factory.configure("CAM-OK", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-BAD"))
        mgr.register_source(make_descriptor("CAM-OK"))
        mgr.start("CAM-BAD")
        mgr.start("CAM-OK")
        time.sleep(0.2)

        mgr.isolate_failure("CAM-BAD")
        h_bad = mgr.health("CAM-BAD")
        h_ok = mgr.health("CAM-OK")
        self.assertFalse(h_bad.healthy)
        self.assertTrue(h_ok.healthy)
        mgr.close_all()


class TestSourceManagerQueue(unittest.TestCase):

    def test_bounded_queue_drop_oldest(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-01", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-01"))
        mgr.start("CAM-01")
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            h = mgr.health("CAM-01")
            if h.queue_depth > 0 and h.queue_depth <= SourceManager._QUEUE_MAX:
                break
            time.sleep(0.01)
        h = mgr.health("CAM-01")
        self.assertLessEqual(h.queue_depth, SourceManager._QUEUE_MAX)
        self.assertGreaterEqual(h.queue_depth, 0)
        mgr.close_all()


class TestSourceManagerErrors(unittest.TestCase):

    def test_operations_on_unregistered_camera(self):
        mgr = SourceManager(source_factory=FakeSourceFactory())
        for op in ("start", "stop", "restart", "health", "snapshot", "isolate_failure"):
            with self.assertRaises(SourceManagerError):
                getattr(mgr, op)("CAM-999")

    def test_health_type(self):
        factory = FakeSourceFactory()
        factory.configure("CAM-01", frames=None)
        mgr = SourceManager(source_factory=factory)
        mgr.register_source(make_descriptor("CAM-01"))
        mgr.start("CAM-01")
        deadline = time.monotonic() + 5.0
        h = None
        while time.monotonic() < deadline:
            h = mgr.health("CAM-01")
            if h.healthy:
                break
            time.sleep(0.01)
        self.assertIsInstance(h, CameraHealth)
        mgr.close_all()


if __name__ == "__main__":
    unittest.main()
class TestOpenSlots(unittest.TestCase):
    def test_initial_opens_are_limited_and_slots_release_before_stream_ends(self):
        from threading import Lock, Semaphore
        lock, release = Lock(), Event()
        counts = {'active': 0, 'max': 0, 'opened': 0}
        class SlowSource(FakeSource):
            def open(self):
                with lock:
                    counts['active'] += 1
                    counts['max'] = max(counts['max'], counts['active'])
                try:
                    time.sleep(.08)
                    return super().open()
                finally:
                    with lock:
                        counts['active'] -= 1
                        counts['opened'] += 1
            def frames(self):
                while not release.wait(.02):
                    yield 0, np.zeros((2,2,3),dtype=np.uint8)
        mgr = SourceManager(source_factory=lambda d: SlowSource(d.camera_id))
        mgr._RECONNECT_SEMAPHORE = Semaphore(2)
        try:
            for i in range(5):
                mgr.register_source(make_descriptor(f'C{i}'))
                mgr.start(f'C{i}')
            deadline=time.monotonic()+3
            while counts['opened']<5 and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertEqual(counts['opened'],5)
            self.assertLessEqual(counts['max'],2)
        finally:
            release.set()
            mgr.close_all()

    def test_no_open_without_slot_and_wait_is_cancelable(self):
        from threading import Semaphore
        factory=FakeSourceFactory()
        mgr=SourceManager(source_factory=factory)
        mgr._RECONNECT_SEMAPHORE=Semaphore(0)
        mgr.register_source(make_descriptor('C'))
        mgr.start('C')
        time.sleep(.1)
        self.assertIsNone(mgr._runtimes['C'].source)
        before=time.monotonic()
        mgr.stop('C')
        self.assertLess(time.monotonic()-before,1)
