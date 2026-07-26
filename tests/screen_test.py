"""Decoder test for screen.py. Run: python tests/screen_test.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.busybar.screen import DISPLAYS, decode_frame

# Front 24-bit BGR -> RGB swap (LVGL memory order)
front_len = 72 * 16 * 3
bgr = bytes([10, 20, 30]) * (72 * 16)  # b=10 g=20 r=30
rgb = decode_frame(bgr, "front")
assert rgb[:3] == bytes([30, 20, 10])
assert len(rgb) == front_len

# Back 4-bit packed: 0xF0 -> px1=0 (black), px2=15 (white)
back_len = (160 * 80) // 2
packed = bytes([0xF0]) * back_len
out = decode_frame(packed, "back")
assert len(out) == 160 * 80 * 3
assert out[0:3] == b"\x00\x00\x00"
assert out[3:6] == b"\xff\xff\xff"

# Base64-encoded transport (firmware MG_REPLY_IMAGE) decoded upstream in views;
# decoder itself still rejects the undecoded text
import base64
assert decode_frame(base64.b64encode(bgr), "front") is None
assert decode_frame(base64.b64decode(base64.b64encode(bgr)), "front") == rgb

# Unknown length -> None
assert decode_frame(b"\x00" * 17, "front") is None

print("ALL SCREEN TESTS PASSED")
