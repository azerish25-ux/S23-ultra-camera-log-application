"""TC-P036-01 packing boundary corruption.

Intervention: Perturb packed sample boundaries, row padding, or crop parity
while preserving plausible image dimensions.
Expected: Decode using the declared layout or reject the unsupported arrangement
before processing color.
Negative: Treating every RAW buffer as contiguous sixteen-bit pixels must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P036-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while preserving "
    "plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement before "
    "processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."

_LAYOUTS = ("declared_packed", "contiguous_sixteen_bit")
_PARITY = ("even", "odd")
_CFA = ("RGGB", "BGGR", "GRBG", "GBRG")
_CODES = ("minimum", "maximum", "mid")
_BOUNDARIES = ("aligned", "perturbed")
_PAYLOAD_KEYS = (
    "width",
    "height",
    "layout",
    "rowPaddingBytes",
    "cropParity",
    "cfa",
    "code",
    "packedBoundary",
    "processColor",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "layout_rejected", "decoded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Decode a declared layout, or reject it before color. Keep dimensions."""
    fields = _payload(payload)
    preserved = [
        f"{fields['width']}x{fields['height']}",
        f"cfa:{fields['cfa']}",
        f"code:{fields['code']}",
        f"padding:{fields['rowPaddingBytes']}",
        f"parity:{fields['cropParity']}",
    ]
    supported = (
        fields["layout"] == "declared_packed"
        and fields["packedBoundary"] == "aligned"
        and fields["cropParity"] == "even"
    )
    rejected: list[str] = []
    if fields["layout"] == "contiguous_sixteen_bit":
        rejected.append("contiguous-sixteen-bit-pixels")
    if fields["packedBoundary"] == "perturbed":
        rejected.append("perturbed-packed-boundary")
    if fields["cropParity"] == "odd":
        rejected.append("odd-crop-parity")
    if not supported and fields["processColor"]:
        rejected.append("color-before-layout-rejection")

    questions: list[str] = []
    if fields["layout"] == "contiguous_sixteen_bit" or (not supported and fields["processColor"]):
        decision = "rejected"
        reasons = [NEGATIVE, EXPECTED, "plausible image dimensions are preserved"]
        questions.append("dimensions preserved")
    elif not supported:
        decision = "layout_rejected"
        reasons = [EXPECTED, "unsupported arrangement rejected before color"]
        questions.append("color was not processed")
    else:
        decision = "decoded"
        reasons = [
            EXPECTED,
            (
                f"declared layout decoded {fields['width']}x{fields['height']} "
                f"{fields['cfa']} code {fields['code']}"
            ),
        ]
        if fields["processColor"]:
            reasons.append("color processed after declared layout decode")
        if fields["rowPaddingBytes"]:
            reasons.append("row padding stayed inside the declared layout")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = payload["width"]
    height = payload["height"]
    if type(width) is not int or width <= 0 or type(height) is not int or height <= 0:
        raise ValueError("width and height must be positive ints")
    layout = payload["layout"]
    if layout not in _LAYOUTS:
        raise ValueError("layout is not a known packing")
    padding = payload["rowPaddingBytes"]
    if type(padding) is not int or padding < 0:
        raise ValueError("rowPaddingBytes must be a non-negative int")
    parity = payload["cropParity"]
    if parity not in _PARITY:
        raise ValueError("cropParity must be even or odd")
    cfa = payload["cfa"]
    if cfa not in _CFA:
        raise ValueError("cfa is not a supported pattern")
    code = payload["code"]
    if code not in _CODES:
        raise ValueError("code must be minimum, maximum, or mid")
    boundary = payload["packedBoundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("packedBoundary must be aligned or perturbed")
    process = payload["processColor"]
    if type(process) is not bool:
        raise ValueError("processColor must be a bool")
    return {
        "width": width,
        "height": height,
        "layout": layout,
        "rowPaddingBytes": padding,
        "cropParity": parity,
        "cfa": cfa,
        "code": code,
        "packedBoundary": boundary,
        "processColor": process,
    }


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
