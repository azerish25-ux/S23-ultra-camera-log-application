"""TC-P064-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and exact
unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P064-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = (
    "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
)
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."
REPEAT = "Repeat with padded rows, chroma endpoints, and unsupported plane layouts."

_LAYOUTS = ("p010-msb", "low-six", "padded-row", "chroma-endpoint", "unsupported")
_SUPPORTED = {"p010-msb", "padded-row", "chroma-endpoint"}
_CROPS = ("none", "changed")
_PAYLOAD_KEYS = (
    "width",
    "height",
    "stride",
    "crop",
    "layout",
    "boundsChecked",
    "unpackedMatches",
    "explicitlySupported",
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
    """Accept only explicit P010 layouts and reject low-six alignment."""
    width, height, stride, crop, layout, bounds, unpacked, supported = _payload(payload)
    preserved = [
        f"{width}x{height}",
        f"stride:{stride}",
        f"crop:{crop}",
        f"layout:{layout}",
        f"bounds-checked:{_flag(bounds)}",
        f"unpacked-matches:{_flag(unpacked)}",
        f"explicitly-supported:{_flag(supported)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT, "nominal dimensions were kept"]
    rejected: list[str] = []
    if layout == "low-six":
        rejected.append("low-six-bit-aligned")
        reasons.append(NEGATIVE)
        if supported:
            reasons.append("explicit support does not legalize low-six alignment")
    if layout == "unsupported":
        rejected.append("unsupported-plane")
        reasons.append("plane layout is not an explicitly supported arrangement")
    if layout == "padded-row" and stride <= width:
        rejected.append("padding-not-in-stride")
        reasons.append("padded rows require a stride wider than the nominal width")
    if stride < width:
        rejected.append("stride-below-width")
        reasons.append("row stride is below the nominal width")
    if crop == "changed":
        rejected.append("crop-changed")
        reasons.append("crop changed while nominal dimensions stayed the same")
    if not bounds:
        rejected.append("bounds-not-checked")
        reasons.append("bounds were not checked")
    if not unpacked:
        rejected.append("unpacked-code-mismatch")
        reasons.append("unpacked codes did not match")
    if layout in _SUPPORTED and not supported:
        rejected.append("not-explicitly-supported")
    if layout == "unsupported" and supported:
        rejected.append("support-flag-contradiction")
    if rejected:
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("explicitly supported layout passed bounds and unpacked-code checks")
        questions.append("a handled layout is not ten-bit fidelity or physical qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = payload["width"]
    height = payload["height"]
    stride = payload["stride"]
    for name, value in (("width", width), ("height", height), ("stride", stride)):
        if type(value) is not int or isinstance(value, bool) or value <= 0:
            raise ValueError(name + " must be a positive int")
    crop = payload["crop"]
    if crop not in _CROPS:
        raise ValueError("crop is unsupported")
    layout = payload["layout"]
    if layout not in _LAYOUTS:
        raise ValueError("layout is unsupported")
    bounds = payload["boundsChecked"]
    unpacked = payload["unpackedMatches"]
    supported = payload["explicitlySupported"]
    for name, value in (
        ("boundsChecked", bounds),
        ("unpackedMatches", unpacked),
        ("explicitlySupported", supported),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    return width, height, stride, crop, layout, bounds, unpacked, supported


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-04 must not yield qualified or allowed")
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
