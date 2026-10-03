"""TC-P038-01 packing boundary corruption.

Intervention: Perturb packed sample boundaries, row padding, or crop parity
while preserving plausible image dimensions.
Expected: Decode using the declared layout or reject the unsupported arrangement
before processing color.
Negative: Treating every RAW buffer as contiguous sixteen-bit pixels must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while "
    "preserving plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement "
    "before processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."

_CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
_PACKING = ("packed10", "packed12", "unpacked16")
_CODES = ("min", "max")
_PAYLOAD_KEYS = (
    "width",
    "height",
    "rowPadding",
    "cropLeft",
    "cropTop",
    "cropWidth",
    "cropHeight",
    "cfa",
    "packing",
    "sampleCode",
    "treatAsContiguous16",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "layout_accepted")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Accept a declared layout or reject it before any color processing."""
    width, height, padding, crop, cfa, packing, code, contiguous = _payload(payload)
    crop_text = f"{crop[2]}x{crop[3]}+{crop[0]}+{crop[1]}"
    preserved = [
        f"dimensions:{width}x{height}",
        f"cfa:{cfa}",
        f"packing:{packing}",
        f"padding:{padding}",
        f"crop:{crop_text}",
        f"code:{code}",
    ]
    odd = any(value % 2 for value in crop)
    outside = crop[0] + crop[2] > width or crop[1] + crop[3] > height
    rejected: list[str] = []
    if contiguous:
        rejected.append("contiguous-sixteen-bit")
    if odd or outside:
        rejected.append("unsupported-layout")
    if rejected:
        decision = "rejected"
        reasons = [EXPECTED, "rejected before processing color"]
        if contiguous:
            reasons.append(NEGATIVE)
        if odd or outside:
            reasons.append("unsupported arrangement rejected before processing color")
        questions = ["color processing not started"]
    else:
        decision = "layout_accepted"
        reasons = [
            EXPECTED,
            "decoded using the declared layout",
            "row padding stays outside the sample stream",
            "color was not processed by this layout gate",
        ]
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int, int, int, tuple[int, int, int, int], str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = _dim(payload["width"], "width")
    height = _dim(payload["height"], "height")
    padding = payload["rowPadding"]
    if type(padding) is not int or padding < 0 or padding > 4096:
        raise ValueError("rowPadding must be an int from 0 through 4096")
    crop = (
        _nonneg(payload["cropLeft"], "cropLeft"),
        _nonneg(payload["cropTop"], "cropTop"),
        _positive(payload["cropWidth"], "cropWidth"),
        _positive(payload["cropHeight"], "cropHeight"),
    )
    cfa = payload["cfa"]
    if cfa not in _CFA:
        raise ValueError("cfa must be a supported Bayer phase")
    packing = payload["packing"]
    if packing not in _PACKING:
        raise ValueError("packing must be a declared layout")
    code = payload["sampleCode"]
    if code not in _CODES:
        raise ValueError("sampleCode must be min or max")
    contiguous = payload["treatAsContiguous16"]
    if type(contiguous) is not bool:
        raise ValueError("treatAsContiguous16 must be a bool")
    return width, height, padding, crop, cfa, packing, code, contiguous


def _dim(value: object, label: str) -> int:
    if type(value) is not int or value < 2 or value > 8192 or value % 2:
        raise ValueError(label + " must be a plausible even dimension")
    return value


def _positive(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _nonneg(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("layout decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
