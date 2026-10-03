"""TC-P058-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and
exact unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P058-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."

_LAYOUTS = ("nv12-msb10", "padded-rows", "chroma-endpoint", "unsupported-planes", "low-six-align")
_CROPS = ("none", "shifted")
_PAYLOAD_KEYS = (
    "nominalWidth",
    "nominalHeight",
    "stride",
    "layout",
    "crop",
    "unpackedExpected",
    "unpackedObserved",
    "boundsOk",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Accept only MSB-aligned NV12 with exact codes. Low-six alignment fails."""
    width, height, stride, layout, crop, expected, observed, bounds_ok = _payload(payload)
    preserved = [
        f"{width}x{height}",
        f"stride:{stride}",
        f"layout:{layout}",
        f"crop:{crop}",
        f"expected:{expected}",
        f"observed:{observed}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions: list[str] = []
    if layout == "low-six-align":
        rejected.append("low-six-bit-alignment")
        reasons.append(NEGATIVE)
    if layout == "padded-rows":
        rejected.append("padded-rows")
    if layout == "chroma-endpoint":
        rejected.append("chroma-endpoint")
    if layout == "unsupported-planes":
        rejected.append("unsupported-planes")
    if crop == "shifted":
        rejected.append("crop-shift")
    if not bounds_ok:
        rejected.append("bounds")
    if layout == "nv12-msb10" and stride != width * 2:
        rejected.append("stride")
    if expected != observed:
        rejected.append("unpacked-code")
    if rejected:
        decision = "rejected"
        reasons.append("nominal dimensions were kept and the layout was not accepted")
        questions.append("only nv12-msb10 with bounds and exact codes is supported")
    else:
        decision = "layout_checked"
        reasons.append("supported layout passed bounds and unpacked-code checks")
        questions.append("layout check is not ten-bit fidelity")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = payload["nominalWidth"]
    height = payload["nominalHeight"]
    stride = payload["stride"]
    for name, value in (("nominalWidth", width), ("nominalHeight", height), ("stride", stride)):
        if type(value) is not int or value < 1:
            raise ValueError(name + " must be a positive int")
    layout = payload["layout"]
    if layout not in _LAYOUTS:
        raise ValueError("layout is unsupported")
    crop = payload["crop"]
    if crop not in _CROPS:
        raise ValueError("crop is unsupported")
    expected = payload["unpackedExpected"]
    observed = payload["unpackedObserved"]
    for name, value in (("unpackedExpected", expected), ("unpackedObserved", observed)):
        if type(value) is not int or value < 0 or value > 1023:
            raise ValueError(name + " must be a ten-bit code")
    bounds_ok = payload["boundsOk"]
    if type(bounds_ok) is not bool:
        raise ValueError("boundsOk must be a bool")
    return width, height, stride, layout, crop, expected, observed, bounds_ok


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-04 must not yield qualified or allowed")
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
