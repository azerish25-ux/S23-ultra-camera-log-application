#!/usr/bin/env python3
"""P035 packed RAW decoding fixtures.

Tiny synthetic mosaics for RAW_SENSOR, RAW10, and RAW12 carry known codes,
row padding, an odd crop, and every CFA parity. Decoders use the declared
layout only. Padding bytes stay in the buffer and out of the code plane.

The deliberate mutant — reading every source as contiguous sixteen-bit
native-endian samples — is rejected. This module does not probe a device,
does not qualify a physical S23, and does not execute TC-P035-01 through
TC-P035-08.
"""

from __future__ import annotations

import re
import sys
from typing import Any


PHASE = "P035"
CASE_ID = "P035"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-packed-raw-fixture"
METHOD = (
    "Construct tiny synthetic mosaics for supported RAW formats with known code values, "
    "row padding, crop offsets, and all CFA parities. Use independent bit-level references. "
    "Do not assume RAW_SENSOR, RAW10, and RAW12 have interchangeable memory layouts."
)
FIXTURE = (
    "Alternating minimum and maximum sample codes in padded rows with a crop beginning "
    "on an odd coordinate."
)
ORACLE = (
    "Decoded codes and CFA coordinates match the independent fixture exactly, "
    "with padding untouched."
)
MUTANT = "Read every source as contiguous sixteen-bit native-endian samples."

FORMATS = ("RAW_SENSOR", "RAW10", "RAW12")
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
MAX_CODE = {"RAW_SENSOR": 65535, "RAW10": 1023, "RAW12": 4095}
FORMAT_SLUG = {"RAW_SENSOR": "raw-sensor", "RAW10": "raw10", "RAW12": "raw12"}
# Row-major 2×2 phase at the buffer origin, not the crop origin.
CFA_PHASE = {
    "RGGB": ("R", "G", "G", "B"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
    "BGGR": ("B", "G", "G", "R"),
}
OPEN = (
    "physical S23 capture unverified",
    "no demosaic applied",
    "no color transform applied",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX_BYTES = re.compile(r"^(?:[0-9a-f]{2})+$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "mosaics",
}
MOSAIC_KEYS = {
    "id",
    "format",
    "cfa",
    "width",
    "height",
    "rowStride",
    "cropLeft",
    "cropTop",
    "cropWidth",
    "cropHeight",
    "packedHex",
    "paddingHex",
    "codes",
    "cropCodes",
    "cropChannels",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def mosaic_id(fmt: str, cfa: str) -> str:
    return FORMAT_SLUG[fmt] + "-" + cfa.lower()


def expected_ids() -> list[str]:
    return [mosaic_id(fmt, cfa) for fmt in FORMATS for cfa in CFAS]


def payload_length(fmt: str, width: int) -> int:
    """Packed sample bytes in one row, excluding stride padding."""
    require(fmt in FORMATS, "unknown RAW format")
    require(type(width) is int and width > 0 and width % 4 == 0, "width must be a positive multiple of 4")
    if fmt == "RAW_SENSOR":
        return width * 2
    if fmt == "RAW10":
        return (width // 4) * 5
    return (width // 2) * 3


def channel_at(cfa: str, x: int, y: int) -> str:
    """CFA channel at an absolute buffer coordinate. Crop origin is not reset."""
    require(cfa in CFA_PHASE, "unknown CFA")
    require(type(x) is int and type(y) is int and x >= 0 and y >= 0, "coordinate")
    return CFA_PHASE[cfa][(y % 2) * 2 + (x % 2)]


def expected_code(fmt: str, x: int, y: int) -> int:
    """Independent checkerboard: minimum on even x+y, format maximum on odd."""
    require(fmt in MAX_CODE, "unknown RAW format")
    return MAX_CODE[fmt] if (x + y) % 2 else 0


def memory_layout(fmt: str) -> dict[str, object]:
    """Declared memory layout. Distinct formats are not interchangeable."""
    require(fmt in FORMATS, "unknown RAW format")
    if fmt == "RAW_SENSOR":
        return {"bits": 16, "groupPixels": 1, "groupBytes": 2, "endian": "little"}
    if fmt == "RAW10":
        return {"bits": 10, "groupPixels": 4, "groupBytes": 5, "endian": "packed-raw10"}
    return {"bits": 12, "groupPixels": 2, "groupBytes": 3, "endian": "packed-raw12"}


def layouts_equivalent(left: str, right: str) -> bool:
    return memory_layout(left) == memory_layout(right)


def _unpack_row(fmt: str, row: bytes, width: int) -> list[int]:
    if fmt == "RAW_SENSOR":
        return [row[index * 2] | (row[index * 2 + 1] << 8) for index in range(width)]
    if fmt == "RAW10":
        values: list[int] = []
        for group in range(width // 4):
            block = row[group * 5:group * 5 + 5]
            values.extend((
                (block[0] << 2) | (block[4] & 0x03),
                (block[1] << 2) | ((block[4] >> 2) & 0x03),
                (block[2] << 2) | ((block[4] >> 4) & 0x03),
                (block[3] << 2) | ((block[4] >> 6) & 0x03),
            ))
        return values
    values = []
    for group in range(width // 2):
        block = row[group * 3:group * 3 + 3]
        values.extend((
            (block[0] << 4) | (block[2] & 0x0F),
            (block[1] << 4) | ((block[2] >> 4) & 0x0F),
        ))
    return values


def _pack_row(fmt: str, samples: list[int]) -> bytes:
    if fmt == "RAW_SENSOR":
        out = bytearray()
        for value in samples:
            out.append(value & 0xFF)
            out.append((value >> 8) & 0xFF)
        return bytes(out)
    if fmt == "RAW10":
        out = bytearray()
        for group in range(len(samples) // 4):
            pixels = samples[group * 4:group * 4 + 4]
            out.extend((pixel >> 2) & 0xFF for pixel in pixels)
            out.append(
                ((pixels[3] & 3) << 6)
                | ((pixels[2] & 3) << 4)
                | ((pixels[1] & 3) << 2)
                | (pixels[0] & 3)
            )
        return bytes(out)
    out = bytearray()
    for group in range(len(samples) // 2):
        first, second = samples[group * 2], samples[group * 2 + 1]
        out.append((first >> 4) & 0xFF)
        out.append((second >> 4) & 0xFF)
        out.append(((second & 0x0F) << 4) | (first & 0x0F))
    return bytes(out)


def decode_row(fmt: str, row: bytes, width: int) -> list[int]:
    """Unpack one packed row. Padding is not part of `row`."""
    require(isinstance(row, (bytes, bytearray)), "row must be bytes")
    require(len(row) == payload_length(fmt, width), "row payload length")
    return _unpack_row(fmt, bytes(row), width)


def decode_plane(
    fmt: str,
    buffer: bytes | bytearray,
    width: int,
    height: int,
    row_stride: int,
) -> list[list[int]]:
    """Decode a padded plane. Does not write the buffer or read padding as samples."""
    require(type(height) is int and height > 0 and height % 2 == 0, "height must be a positive even int")
    payload = payload_length(fmt, width)
    require(
        type(row_stride) is int and row_stride > payload,
        "row stride must be greater than the packed payload",
    )
    raw = bytes(buffer)
    require(len(raw) == row_stride * height, "buffer length must be stride times height")
    return [
        _unpack_row(fmt, raw[y * row_stride:y * row_stride + payload], width)
        for y in range(height)
    ]


def pack_plane(fmt: str, codes: list[list[int]], row_stride: int, padding: bytes) -> bytes:
    """Pack codes with an explicit little-endian or bit layout and append padding."""
    require(isinstance(codes, list) and codes, "codes")
    height = len(codes)
    width = len(codes[0])
    require(all(isinstance(row, list) and len(row) == width for row in codes), "ragged codes")
    payload = payload_length(fmt, width)
    require(isinstance(padding, (bytes, bytearray)) and len(padding) == row_stride - payload,
            "padding must fill the stride and nothing else")
    limit = MAX_CODE[fmt]
    rows: list[bytes] = []
    for row in codes:
        require(all(type(value) is int and 0 <= value <= limit for value in row), "code out of range")
        rows.append(_pack_row(fmt, row) + bytes(padding))
    require(len(rows) == height and height % 2 == 0, "height")
    return b"".join(rows)


def mutant_plane(buffer: bytes | bytearray, width: int, height: int) -> list[list[int]]:
    """Mutant: contiguous native-endian uint16, ignoring packing and row stride."""
    require(type(width) is int and width > 0 and type(height) is int and height > 0, "size")
    raw = bytes(buffer)
    count = width * height
    values: list[int] = []
    for index in range(count):
        chunk = raw[index * 2:index * 2 + 2]
        if len(chunk) < 2:
            values.append(-1)
        else:
            values.append(int.from_bytes(chunk, sys.byteorder))
    return [values[y * width:(y + 1) * width] for y in range(height)]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P035 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def inventory(mosaics: list[dict]) -> list[str]:
    """Declared evidence. A decode failure must not replace these tokens."""
    rows: list[str] = []
    for mosaic in mosaics:
        ident = mosaic["id"]
        flat = ",".join(str(code) for row in mosaic["codes"] for code in row)
        channels = ",".join(channel for row in mosaic["cropChannels"] for channel in row)
        rows.append(f"id:{ident}")
        rows.append(f"format:{mosaic['format']}")
        rows.append(f"cfa:{mosaic['cfa']}")
        rows.append(f"pad:{ident}:{mosaic['paddingHex']}")
        rows.append(f"codes:{ident}:{flat}")
        rows.append(f"crop:{ident}:{mosaic['cropLeft']},{mosaic['cropTop']}")
        rows.append(f"channels:{ident}:{channels}")
    return rows


def _int_field(value: object, label: str, low: int, high: int) -> int:
    require(type(value) is int and low <= value <= high, label + " out of range")
    return value


def _codes(value: object, fmt: str, width: int, height: int, label: str) -> list[list[int]]:
    require(isinstance(value, list) and len(value) == height, label + " height")
    rows: list[list[int]] = []
    limit = MAX_CODE[fmt]
    for y, row in enumerate(value):
        require(isinstance(row, list) and len(row) == width, label + " width")
        parsed: list[int] = []
        for x, code in enumerate(row):
            require(type(code) is int and 0 <= code <= limit, label + " code")
            require(code == expected_code(fmt, x, y), label + " must be the alternating fixture")
            parsed.append(code)
        rows.append(parsed)
    return rows


def _channels(value: object, cfa: str, left: int, top: int, width: int, height: int) -> list[list[str]]:
    require(isinstance(value, list) and len(value) == height, "cropChannels height")
    rows: list[list[str]] = []
    for y, row in enumerate(value):
        require(isinstance(row, list) and len(row) == width, "cropChannels width")
        parsed: list[str] = []
        for x, channel in enumerate(row):
            expect = channel_at(cfa, left + x, top + y)
            require(channel == expect, "crop channel must use the absolute CFA phase")
            parsed.append(channel)
        rows.append(parsed)
    return rows


def _mosaic(value: object, index: int) -> dict:
    item = exact_keys(value, MOSAIC_KEYS, f"mosaic {index}")
    fmt = item["format"]
    cfa = item["cfa"]
    require(fmt in FORMATS, "mosaic format")
    require(cfa in CFAS, "mosaic cfa")
    require(item["id"] == mosaic_id(fmt, cfa), "mosaic id must name format and CFA")
    width = _int_field(item["width"], "width", 4, 16)
    height = _int_field(item["height"], "height", 2, 16)
    require(width % 4 == 0 and height % 2 == 0, "tiny even geometry required")
    payload = payload_length(fmt, width)
    stride = _int_field(item["rowStride"], "rowStride", payload + 1, 64)
    left = _int_field(item["cropLeft"], "cropLeft", 0, width - 1)
    top = _int_field(item["cropTop"], "cropTop", 0, height - 1)
    crop_w = _int_field(item["cropWidth"], "cropWidth", 1, width - left)
    crop_h = _int_field(item["cropHeight"], "cropHeight", 1, height - top)
    require(left % 2 == 1 and top % 2 == 1, "crop must begin on an odd coordinate")
    packed = item["packedHex"]
    padding = item["paddingHex"]
    require(isinstance(packed, str) and HEX_BYTES.fullmatch(packed) is not None, "packedHex")
    require(isinstance(padding, str) and HEX_BYTES.fullmatch(padding) is not None, "paddingHex")
    require(len(packed) == stride * height * 2, "packedHex length")
    require(len(padding) == (stride - payload) * 2, "paddingHex length")
    codes = _codes(item["codes"], fmt, width, height, "codes")
    crop = _codes(item["cropCodes"], fmt, crop_w, crop_h, "cropCodes")
    for y in range(crop_h):
        for x in range(crop_w):
            require(crop[y][x] == codes[top + y][left + x], "cropCodes must be the odd-origin window")
    _channels(item["cropChannels"], cfa, left, top, crop_w, crop_h)
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P035 packed-RAW fixture schema."""
    exact_keys(document, DOCUMENT_KEYS, "packed raw document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P035")
    require(document["mapId"] == MAP_ID, "mapId must be s23-packed-raw-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "packed raw document needs the P035 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    mosaics = document["mosaics"]
    require(isinstance(mosaics, list), "mosaics must be a list")
    parsed = [_mosaic(item, index) for index, item in enumerate(mosaics)]
    require([item["id"] for item in parsed] == expected_ids(),
            "mosaics must cover every format and CFA parity in order")


def _padding_ok(mosaic: dict, raw: bytes) -> bool:
    stride = mosaic["rowStride"]
    pad = bytes.fromhex(mosaic["paddingHex"])
    payload = stride - len(pad)
    return all(raw[y * stride + payload:(y + 1) * stride] == pad for y in range(mosaic["height"]))


def assess(document: dict) -> dict:
    """Match decoded codes and CFA coordinates to the independent fixture.

    Padding is checked and left unchanged. The contiguous uint16 mutant is not
    a successful decode. Decision is never qualified or allowed.
    """
    validate_document(document)
    preserved = inventory(document["mosaics"])
    rejected: list[str] = []
    for mosaic in document["mosaics"]:
        raw = bytes.fromhex(mosaic["packedHex"])
        decoded = decode_plane(
            mosaic["format"], raw, mosaic["width"], mosaic["height"], mosaic["rowStride"]
        )
        if decoded != mosaic["codes"]:
            rejected.append("decode-mismatch:" + mosaic["id"])
        if not _padding_ok(mosaic, raw):
            rejected.append("padding-mismatch:" + mosaic["id"])
        if mutant_plane(raw, mosaic["width"], mosaic["height"]) == mosaic["codes"]:
            rejected.append("mutant-indistinguishable:" + mosaic["id"])
    if rejected:
        return _result(
            "rejected",
            [ORACLE, "declared layout did not match the independent fixture"],
            rejected,
            preserved,
            list(OPEN),
        )
    return _result(
        "decoded",
        [
            ORACLE,
            "decoded codes and CFA coordinates match the independent fixture",
            "padding bytes were not consumed as samples",
            "RAW_SENSOR, RAW10, and RAW12 were not treated as one memory layout",
            "a decoded host fixture is not physical S23 qualification",
        ],
        [],
        preserved,
        list(OPEN),
    )


def reject_mutant(document: dict) -> dict:
    """Apply the mutant reading and refuse it when it disagrees with the fixture.

    Preserved results stay the declared golden inventory. Mutant samples are
    not written back over the codes or the padding.
    """
    validate_document(document)
    preserved = inventory(document["mosaics"])
    indistinguishable = [
        mosaic["id"]
        for mosaic in document["mosaics"]
        if mutant_plane(bytes.fromhex(mosaic["packedHex"]), mosaic["width"], mosaic["height"])
        == mosaic["codes"]
    ]
    if indistinguishable:
        return _result(
            "rejected",
            [MUTANT, "mutant matched the golden codes"],
            ["mutant-indistinguishable:" + ident for ident in indistinguishable],
            preserved,
            list(OPEN),
        )
    return _result(
        "rejected",
        [
            MUTANT,
            ORACLE,
            "contiguous native-endian samples do not match the packed fixture",
        ],
        ["contiguous-sixteen-bit-native-endian"],
        preserved,
        list(OPEN),
    )
