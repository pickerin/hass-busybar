"""Decoder test for screen.py. Run: python tests/screen_test.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.busybar.screen import DISPLAYS, decode_frame

# Front RGB888 passthrough
front_len = 72 * 16 * 3
rgb = bytes(range(256)) * (front_len // 256) + bytes(front_len % 256)
assert decode_frame(rgb, "front") == rgb

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
assert decode_frame(base64.b64encode(rgb), "front") is None
assert decode_frame(base64.b64decode(base64.b64encode(rgb)), "front") == rgb

# Unknown length -> None
assert decode_frame(b"\x00" * 17, "front") is None

print("ALL SCREEN TESTS PASSED")
