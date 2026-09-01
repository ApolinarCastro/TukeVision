"""Reproduce slow consumer / full queue behavior in FFmpegSupervisedSource."""
import time
import pytest
from unittest import mock
import numpy as np
from src.capture.ffmpeg_supervised import FFmpegSupervisedSource

def test_slow_consumer_does_not_block_reader_and_updates_last_valid_at():
    """Verify that if the consumer reads slowly or stops reading:
    1. The reader loop continues draining stdout (no pipe deadlock).
    2. _queue drops oldest frames (bounded memory).
    3. _last_valid_at continues advancing as new frames arrive from stdout.
    4. The watchdog does NOT trigger a false STALL while stdout produces data.
    """
    s = FFmpegSupervisedSource('rtsp://127.0.0.1:1/test', max_width=64,
                               rtsp_open_timeout_ms=3000, frame_stall_timeout_s=1.0)
    w, h = 64, 48
    frame_bytes = w * h * 3
    # Script produces 30 frames at 20 fps (1.5 seconds of video)
    code = (
        f'import os, time\n'
        f'for i in range(30):\n'
        f'    os.write(1, bytes([i % 256]) * {frame_bytes})\n'
        f'    time.sleep(0.05)\n'
        f'time.sleep(10)\n'
    )
    import sys
    cmd = [sys.executable, '-u', '-c', code]
    
    with mock.patch('src.capture.ffmpeg_supervised._probe_size', return_value=((w, h), "")), \
         mock.patch.object(s, '_build_ffmpeg_cmd', return_value=cmd):
        try:
            s.open()
            # Do NOT read anything for 0.8 seconds (simulating completely stalled consumer/inference)
            initial_valid_at = s._last_valid_at
            time.sleep(0.8)
            
            # 1. Reader must have advanced and updated _last_valid_at continuously
            assert s._last_valid_at > initial_valid_at
            assert s._readable_frames > 5
            # 2. Queue must be bounded to _QUEUE_MAX (8)
            assert len(s._queue) <= s._QUEUE_MAX
            # 3. Watchdog must not have stalled because stdout was actively delivering frames
            assert s.stall_count == 0
            assert s.state == "OPEN"
            
            # Now read one frame: it should be one of the newest dropped-oldest frames
            idx, frame = s.read()
            assert idx > 0
            assert frame.shape == (h, w, 3)
        finally:
            s.close()
