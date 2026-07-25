"""Decoder test for pb.py using hand-encoded protobuf wire bytes.

Run: python tests/pb_test.py
"""

import gzip
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.busybar.pb import decode_state


def varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out += bytes([b | 0x80])
        else:
            return out + bytes([b])


def field(num: int, wire: int, payload: bytes) -> bytes:
    tag = varint((num << 3) | wire)
    if wire == 2:
        return tag + varint(len(payload)) + payload
    return tag + payload


def zigzag(n: int) -> int:
    return (n << 1) ^ (n >> 63)


def state(*updates: bytes) -> bytes:
    msg = field(1, 1, (0).to_bytes(8, "little"))  # timestamp fixed64
    for u in updates:
        msg += field(2, 2, u)
    return msg


# START button press: ButtonEvent{button=START(2), action=PRESS(0 omitted)}
button_ev = field(1, 2, field(1, 0, varint(2)))
update_button = field(11, 2, button_ev)

# Switch to CUSTOM(1)
switch_ev = field(2, 2, field(1, 0, varint(1)))
update_switch = field(11, 2, switch_ev)

# Encoder delta -3 (sint32 zigzag)
enc_ev = field(3, 2, field(1, 0, varint(zigzag(-3))))
update_encoder = field(11, 2, enc_ev)

# Empty ButtonEvent = OK press (proto3 omits zero values)
update_ok = field(11, 2, field(1, 2, b""))

# Timer update with gzipped JSON
timer_json = {"snapshot": {"type": "INFINITE", "card_id": "x", "is_paused": False}}
json_wrapper = field(1, 0, varint(1)) + field(
    2, 2, gzip.compress(json.dumps(timer_json).encode())
)
update_timer = field(12, 2, field(1, 2, json_wrapper))

decoded = decode_state(
    state(update_button, update_switch, update_encoder, update_ok, update_timer)
)

assert decoded[0] == {"type": "button", "button": "start", "action": "press"}, decoded[0]
assert decoded[1] == {"type": "switch", "position": "custom"}, decoded[1]
assert decoded[2] == {"type": "encoder", "delta": -3}, decoded[2]
assert decoded[3] == {"type": "button", "button": "ok", "action": "press"}, decoded[3]
assert decoded[4] == {"type": "timer", "data": timer_json}, decoded[4]

# Unknown fields must not break decoding
noise = field(5, 0, varint(7)) + field(9, 2, b"junk")
assert decode_state(state(noise + update_button))[0]["button"] == "start"

print("ALL PB TESTS PASSED")
