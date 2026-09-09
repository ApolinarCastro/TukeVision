import pytest
import numpy as np
from src.ui.tk_view import fit_display_size, _clamp_pan, build_viewport_display_image

def test_fit_display_size_respects_original_w():
    # HD source
    w, h = fit_display_size(640, 360, 1920, 1080, allow_upscale=True, original_w=1280)
    assert w > 640 and h > 360  # Upscales because original was HD
    
    # SD source
    w, h = fit_display_size(176, 120, 1920, 1080, allow_upscale=True, original_w=352)
    assert w == 176 and h == 120  # Native SD anti-upscale respects rule

def test_clamp_pan_within_bounds():
    # 1280x720, 2x zoom -> crop is 640x360
    # pan_x can be at most 320 in either direction
    px, py = _clamp_pan(400, 400, 1280, 720, 640, 360)
    assert px == 320
    assert py == 180

def test_build_viewport_display_image():
    # Simulate an HD frame 1280x720
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Zoom 1.0 (no upscale needed for 1280 viewport, but let's say max viewport is 1000x1000)
    img_1 = build_viewport_display_image(frame, 1000, 1000, 1.0, allow_upscale=True)
    assert img_1.size[0] == 1000
    
    # Zoom 2.0 HD
    img_2 = build_viewport_display_image(frame, 1000, 1000, 2.0, allow_upscale=True)
    assert img_2.size[0] == 1000  # Should upscale crop to fill viewport
    
    # Simulate an SD frame 352x240
    frame_sd = np.zeros((240, 352, 3), dtype=np.uint8)
    img_sd_1 = build_viewport_display_image(frame_sd, 1000, 1000, 1.0, allow_upscale=True)
    assert img_sd_1.size[0] == 352  # No upscale for SD
    
    img_sd_2 = build_viewport_display_image(frame_sd, 1000, 1000, 2.0, allow_upscale=True)
    assert img_sd_2.size[0] == 176  # 2x zoom of SD, doesn't upscale either
