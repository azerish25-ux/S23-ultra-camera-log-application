"""TC-P057-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and exact
unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P057-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping "
    "nominal dimensions."
)
EXPECTED = (
    "Handle only explicitly supported layouts with bounds checks and exact "
    "unpacked-code verification."
)
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."

_LAYOUTS = ("p010-msb", "padded", "low-six", "chroma-endpoint", "unsupported-planes")
_SUPPORTED = {"p010-msb", "padded"}
_PAYLOAD_KEYS = (
    "layout",
    "width",
    "height",
    "nominalWidth",
    "nominalHeight",
    "rowStride",
    "code",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "supported_layout")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Accept only MSB-aligned P010 rows that unpack to the original code."""
    layout, width, height, nominal_w, nominal_h, stride, code = _payload(payload)
    preserved = [
        f"layout:{layout}",
        f"nominal:{nominal_w}x{nominal_h}",
        f"geometry:{width}x{height}",
        f"stride:{stride}",
        f"code:{code}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["supported layout is not ten-bit fidelity or a physical capture"]
    if width != nominal_w or height != nominal_h:
        reasons.append("nominal dimensions were kept while the active geometry changed")
        return _result("rejected", reasons, ["geometry-changed"], preserved, questions)
    if stride < 2 * width:
        reasons.append("row stride failed the bounds check")
        return _result("rejected", reasons, ["stride-bounds"], preserved, questions)
    if layout == "low-six":
        unpacked = _unpack(_pack(code, width, stride, shift=False), width)
        reasons.append(NEGATIVE)
        reasons.append("low six-bit alignment failed exact unpacked-code verification")
        preserved.append(f"unpacked:{unpacked}")
        return _result("rejected", reasons, ["low-six-alignment"], preserved, questions)
    if layout == "chroma-endpoint":
        reasons.append("chroma endpoint layout is not an explicitly supported plane")
        return _result("rejected", reasons, ["chroma-endpoint"], preserved, questions)
    if layout == "unsupported-planes":
        reasons.append("plane arrangement is not explicitly supported")
        return _result("rejected", reasons, ["unsupported-planes"], preserved, questions)
    if layout == "padded" and stride == 2 * width:
        raise ValueError("padded layout needs a stride greater than the active row")
    if layout == "p010-msb" and stride != 2 * width:
        reasons.append("tight P010 row does not include undeclared padding")
        return _result("rejected", reasons, ["unexpected-padding"], preserved, questions)
    unpacked = _unpack(_pack(code, width, stride, shift=True), width)
    if unpacked != code:
        reasons.append("unpacked code did not match")
        preserved.append(f"unpacked:{unpacked}")
        return _result("rejected", reasons, ["unpacked-mismatch"], preserved, questions)
    preserved.append(f"unpacked:{unpacked}")
    reasons.append(f"{layout} passed bounds and exact code verification")
    return _result("supported_layout", reasons, [], preserved, questions)


def _pack(code: int, width: int, stride: int, shift: bool) -> bytes:
    row = bytearray(stride)
    word = code << 6 if shift else code
    encoded = word.to_bytes(2, "little")
    for index in range(width):
        row[2 * index: 2 * index + 2] = encoded
    return bytes(row)


def _unpack(data: bytes, width: int) -> int:
    word = int.from_bytes(data[0:2], "little")
    if word & 0x3F:
        return -1
    value = word >> 6
    for index in range(1, width):
        other = int.from_bytes(data[2 * index: 2 * index + 2], "little")
        if other != word:
            return -1
    return value


def _payload(payload: object) -> tuple[str, int, int, int, int, int, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    layout = payload["layout"]
    if layout not in _LAYOUTS:
        raise ValueError("layout is unknown")
    numbers = []
    for name in ("width", "height", "nominalWidth", "nominalHeight", "rowStride", "code"):
        value = payload[name]
        if type(value) is not int:
            raise ValueError(name + " must be an int")
        numbers.append(value)
    width, height, nominal_w, nominal_h, stride, code = numbers
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("dimensions are out of bounds")
    if not 1 <= nominal_w <= 4096 or not 1 <= nominal_h <= 4096:
        raise ValueError("nominal dimensions are out of bounds")
    if stride <= 0 or stride % 2 or stride > 8192:
        raise ValueError("rowStride must be a positive even int within bounds")
    if not 0 <= code <= 1023:
        raise ValueError("code must be a ten-bit value")
    return layout, width, height, nominal_w, nominal_h, stride, code


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN or layout_guard(decision):
        raise ValueError("decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def layout_guard(decision: str) -> bool:
    return decision not in _DECISIONS
