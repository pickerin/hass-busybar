"""Framebuffer decoding for the BUSY Bar displays.

Formats per the device firmware and busylib-py:
- front: 72x16, RGB888 (3 bytes/px)
- back: 160x80, 16-level grayscale packed 2 px/byte (low nibble first)
"""

from __future__ import annotations

DISPLAYS = {
    "front": {"index": 0, "width": 72, "height": 16},
    "back": {"index": 1, "width": 160, "height": 80},
}


def decode_frame(data: bytes, display: str) -> bytes | None:
    """Return RGB888 bytes for a raw framebuffer, or None if unrecognized."""
    spec = DISPLAYS[display]
    width, height = spec["width"], spec["height"]
    rgb_len = width * height * 3
    nibble_len = (width * height) // 2
    gray_len = width * height

    if len(data) == rgb_len:
        return data
    if len(data) == nibble_len:
        out = bytearray()
        for byte in data:
            for value in (byte & 0x0F, (byte >> 4) & 0x0F):
                v = value * 17
                out.extend((v, v, v))
        return bytes(out)
    if len(data) == gray_len:
        factor = 17 if display == "back" else 1
        out = bytearray()
        for value in data:
            v = min(255, value * factor)
            out.extend((v, v, v))
        return bytes(out)
    return None
