"""TC-P059-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and exact
unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P059-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = (
    "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
)
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."

_PLANES = ("Y-UV", "UV-Y", "interleaved", "unsupported")
_ALIGNMENTS = ("high-six", "low-six")
_REPEATS = ("none", "padded-rows", "chroma-endpoint", "unsupported-plane")
_PAYLOAD_KEYS = (
    "nominalWidth",
    "nominalHeight",
    "rowStride",
    "cropX",
    "cropY",
    "cropW",
    "cropH",
    "planeArrangement",
    "alignment",
    "unpackedCode",
    "packedWord",
    "repeat",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "layout_checked")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Accept only high-six Y-UV layouts whose packed word matches the code."""
    (
        width,
        height,
        stride,
        crop_x,
        crop_y,
        crop_w,
        crop_h,
        plane,
        alignment,
        code,
        word,
        repeat,
    ) = _payload(payload)
    preserved = [
        f"size:{width}x{height}",
        f"stride:{stride}",
        f"crop:{crop_w}x{crop_h}+{crop_x}+{crop_y}",
        "plane:" + plane,
        "alignment:" + alignment,
        f"code:{code}",
        f"word:{word}",
        "repeat:" + repeat,
    ]
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION]
    if alignment == "low-six":
        rejected.append("low-six-bit-alignment")
        reasons.append(NEGATIVE)
    elif word != (code << 6):
        rejected.append("unpacked-mismatch")
        reasons.append("packed word does not equal the high-six unpacked code")
    if plane != "Y-UV":
        rejected.append("unsupported-plane")
    if stride < width:
        rejected.append("stride-bounds")
    if crop_w <= 0 or crop_h <= 0 or crop_x + crop_w > width or crop_y + crop_h > height:
        rejected.append("crop-bounds")
    if rejected:
        reasons.append("nominal dimensions were kept and the layout was not handled")
        return _result("rejected", reasons, rejected, preserved, ["unsupported layout was not handled"])
    reasons.append("supported layout passed bounds checks and unpacked-code verification")
    return _result(
        "layout_checked",
        reasons,
        [],
        preserved,
        ["layout check is not ten-bit fidelity"],
    )


def _positive(value: object, label: str, zero_ok: bool = False) -> int:
    if type(value) is not int:
        raise ValueError(label + " must be an int")
    if zero_ok:
        if value < 0:
            raise ValueError(label + " must be a non-negative int")
    elif value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = _positive(payload["nominalWidth"], "nominalWidth")
    height = _positive(payload["nominalHeight"], "nominalHeight")
    stride = _positive(payload["rowStride"], "rowStride")
    crop_x = _positive(payload["cropX"], "cropX", True)
    crop_y = _positive(payload["cropY"], "cropY", True)
    crop_w = _positive(payload["cropW"], "cropW", True)
    crop_h = _positive(payload["cropH"], "cropH", True)
    plane = payload["planeArrangement"]
    if plane not in _PLANES:
        raise ValueError("planeArrangement is unsupported")
    alignment = payload["alignment"]
    if alignment not in _ALIGNMENTS:
        raise ValueError("alignment must be high-six or low-six")
    code = payload["unpackedCode"]
    if type(code) is not int or not 0 <= code <= 1023:
        raise ValueError("unpackedCode must be an int from 0 through 1023")
    word = payload["packedWord"]
    if type(word) is not int or not 0 <= word <= 65535:
        raise ValueError("packedWord must be an int from 0 through 65535")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    return (
        width,
        height,
        stride,
        crop_x,
        crop_y,
        crop_w,
        crop_h,
        plane,
        alignment,
        code,
        word,
        repeat,
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-04 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
