"""Capture regressions: real local subprocesses, no DVR or credentials needed."""
import shutil
import subprocess
import sys
import time
from unittest import mock

import pytest

from src.capture.ffmpeg_supervised import FFmpegSupervisedSource
from src.capture.video_source import VideoSourceError


def source(timeout=1000):
    return FFmpegSupervisedSource('rtsp://127.0.0.1:1/test', max_width=64,
                                  rtsp_open_timeout_ms=timeout, frame_stall_timeout_s=1)


def test_command_options_supported_by_installed_ffmpeg():
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg not installed')
    cmd = source()._build_ffmpeg_cmd(64, 48, 64, 48)
    result = subprocess.run(cmd, capture_output=True, timeout=5)
    assert b'Unrecognized option' not in result.stderr
    assert b'Option not found' not in result.stderr
    assert result.returncode != 0  # no server on localhost port 1


def test_probe_failure_does_not_guess_raw_frame_dimensions():
    s = source()
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=(None, "AUTH_FAILED")), mock.patch('subprocess.Popen') as popen:
        with pytest.raises(VideoSourceError, match='FFPROBE_NO_DIMENSIONS'):
            s.open()
        popen.assert_not_called()


def test_first_frame_timeout_does_not_wait_for_stderr_eof():
    s = source(200)
    cmd = [sys.executable, '-u', '-c', 'import sys,time;sys.stderr.write("partial error");sys.stderr.flush();time.sleep(30)']
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((64,48), "")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=cmd):
        before = time.monotonic()
        with pytest.raises(VideoSourceError, match='no first frame'):
            s.open()
        assert time.monotonic() - before < 5
        assert s._proc is None
        assert s._reader_thread is None


def test_partial_raw_reads_and_stderr_flood_are_drained():
    s = source(3000)
    code = ('import os,time; os.write(2,b"x"*200000); '
            'os.write(1,b"\\x11"*71); os.write(1,b"\\x11"*(64*48*3-71)); time.sleep(30)')
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((64,48), "")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=[sys.executable,'-u','-c',code]):
        try:
            s.open()
            proc = s._proc
            idx, frame = s.read()
            assert idx == 0 and frame.shape == (48,64,3)
            assert (frame == 17).all()
            assert len(s._stderr_tail) <= 4096
        finally:
            s.close()
        assert proc.poll() is not None


def test_watchdog_terminates_source_after_first_frame_stalls():
    s = source(1000)
    code = 'import os,time;os.write(1,b"x"*(64*48*3));time.sleep(30)'
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((64,48), "")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=[sys.executable,'-u','-c',code]):
        try:
            s.open()
            proc = s._proc
            deadline = time.monotonic()+4
            while proc.poll() is None and time.monotonic()<deadline:
                time.sleep(.05)
            assert proc.poll() is not None
            assert s.stall_count == 1
        finally:
            s.close()


def test_real_ffmpeg_produces_frames_through_reader():
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg not installed')
    s = source(3000)
    cmd = ['ffmpeg','-hide_banner','-loglevel','error','-re','-f','lavfi','-i',
           'testsrc=size=64x48:rate=10','-threads','1','-pix_fmt','bgr24','-f','rawvideo','pipe:1']
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((64,48), "")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=cmd):
        try:
            s.open()
            proc = s._proc
            first = s.read()
            second = s.read()
            assert first[1].shape == (48,64,3)
            assert second[0] > first[0]
        finally:
            s.close()
        assert proc.poll() is not None


def test_stderr_credentials_not_returned_in_exception():
    s = FFmpegSupervisedSource('rtsp://127.0.0.1:1/test', username='user',password='secret',rtsp_open_timeout_ms=300)
    code = 'import sys;sys.stderr.write("rtsp://user:secret@127.0.0.1/test")'
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((64,48), "")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=[sys.executable,'-u','-c',code]):
        with pytest.raises(VideoSourceError) as caught:
            s.open()
        assert 'secret' not in str(caught.value)


def test_resilient_reconnect_uses_cached_dimensions_on_probe_timeout():
    s = source(1000)
    s._width, s._height = 64, 48
    code = 'import os,time;os.write(1,b"x"*(64*48*3*2));time.sleep(30)'
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=(None, "PROBE_TIMEOUT")), mock.patch.object(s, '_build_ffmpeg_cmd', return_value=[sys.executable,'-u','-c',code]):
        try:
            meta = s.open()
            assert meta.width == 64
            assert meta.height == 48
        finally:
            s.close()
