"""TC-P061-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and exact
unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P061-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = (
    "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
)
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."
REPEAT = "Repeat with padded rows, chroma endpoints, and unsupported plane layouts."

_LAYOUTS = ("P010", "padded-P010", "NV12", "unsupported")
_CROPS = ("none", "supported-inset", "unsupported")
_ALIGNMENTS = ("msb", "low-six")
_PLANES = ("luma", "chroma")
_SUPPORTED = {"P010", "padded-P010"}
_PAYLOAD_KEYS = (
    "nominalWidth",
    "nominalHeight",
    "strideBytes",
    "crop",
    "layout",
    "alignment",
    "unpackedCode",
    "storedWord",
    "plane",
    "chromaEndpoint",
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
    """Accept only MSB-aligned P010 layouts whose unpacked code matches the word."""
    (
        width,
        height,
        stride,
        crop,
        layout,
        alignment,
        code,
        stored,
        plane,
        endpoint,
    ) = _payload(payload)
    preserved = [
        f"nominal:{width}x{height}",
        f"stride:{stride}",
        f"crop:{crop}",
        f"layout:{layout}",
        f"alignment:{alignment}",
        f"code:{code}",
        f"stored:{stored}",
        f"plane:{plane}",
        f"chroma-endpoint:{str(endpoint).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions = ["nominal dimensions were kept even when the layout was rejected"]
    rejected: list[str] = []
    if layout not in _SUPPORTED:
        rejected.append("unsupported-layout")
        reasons.append("plane layout is not an explicitly supported P010 arrangement")
    if alignment != "msb":
        rejected.append("low-six-aligned")
        reasons.append(NEGATIVE)
    if crop == "unsupported":
        rejected.append("unsupported-crop")
        reasons.append("crop is not an explicitly supported inset")
    minimum = width * 2
    stride_ok = stride >= minimum and stride % 2 == 0
    if layout == "P010":
        stride_ok = stride == minimum
    elif layout == "padded-P010":
        stride_ok = stride > minimum and stride % 2 == 0
    if not stride_ok:
        rejected.append("stride-bounds")
        reasons.append("row stride failed the bounds check")
    expected_word = (code << 6) if alignment == "msb" else code
    if stored != expected_word:
        rejected.append("unpacked-code-mismatch")
        reasons.append("unpacked code does not match the stored word")
    if rejected:
        decision = "rejected"
    else:
        decision = "layout_checked"
        reasons.append("supported layout passed bounds and exact unpacked-code checks")
        questions.append("layout_checked is not ten-bit fidelity and not physical qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = _positive(payload["nominalWidth"], "nominalWidth")
    height = _positive(payload["nominalHeight"], "nominalHeight")
    stride = _positive(payload["strideBytes"], "strideBytes")
    crop = payload["crop"]
    if crop not in _CROPS:
        raise ValueError("crop is unsupported")
    layout = payload["layout"]
    if layout not in _LAYOUTS:
        raise ValueError("layout is unsupported")
    alignment = payload["alignment"]
    if alignment not in _ALIGNMENTS:
        raise ValueError("alignment is unsupported")
    code = payload["unpackedCode"]
    if type(code) is not int or isinstance(code, bool) or not 0 <= code <= 1023:
        raise ValueError("unpackedCode must be an int from 0 through 1023")
    stored = payload["storedWord"]
    if type(stored) is not int or isinstance(stored, bool) or not 0 <= stored <= 65535:
        raise ValueError("storedWord must be an int from 0 through 65535")
    plane = payload["plane"]
    if plane not in _PLANES:
        raise ValueError("plane is unsupported")
    endpoint = payload["chromaEndpoint"]
    if type(endpoint) is not bool:
        raise ValueError("chromaEndpoint must be a bool")
    if endpoint and plane != "chroma":
        raise ValueError("chromaEndpoint requires the chroma plane")
    return width, height, stride, crop, layout, alignment, code, stored, plane, endpoint


def _positive(value: object, label: str) -> int:
    if type(value) is not int or isinstance(value, bool) or value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-04 must not yield qualified or allowed")
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
