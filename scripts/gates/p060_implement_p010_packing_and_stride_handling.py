#!/usr/bin/env python3
"""P060 P010 packing and stride handling on a host fixture.

Write ten-bit samples into explicit luma and chroma planes. Row stride,
pixel stride, and a nonzero crop rectangle are part of the geometry. An
independent unpacker reads the high ten bits of each sixteen-bit word.
Padding and guard bytes stay untouched. Limited-range luma and chroma use
different quantization formulas. Unknown plane layouts are rejected.

The deliberate mutant — ten-bit codes stored in the low bits of each
sixteen-bit word — is rejected. This module does not probe a device, does
not qualify a physical S23, and does not execute TC-P060-01 through TC-P060-08.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


PHASE = "P060"
CASE_ID = "P060"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-p010-packing-fixture"
METHOD = (
    "Handle supported row strides, pixel strides, crop rectangles, and chroma layout "
    "explicitly. Validate alignment and bounds. Keep limited-range luma and chroma "
    "quantization formulas distinct. Unknown plane configurations are rejected, not guessed."
)
FIXTURE = (
    "Padded luma and chroma rows with known endpoint codes and a nonzero crop rectangle."
)
ORACLE = (
    "An independent unpacker reconstructs exact intended codes while guard bytes and "
    "padding remain untouched."
)
MUTANT = "Store ten-bit codes in the low bits of each sixteen-bit word."
HOST_LIMIT = "host fixture does not qualify a physical S23 or ten-bit image fidelity"
DECLARED_STORE = "msb"
MUTANT_STORE = "lsb"
STORES = (DECLARED_STORE, MUTANT_STORE)
SUPPORTED_LAYOUT = "420-interleaved"
LAYOUTS = (
    SUPPORTED_LAYOUT,
    "420-planar",
    "422-interleaved",
    "444-planar",
    "contiguous-guess",
)
RANGES = ("limited", "full")
LUMA_ENDPOINTS = frozenset({"64", "940"})
CHROMA_ENDPOINTS = frozenset({"64", "512", "960"})
HEX40 = re.compile(r"^[0-9a-f]{40}$")
UINT = re.compile(r"0|[1-9][0-9]*")
SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "planes",
    "endpoints",
    "lumaSamples",
    "chromaSamples",
}
PLANE_KEYS = {
    "chromaLayout",
    "range",
    "store",
    "bufferWidth",
    "bufferHeight",
    "cropLeft",
    "cropTop",
    "cropRight",
    "cropBottom",
    "yRowStride",
    "yPixelStride",
    "uvRowStride",
    "uvPixelStride",
    "guard",
}
ENDPOINT_KEYS = {
    "lumaBlack",
    "lumaWhite",
    "chromaLow",
    "chromaNeutral",
    "chromaHigh",
}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "geometry_retained"}


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


def quantize_luma_limited(unit: str) -> int:
    """10-bit limited luma: round(876*E + 64), E in 0..1. Not the chroma formula."""
    require(isinstance(unit, str) and SIGNED.fullmatch(unit) is not None and not unit.startswith("-"),
            "luma unit must be a canonical non-negative decimal")
    number = Decimal(unit)
    require(Decimal(0) <= number <= Decimal(1), "luma unit must be inside 0..1")
    code = (number * Decimal(876) + Decimal(64)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(code)


def quantize_chroma_limited(unit: str) -> int:
    """10-bit limited chroma: round(896*E + 512), E in -0.5..0.5. Not the luma formula."""
    require(isinstance(unit, str) and SIGNED.fullmatch(unit) is not None and unit != "-0",
            "chroma unit must be a canonical signed decimal")
    number = Decimal(unit)
    require(Decimal("-0.5") <= number <= Decimal("0.5"), "chroma unit must be inside -0.5..0.5")
    code = (number * Decimal(896) + Decimal(512)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(code)


def formula_endpoints() -> dict[str, str]:
    return {
        "lumaBlack": str(quantize_luma_limited("0")),
        "lumaWhite": str(quantize_luma_limited("1")),
        "chromaLow": str(quantize_chroma_limited("-0.5")),
        "chromaNeutral": str(quantize_chroma_limited("0")),
        "chromaHigh": str(quantize_chroma_limited("0.5")),
    }


def pack_msb(code: int) -> int:
    """Place a ten-bit code in the high bits of a sixteen-bit P010 word."""
    require(0 <= code <= 1023, "code out of ten-bit range")
    return code << 6


def pack_lsb(code: int) -> int:
    """Mutant: store the ten-bit code in the low bits. Not a P010 word."""
    require(0 <= code <= 1023, "code out of ten-bit range")
    return code


def independent_unpack_word(word: int) -> int:
    """Independent P010 reader. Always takes the high ten bits, never the low-bit mutant."""
    require(0 <= word <= 65535, "word out of sixteen-bit range")
    return (word >> 6) & 0x3FF


def _uint(value: object, label: str, limit: int) -> int:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    number = int(value)
    require(0 <= number <= limit, label + " is out of range")
    return number


def _codes(value: object, label: str, expected: int | None, allowed: frozenset[str] | None) -> list[int]:
    require(isinstance(value, list), label + " must be a list")
    if expected is not None:
        require(len(value) == expected, label + " length does not match the crop")
    else:
        require(1 <= len(value) <= 64, label + " length is unsupported")
    codes: list[int] = []
    for index, item in enumerate(value):
        require(isinstance(item, str) and (allowed is None or item in allowed),
                f"{label}[{index}] is not a known endpoint code")
        codes.append(_uint(item, f"{label}[{index}]", 1023))
    return codes


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P060 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be strings")
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


def _load_planes(document: dict) -> dict[str, Any]:
    planes = exact_keys(document["planes"], PLANE_KEYS, "planes")
    layout = planes["chromaLayout"]
    require(layout in LAYOUTS, "chromaLayout is not a known token")
    require(planes["range"] in RANGES, "range must be limited or full")
    require(planes["store"] in STORES, "store must be msb or lsb")
    width = _uint(planes["bufferWidth"], "bufferWidth", 32)
    height = _uint(planes["bufferHeight"], "bufferHeight", 32)
    left = _uint(planes["cropLeft"], "cropLeft", 32)
    top = _uint(planes["cropTop"], "cropTop", 32)
    right = _uint(planes["cropRight"], "cropRight", 32)
    bottom = _uint(planes["cropBottom"], "cropBottom", 32)
    y_stride = _uint(planes["yRowStride"], "yRowStride", 4096)
    y_pixel = _uint(planes["yPixelStride"], "yPixelStride", 64)
    uv_stride = _uint(planes["uvRowStride"], "uvRowStride", 4096)
    uv_pixel = _uint(planes["uvPixelStride"], "uvPixelStride", 64)
    guard = _uint(planes["guard"], "guard", 255)
    require(width >= 2 and height >= 2, "buffer dimensions must cover a chroma site")
    require(width % 2 == 0 and height % 2 == 0, "buffer dimensions must be even")
    require(0 <= left < right <= width and 0 <= top < bottom <= height, "crop is outside the buffer")
    require(left > 0 or top > 0, "crop origin must be nonzero")
    require(not (left == 0 and top == 0 and right == width and bottom == height),
            "crop must not be the entire buffer")
    require((right - left) % 2 == 0 and (bottom - top) % 2 == 0, "crop extents must be even")
    require(left % 2 == 0 and top % 2 == 0 and right % 2 == 0 and bottom % 2 == 0,
            "crop edges must be even")
    return {
        "chromaLayout": layout,
        "range": planes["range"],
        "store": planes["store"],
        "bufferWidth": width,
        "bufferHeight": height,
        "cropLeft": left,
        "cropTop": top,
        "cropRight": right,
        "cropBottom": bottom,
        "yRowStride": y_stride,
        "yPixelStride": y_pixel,
        "uvRowStride": uv_stride,
        "uvPixelStride": uv_pixel,
        "guard": guard,
    }


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P060 packing fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "packing document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P060")
    require(document["mapId"] == MAP_ID, "mapId must be s23-p010-packing-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "packing document needs the P060 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    geometry = _load_planes(document)
    require(geometry["store"] == DECLARED_STORE, "fixture store must be msb; lsb is the mutant argument")
    endpoints = exact_keys(document["endpoints"], ENDPOINT_KEYS, "endpoints")
    for key, expected in formula_endpoints().items():
        require(endpoints[key] == expected or _uint(endpoints[key], key, 1023) >= 0,
                key + " must be a ten-bit code string")
        require(isinstance(endpoints[key], str) and UINT.fullmatch(endpoints[key]) is not None,
                key + " must be a canonical integer string")
    crop_w = geometry["cropRight"] - geometry["cropLeft"]
    crop_h = geometry["cropBottom"] - geometry["cropTop"]
    _codes(document["lumaSamples"], "lumaSamples", crop_w * crop_h, None)
    chroma_count = (crop_w // 2) * (crop_h // 2) * 2
    _codes(document["chromaSamples"], "chromaSamples", chroma_count, None)


def _bounds(geometry: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    width = geometry["bufferWidth"]
    height = geometry["bufferHeight"]
    y_pixel = geometry["yPixelStride"]
    uv_pixel = geometry["uvPixelStride"]
    y_stride = geometry["yRowStride"]
    uv_stride = geometry["uvRowStride"]
    if y_pixel < 2 or y_pixel % 2 != 0:
        claims.append("luma-pixel-stride")
    elif (width - 1) * y_pixel + 2 > y_stride:
        claims.append("luma-row-overflow")
    if uv_pixel < 4 or uv_pixel % 2 != 0:
        claims.append("chroma-pixel-stride")
    else:
        chroma_width = width // 2
        if chroma_width <= 0 or (chroma_width - 1) * uv_pixel + 4 > uv_stride:
            claims.append("chroma-row-overflow")
    if y_stride % 2 != 0 or uv_stride % 2 != 0:
        claims.append("odd-row-stride")
    if geometry["yRowStride"] <= width * y_pixel or geometry["uvRowStride"] <= (width // 2) * uv_pixel:
        claims.append("missing-row-padding")
    return claims


def _store_word(code: int, store: str) -> int:
    if store == DECLARED_STORE:
        return pack_msb(code)
    if store == MUTANT_STORE:
        return pack_lsb(code)
    raise ValueError("store must be msb or lsb")


def _put(buf: bytearray, offset: int, row_start: int, row_stride: int, word: int) -> None:
    require(row_start <= offset and offset + 2 <= row_start + row_stride, "sample crosses the row")
    require(offset + 2 <= len(buf), "sample exceeds the plane")
    buf[offset] = word & 0xFF
    buf[offset + 1] = (word >> 8) & 0xFF


def write_planes(
    geometry: dict[str, Any],
    luma: list[int],
    chroma: list[int],
    store: str,
) -> tuple[bytearray, bytearray]:
    """Write only in-crop samples. Every other byte stays the guard value."""
    guard = geometry["guard"]
    ybuf = bytearray([guard]) * (geometry["yRowStride"] * geometry["bufferHeight"])
    uvbuf = bytearray([guard]) * (geometry["uvRowStride"] * (geometry["bufferHeight"] // 2))
    index = 0
    for y in range(geometry["cropTop"], geometry["cropBottom"]):
        for x in range(geometry["cropLeft"], geometry["cropRight"]):
            offset = y * geometry["yRowStride"] + x * geometry["yPixelStride"]
            _put(ybuf, offset, y * geometry["yRowStride"], geometry["yRowStride"],
                 _store_word(luma[index], store))
            index += 1
    index = 0
    for cy in range(geometry["cropTop"] // 2, geometry["cropBottom"] // 2):
        for cx in range(geometry["cropLeft"] // 2, geometry["cropRight"] // 2):
            base = cy * geometry["uvRowStride"] + cx * geometry["uvPixelStride"]
            row_start = cy * geometry["uvRowStride"]
            _put(uvbuf, base, row_start, geometry["uvRowStride"], _store_word(chroma[index], store))
            _put(uvbuf, base + 2, row_start, geometry["uvRowStride"],
                 _store_word(chroma[index + 1], store))
            index += 2
    return ybuf, uvbuf


def independent_unpack(
    ybuf: bytearray,
    uvbuf: bytearray,
    geometry: dict[str, Any],
) -> tuple[list[int], list[int]]:
    """Read the crop with P010 high-bit placement. Ignores the writer store flag."""
    luma: list[int] = []
    for y in range(geometry["cropTop"], geometry["cropBottom"]):
        for x in range(geometry["cropLeft"], geometry["cropRight"]):
            offset = y * geometry["yRowStride"] + x * geometry["yPixelStride"]
            word = ybuf[offset] | (ybuf[offset + 1] << 8)
            luma.append(independent_unpack_word(word))
    chroma: list[int] = []
    for cy in range(geometry["cropTop"] // 2, geometry["cropBottom"] // 2):
        for cx in range(geometry["cropLeft"] // 2, geometry["cropRight"] // 2):
            base = cy * geometry["uvRowStride"] + cx * geometry["uvPixelStride"]
            cb = uvbuf[base] | (uvbuf[base + 1] << 8)
            cr = uvbuf[base + 2] | (uvbuf[base + 3] << 8)
            chroma.append(independent_unpack_word(cb))
            chroma.append(independent_unpack_word(cr))
    return luma, chroma


def _written_offsets(geometry: dict[str, Any]) -> tuple[set[int], set[int]]:
    y_offsets: set[int] = set()
    for y in range(geometry["cropTop"], geometry["cropBottom"]):
        for x in range(geometry["cropLeft"], geometry["cropRight"]):
            offset = y * geometry["yRowStride"] + x * geometry["yPixelStride"]
            y_offsets.add(offset)
            y_offsets.add(offset + 1)
    uv_offsets: set[int] = set()
    for cy in range(geometry["cropTop"] // 2, geometry["cropBottom"] // 2):
        for cx in range(geometry["cropLeft"] // 2, geometry["cropRight"] // 2):
            base = cy * geometry["uvRowStride"] + cx * geometry["uvPixelStride"]
            uv_offsets.update(range(base, base + 4))
    return y_offsets, uv_offsets


def _padding_offsets(geometry: dict[str, Any]) -> tuple[set[int], set[int]]:
    y_pad: set[int] = set()
    span = geometry["bufferWidth"] * geometry["yPixelStride"]
    for y in range(geometry["bufferHeight"]):
        start = y * geometry["yRowStride"] + span
        y_pad.update(range(start, (y + 1) * geometry["yRowStride"]))
    uv_pad: set[int] = set()
    chroma_span = (geometry["bufferWidth"] // 2) * geometry["uvPixelStride"]
    for cy in range(geometry["bufferHeight"] // 2):
        start = cy * geometry["uvRowStride"] + chroma_span
        uv_pad.update(range(start, (cy + 1) * geometry["uvRowStride"]))
    return y_pad, uv_pad


def _untouched(buf: bytearray, skip: set[int], guard: int) -> bool:
    return all(buf[index] == guard for index in range(len(buf)) if index not in skip)


def _join(codes: list[int]) -> str:
    return ",".join(str(code) for code in codes)


def _inventory(
    geometry: dict[str, Any],
    endpoints: dict[str, str],
    luma: list[int],
    chroma: list[int],
    store: str,
    unpacked: tuple[list[int], list[int]] | None,
    guards_ok: bool | None,
    padding_ok: bool | None,
    packed_first: int | None,
) -> list[str]:
    y_pad = geometry["yRowStride"] - geometry["bufferWidth"] * geometry["yPixelStride"]
    uv_pad = geometry["uvRowStride"] - (geometry["bufferWidth"] // 2) * geometry["uvPixelStride"]
    preserved = [
        f"crop:{geometry['cropLeft']},{geometry['cropTop']},{geometry['cropRight']},{geometry['cropBottom']}",
        f"buffer:{geometry['bufferWidth']}x{geometry['bufferHeight']}",
        f"y-stride:{geometry['yRowStride']}/{geometry['yPixelStride']}",
        f"uv-stride:{geometry['uvRowStride']}/{geometry['uvPixelStride']}",
        f"layout:{geometry['chromaLayout']}",
        f"range:{geometry['range']}",
        f"guard:{geometry['guard']}",
        f"row-padding-y:{y_pad}",
        f"row-padding-uv:{uv_pad}",
        f"luma-black:{endpoints['lumaBlack']}",
        f"luma-white:{endpoints['lumaWhite']}",
        f"chroma-low:{endpoints['chromaLow']}",
        f"chroma-neutral:{endpoints['chromaNeutral']}",
        f"chroma-high:{endpoints['chromaHigh']}",
        f"intended-luma:{_join(luma)}",
        f"intended-chroma:{_join(chroma)}",
        f"store:{store}",
    ]
    if unpacked is None:
        preserved.append("unpacked:not-guessed")
    else:
        preserved.append(f"unpacked-luma:{_join(unpacked[0])}")
        preserved.append(f"unpacked-chroma:{_join(unpacked[1])}")
    if packed_first is not None:
        preserved.append(f"packed-luma-0:{packed_first}")
    preserved.append("guards-untouched:" + ("yes" if guards_ok else "no" if guards_ok is False else "untested"))
    preserved.append("padding-untouched:" + ("yes" if padding_ok else "no" if padding_ok is False else "untested"))
    return preserved


def _questions(geometry: dict[str, Any], guessed: bool) -> list[str]:
    questions = [
        "host fixture is not a physical S23 measurement",
        "limited-range formulas are declared conventions, not a measured camera",
    ]
    if guessed:
        questions.append("unknown plane configuration was rejected and not guessed")
    else:
        questions.append(
            f"crop {geometry['cropLeft']},{geometry['cropTop']},"
            f"{geometry['cropRight']},{geometry['cropBottom']} was applied explicitly"
        )
    return questions


def assess(document: dict, store: str = DECLARED_STORE) -> dict:
    """Pack the fixture and compare it with an independent high-bit unpacker.

    store "lsb" is the mutant. It writes ten-bit codes into the low bits.
    The unpacker still reads the high bits, so the mutant cannot come back
    as geometry_retained. Unknown layouts are rejected without a contiguous guess.
    """
    validate_document(document)
    require(store in STORES, "store must be msb or lsb")
    geometry = _load_planes(document)
    endpoints = {key: document["endpoints"][key] for key in ENDPOINT_KEYS}
    crop_w = geometry["cropRight"] - geometry["cropLeft"]
    crop_h = geometry["cropBottom"] - geometry["cropTop"]
    luma = _codes(document["lumaSamples"], "lumaSamples", crop_w * crop_h, None)
    chroma = _codes(
        document["chromaSamples"],
        "chromaSamples",
        (crop_w // 2) * (crop_h // 2) * 2,
        None,
    )
    claims: list[str] = []
    reasons = [
        "limited luma uses round(876*E+64); limited chroma uses round(896*E+512)",
        f"layout {geometry['chromaLayout']} buffer {geometry['bufferWidth']}x{geometry['bufferHeight']}",
    ]
    supported = (
        geometry["chromaLayout"] == SUPPORTED_LAYOUT
        and geometry["range"] == "limited"
        and geometry["yPixelStride"] == 2
        and geometry["uvPixelStride"] == 4
    )
    if geometry["chromaLayout"] != SUPPORTED_LAYOUT:
        claims.append("unknown-plane-configuration")
        reasons.append("unknown plane configuration was rejected and not guessed")
    if geometry["range"] != "limited":
        claims.append("unsupported-range")
    if geometry["yPixelStride"] != 2 or geometry["uvPixelStride"] != 4:
        claims.append("unsupported-pixel-stride")
    if not supported:
        reasons.append(HOST_LIMIT)
        return _result(
            "rejected",
            reasons,
            claims,
            _inventory(geometry, endpoints, luma, chroma, store, None, None, None, None),
            _questions(geometry, geometry["chromaLayout"] != SUPPORTED_LAYOUT),
        )
    bound_claims = _bounds(geometry)
    if bound_claims:
        claims.extend(bound_claims)
        reasons.append("alignment or bounds checks failed before any sample was written")
        reasons.append(HOST_LIMIT)
        return _result(
            "rejected",
            reasons,
            claims,
            _inventory(geometry, endpoints, luma, chroma, store, None, None, None, None),
            _questions(geometry, False),
        )
    expected = formula_endpoints()
    if any(endpoints[key] != expected[key] for key in expected):
        claims.append("quantizer-not-distinct")
        reasons.append("endpoint codes do not match the distinct limited-range formulas")
    if any(str(code) not in LUMA_ENDPOINTS for code in luma) or not LUMA_ENDPOINTS.issubset(
        {str(code) for code in luma}
    ):
        claims.append("luma-endpoint-missing")
    if any(str(code) not in CHROMA_ENDPOINTS for code in chroma) or not CHROMA_ENDPOINTS.issubset(
        {str(code) for code in chroma}
    ):
        claims.append("chroma-endpoint-missing")
    if claims:
        reasons.append(HOST_LIMIT)
        return _result(
            "rejected",
            reasons,
            claims,
            _inventory(geometry, endpoints, luma, chroma, store, None, None, None, None),
            _questions(geometry, False),
        )
    ybuf, uvbuf = write_planes(geometry, luma, chroma, store)
    unpacked = independent_unpack(ybuf, uvbuf, geometry)
    y_written, uv_written = _written_offsets(geometry)
    y_pad, uv_pad = _padding_offsets(geometry)
    guards_ok = _untouched(ybuf, y_written, geometry["guard"]) and _untouched(
        uvbuf, uv_written, geometry["guard"]
    )
    padding_ok = all(ybuf[index] == geometry["guard"] for index in y_pad) and all(
        uvbuf[index] == geometry["guard"] for index in uv_pad
    )
    packed_first = _store_word(luma[0], store)
    if store == MUTANT_STORE:
        claims.append("low-bit-ten-bit-store")
        reasons.append(MUTANT)
        reasons.append("the independent unpacker reads the high ten bits and rejects the low-bit store")
    if unpacked != (luma, chroma):
        claims.append("unpacked-code-mismatch")
        reasons.append("independent unpacker did not reconstruct the intended codes")
    if not guards_ok:
        claims.append("guard-bytes-touched")
    if not padding_ok:
        claims.append("padding-touched")
    if not claims and guards_ok and padding_ok and unpacked == (luma, chroma):
        reasons.append(ORACLE)
        reasons.append(HOST_LIMIT)
        decision = "geometry_retained"
    else:
        reasons.append(HOST_LIMIT)
        decision = "rejected"
    return _result(
        decision,
        reasons,
        claims,
        _inventory(
            geometry,
            endpoints,
            luma,
            chroma,
            store,
            unpacked,
            guards_ok,
            padding_ok,
            packed_first,
        ),
        _questions(geometry, False),
    )
