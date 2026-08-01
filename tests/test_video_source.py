"""Pruebas unitarias para src.capture.video_source."""

import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np

from src.capture.video_source import (
    VideoSource,
    VideoNotFoundError,
    VideoOpenError,
    VideoReadError,
    VideoMetadata,
)


class TestVideoSource(unittest.TestCase):
    """Pruebas para la clase VideoSource."""

    def _create_test_video(
        self,
        path: Path,
        width: int = 320,
        height: int = 240,
        fps: float = 10.0,
        frame_count: int = 30,
        fourcc: str = "mp4v"
    ) -> None:
        """Crea un video de prueba temporal."""
        fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
        writer = cv2.VideoWriter(str(path), fourcc_code, fps, (width, height))
        for i in range(frame_count):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Dibujar algo para que no sea todo negro
            cv2.rectangle(frame, (50 + i * 2, 50), (100 + i * 2, 100), (0, 255, 0), -1)
            writer.write(frame)
        writer.release()

    def test_open_valid_video(self) -> None:
        """Verifica que un video válido se abre correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path)

            source = VideoSource(str(video_path))
            metadata = source.open()

            self.assertIsInstance(metadata, VideoMetadata)
            self.assertEqual(metadata.width, 320)
            self.assertEqual(metadata.height, 240)
            self.assertAlmostEqual(metadata.fps, 10.0, places=1)
            self.assertEqual(metadata.total_frames, 30)
            self.assertAlmostEqual(metadata.duration_seconds, 3.0, places=1)

            source.close()

    def test_metadata_properties(self) -> None:
        """Verifica que los metadatos se exponen correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path, width=640, height=480, fps=25.0, frame_count=50)

            source = VideoSource(str(video_path))
            metadata = source.open()

            self.assertEqual(metadata.width, 640)
            self.assertEqual(metadata.height, 480)
            self.assertAlmostEqual(metadata.fps, 25.0, places=1)
            self.assertEqual(metadata.total_frames, 50)
            self.assertAlmostEqual(metadata.duration_seconds, 2.0, places=1)
            self.assertEqual(metadata.path, str(video_path))

            source.close()

    def test_read_frames(self) -> None:
        """Verifica que se pueden leer fotogramas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path, width=320, height=240, fps=10.0, frame_count=20)

            source = VideoSource(str(video_path))
            source.open()

            frames_read = 0
            for idx, frame in source.frames():
                self.assertIsInstance(frame, np.ndarray)
                self.assertEqual(len(frame.shape), 3)
                self.assertEqual(frame.shape[2], 3)  # BGR
                frames_read += 1

            self.assertEqual(frames_read, 20)
            self.assertEqual(source.readable_frames, 20)

            source.close()

    def test_resize_preserves_aspect_ratio(self) -> None:
        """Verifica que la reducción de resolución conserva la proporción."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            # Video ancho (640x240 = ratio 2.67)
            self._create_test_video(video_path, width=640, height=240, fps=10.0, frame_count=10)

            source = VideoSource(str(video_path), max_width=320)
            source.open()

            for idx, frame in source.frames():
                h, w = frame.shape[:2]
                self.assertLessEqual(w, 320)
                # Proporción original: 640/240 = 2.666...
                # Proporción redimensionada: w/h debe ser ~2.67
                ratio = w / h
                self.assertAlmostEqual(ratio, 640 / 240, places=1)

            source.close()

    def test_resize_no_change_when_smaller(self) -> None:
        """Verifica que no hay redimensionamiento si ya es menor al máximo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path, width=320, height=240, fps=10.0, frame_count=5)

            source = VideoSource(str(video_path), max_width=640)
            source.open()

            for idx, frame in source.frames():
                h, w = frame.shape[:2]
                self.assertEqual(w, 320)
                self.assertEqual(h, 240)

            source.close()

    def test_process_every_n_frames(self) -> None:
        """Verifica el salto de fotogramas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path, width=320, height=240, fps=10.0, frame_count=10)

            source = VideoSource(str(video_path), process_every_n_frames=2)
            source.open()

            frames_read = 0
            for idx, frame in source.frames():
                # Solo índices pares (0, 2, 4, 6, 8)
                self.assertEqual(idx % 2, 0)
                frames_read += 1

            self.assertEqual(frames_read, 5)  # 10 frames / 2 = 5
            source.close()

    def test_nonexistent_file_raises_error(self) -> None:
        """Verifica error controlado para archivo inexistente."""
        source = VideoSource("no_existe_video.mp4")
        with self.assertRaises(VideoNotFoundError):
            source.open()

    def test_directory_instead_of_file_raises_error(self) -> None:
        """Verifica error controlado cuando la ruta es un directorio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = VideoSource(tmpdir)
            with self.assertRaises(VideoNotFoundError):
                source.open()

    def test_invalid_video_raises_error(self) -> None:
        """Verifica error controlado para archivo que no es video válido."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "not_a_video.txt"
            video_path.write_text("esto no es un video")

            source = VideoSource(str(video_path))
            with self.assertRaises(VideoOpenError):
                source.open()

    def test_context_manager(self) -> None:
        """Verifica que el context manager abre y cierra correctamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test_video.mp4"
            self._create_test_video(video_path)

            with VideoSource(str(video_path)) as source:
                metadata = source.open()
                self.assertIsNotNone(metadata)
                frames = list(source.frames())
                self.assertEqual(len(frames), 30)

            # Al salir del with, el recurso debe estar liberado
            # (no hay forma directa de verificarlo, pero no debe lanzar error)

    def test_close_without_open(self) -> None:
        """Verifica que close() sin open() no falla."""
        source = VideoSource("dummy.mp4")
        source.close()  # No debe lanzar excepción


if __name__ == "__main__":
    unittest.main()