"""TC-P034-01 packing boundary corruption.

Decode with the declared packed layout, including odd crops and row padding,
or reject the arrangement before color. A contiguous sixteen-bit reading of
a packed buffer is the negative control and is never qualified.
"""

from __future__ import annotations

CASE_ID = "TC-P034-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while "
    "preserving plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement before processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."

LAYOUTS = ("RAW10", "RAW12", "RAW16")
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
_CODE_MAX = {"RAW10": 1023, "RAW12": 4095, "RAW16": 65535}
_PAYLOAD_KEYS = (
    "layout",
    "width",
    "height",
    "rowStride",
    "cropLeft",
    "cropTop",
    "cfa",
    "codeValue",
    "contiguousSixteenBit",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "layout_held"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Hold a declared packing layout or reject it before color."""
    fields = _payload(payload)
    preserved = [
        f"dim:{fields['width']}x{fields['height']}",
        f"stride:{fields['rowStride']}",
        f"crop:{fields['cropLeft']},{fields['cropTop']}",
        f"cfa:{fields['cfa']}",
        f"code:{fields['codeValue']}",
        f"layout:{fields['layout']}",
    ]
    reasons = [INTERVENTION, EXPECTED]
    rejected: list[str] = []
    questions = ["color not processed"]
    minimum = _minimum_stride(fields["layout"], fields["width"])
    if fields["contiguousSixteenBit"]:
        rejected.append("contiguous-sixteen-bit")
    if fields["codeValue"] > _CODE_MAX[fields["layout"]]:
        rejected.append("code-out-of-range")
    if fields["rowStride"] < minimum:
        rejected.append("packing-boundary")
    if rejected:
        reasons.append(NEGATIVE if "contiguous-sixteen-bit" in rejected else
                       "unsupported arrangement rejected before color")
        return _result("rejected", reasons, rejected, preserved, questions)
    if fields["cropLeft"] % 2 or fields["cropTop"] % 2:
        questions.append("odd-crop-phase")
    reasons.append(
        f"declared {fields['layout']} stride {fields['rowStride']} covers minimum {minimum}"
    )
    reasons.append("color was not processed")
    return _result("layout_held", reasons, [], preserved, questions)


def _minimum_stride(layout: str, width: int) -> int:
    if layout == "RAW10":
        return (width * 5 + 3) // 4
    if layout == "RAW12":
        return (width * 3 + 1) // 2
    return width * 2


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    layout = payload["layout"]
    if layout not in LAYOUTS:
        raise ValueError("layout is not supported")
    width = payload["width"]
    height = payload["height"]
    stride = payload["rowStride"]
    crop_left = payload["cropLeft"]
    crop_top = payload["cropTop"]
    if type(width) is not int or not 1 <= width <= 8192:
        raise ValueError("width must be an int from 1 to 8192")
    if type(height) is not int or not 1 <= height <= 8192:
        raise ValueError("height must be an int from 1 to 8192")
    if type(stride) is not int or stride <= 0:
        raise ValueError("rowStride must be a positive int")
    if type(crop_left) is not int or not 0 <= crop_left < width:
        raise ValueError("cropLeft must lie inside the width")
    if type(crop_top) is not int or not 0 <= crop_top < height:
        raise ValueError("cropTop must lie inside the height")
    cfa = payload["cfa"]
    if cfa not in CFAS:
        raise ValueError("cfa is not supported")
    code = payload["codeValue"]
    if type(code) is not int or code < 0:
        raise ValueError("codeValue must be a non-negative int")
    if type(payload["contiguousSixteenBit"]) is not bool:
        raise ValueError("contiguousSixteenBit must be a bool")
    return payload


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("packing decision cannot be qualified or allowed")
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
