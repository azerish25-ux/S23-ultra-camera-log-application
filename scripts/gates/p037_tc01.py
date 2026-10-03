"""TC-P037-01 packing boundary corruption.

Decode with the declared packed layout, including row padding and odd crops.
Reject an unsupported packing boundary before color. Treating every RAW buffer
as contiguous sixteen-bit pixels is the negative control and is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P037-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while preserving "
    "plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement before processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."

_CFAS = ("RGGB", "BGGR", "GRBG", "GBRG")
_CODES = ("minimum", "maximum")
_PARITY = ("even", "odd")
_PACKED = (10, 12, 16)
_PAYLOAD_KEYS = (
    "width",
    "height",
    "stride",
    "packedBits",
    "cfa",
    "cropParity",
    "code",
    "contiguous16",
    "layoutDeclared",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Decode a declared layout or reject it before color."""
    fields = _payload(payload)
    reasons = [
        EXPECTED,
        (
            f"code {fields['code']} {fields['width']}x{fields['height']} "
            f"cfa {fields['cfa']} crop {fields['cropParity']}"
        ),
    ]
    rejected: list[str] = []
    minimum = _minimum_stride(fields["width"], fields["packedBits"])
    if fields["contiguous16"]:
        rejected.append("contiguous-sixteen-bit")
        reasons.append(NEGATIVE)
        reasons.append("rejected before color processing")
    if fields["packedBits"] not in (10, 12) or minimum is None:
        rejected.append("unsupported-packing")
        reasons.append("rejected before color processing")
    elif fields["stride"] < minimum:
        rejected.append("unsupported-packing")
        reasons.append("row stride is below the declared packed width")
        reasons.append("rejected before color processing")
    if not fields["layoutDeclared"]:
        rejected.append("undeclared-layout")
        reasons.append("rejected before color processing")

    if rejected:
        decision = "rejected"
    else:
        decision = "decoded_layout"
        padding = fields["stride"] - minimum
        reasons.append(f"decoded with declared layout stride padding {padding}")
        reasons.append("color was not assumed from a contiguous sixteen-bit buffer")

    preserved = [
        f"layout:{fields['width']}x{fields['height']}:{fields['cfa']}:{fields['code']}",
        f"stride:{fields['stride']}",
        f"crop:{fields['cropParity']}",
        f"packedBits:{fields['packedBits']}",
    ]
    questions = ["odd crop retained"] if fields["cropParity"] == "odd" and decision == "decoded_layout" else []
    return _result(decision, reasons, rejected, preserved, questions)


def _minimum_stride(width: int, packed_bits: int) -> int | None:
    if packed_bits == 10:
        if width % 4 != 0:
            return None
        return width * 5 // 4
    if packed_bits == 12:
        if width % 2 != 0:
            return None
        return width * 3 // 2
    return None


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = payload["width"]
    height = payload["height"]
    stride = payload["stride"]
    packed = payload["packedBits"]
    if type(width) is not int or not 1 <= width <= 8192:
        raise ValueError("width must be an int from 1 to 8192")
    if type(height) is not int or not 1 <= height <= 8192:
        raise ValueError("height must be an int from 1 to 8192")
    if type(stride) is not int or not 0 <= stride <= 65536:
        raise ValueError("stride must be an int from 0 to 65536")
    if type(packed) is not int or packed not in _PACKED:
        raise ValueError("packedBits must be 10, 12, or 16")
    cfa = payload["cfa"]
    if cfa not in _CFAS:
        raise ValueError("cfa must be a supported pattern")
    parity = payload["cropParity"]
    if parity not in _PARITY:
        raise ValueError("cropParity must be even or odd")
    code = payload["code"]
    if code not in _CODES:
        raise ValueError("code must be minimum or maximum")
    contiguous = payload["contiguous16"]
    declared = payload["layoutDeclared"]
    if type(contiguous) is not bool or type(declared) is not bool:
        raise ValueError("contiguous16 and layoutDeclared must be bools")
    return {
        "width": width,
        "height": height,
        "stride": stride,
        "packedBits": packed,
        "cfa": cfa,
        "cropParity": parity,
        "code": code,
        "contiguous16": contiguous,
        "layoutDeclared": declared,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-01 must not yield qualified or allowed")
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
