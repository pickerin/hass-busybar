"""Minimal protobuf wire-format decoder for the BUSY Bar state stream.

Decodes only the fields this integration uses (input events, timer state)
from busybar-protobuf's State message. Hand-rolled to avoid a protobuf
dependency; the wire format is stable and the message surface is tiny.
Schema: https://github.com/busy-app/busybar-protobuf
"""

from __future__ import annotations

import gzip
import json
from typing import Any


def _read_varint(buf: bytes, i: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def _fields(buf: bytes):
    """Yield (field_number, wire_type, value) for a protobuf message."""
    i = 0
    while i < len(buf):
        tag, i = _read_varint(buf, i)
        field, wire = tag >> 3, tag & 0x07
        if wire == 0:  # varint
            value, i = _read_varint(buf, i)
        elif wire == 1:  # 64-bit
            value, i = buf[i : i + 8], i + 8
        elif wire == 2:  # length-delimited
            length, i = _read_varint(buf, i)
            value, i = buf[i : i + length], i + length
        elif wire == 5:  # 32-bit
            value, i = buf[i : i + 4], i + 4
        else:  # unsupported wire type; cannot continue safely
            return
        yield field, wire, value


def _zigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


BUTTONS = {0: "ok", 1: "back", 2: "start"}
ACTIONS = {0: "press", 1: "release"}
POSITIONS = {0: "busy", 1: "custom", 2: "off", 3: "apps", 4: "settings"}


def _decode_input_event(buf: bytes) -> dict[str, Any] | None:
    for field, _, value in _fields(buf):
        if field == 1:  # ButtonEvent
            button, action = 0, 0
            for f, _, v in _fields(value):
                if f == 1:
                    button = v
                elif f == 2:
                    action = v
            return {
                "type": "button",
                "button": BUTTONS.get(button, str(button)),
                "action": ACTIONS.get(action, str(action)),
            }
        if field == 2:  # SwitchEvent
            position = 0
            for f, _, v in _fields(value):
                if f == 1:
                    position = v
            return {"type": "switch", "position": POSITIONS.get(position, str(position))}
        if field == 3:  # EncoderEvent
            delta = 0
            for f, _, v in _fields(value):
                if f == 1:
                    delta = _zigzag(v)
            return {"type": "encoder", "delta": delta}
    return None


def _decode_json_wrapper(buf: bytes) -> Any | None:
    """BSB_Util.Json: compression (1), data (2)."""
    compression, data = 0, b""
    for field, _, value in _fields(buf):
        if field == 1:
            compression = value
        elif field == 2:
            data = value
    if not data:
        return None
    if compression == 1:
        data = gzip.decompress(data)
    return json.loads(data)


def decode_state(buf: bytes) -> list[dict[str, Any]]:
    """Decode a State message into a list of updates we care about.

    Returns dicts: {"type": "button"|"switch"|"encoder", ...} for input
    events, {"type": "timer", "data": <parsed json>} for timer updates.
    """
    updates: list[dict[str, Any]] = []
    for field, _, value in _fields(buf):
        if field != 2:  # State.updates
            continue
        for f, _, v in _fields(value):
            if f == 11:  # StateUpdate.input
                event = _decode_input_event(v)
                if event:
                    updates.append(event)
            elif f == 12:  # StateUpdate.timer
                for tf, _, tv in _fields(v):
                    if tf == 1:  # Timer.json
                        data = _decode_json_wrapper(tv)
                        if data is not None:
                            updates.append({"type": "timer", "data": data})
    return updates
