"""TC-P063-04 P010 plane geometry fault.

Only an explicit semi-planar MSB layout with a bounds check and matching
unpacked code is handled. Low-six-bit alignment fails. Nominal dimensions
stay in the inventory. This host case does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P063-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."
REPEAT = "Repeat with padded rows, chroma endpoints, and unsupported plane layouts."

_CROPS = ("none", "chroma-endpoint")
_LAYOUTS = ("semi-planar", "planar", "interleaved")
_ALIGNMENTS = ("msb", "lsb")
_PAYLOAD_KEYS = (
    "frameId",
    "width",
    "height",
    "rowStride",
    "crop",
    "planeLayout",
    "alignment",
    "unpackedCode",
    "expectedCode",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_CODE = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Accept only a checked MSB semi-planar layout; reject low-bit alignment."""
    (
        frame_id,
        width,
        height,
        stride,
        crop,
        layout,
        alignment,
        unpacked,
        expected,
        bounds_ok,
    ) = _payload(payload)
    preserved = [
        frame_id,
        f"nominal:{width}x{height}",
        f"row-stride:{stride}",
        f"crop:{crop}",
        f"layout:{layout}",
        f"alignment:{alignment}",
        f"unpacked:{unpacked}",
        f"expected:{expected}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    if alignment == "lsb":
        rejected.append("low-six-bit-alignment")
        reasons.append(NEGATIVE)
    if layout != "semi-planar":
        rejected.append("unsupported-plane")
        reasons.append(f"plane layout {layout} is not an explicitly supported layout")
    if not bounds_ok:
        rejected.append("bounds-failed")
        reasons.append("bounds check failed")
    minimum = width * 2
    if stride < minimum:
        rejected.append("stride-short")
        reasons.append(f"row stride {stride} is below the {minimum}-byte P010 minimum")
    elif stride > minimum:
        reasons.append(f"padded row stride {stride} was checked against nominal {width}x{height}")
    if unpacked != expected:
        rejected.append("unpacked-code-mismatch")
        reasons.append(f"unpacked code {unpacked} does not match expected {expected}")
    if rejected:
        decision = "rejected"
        questions.append("nominal dimensions were kept")
    else:
        decision = "layout_checked"
        reasons.append("supported layout passed bounds checks and unpacked-code verification")
        questions.append("layout_checked is not ten-bit fidelity and not qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frame_id = payload["frameId"]
    if not isinstance(frame_id, str) or _TOKEN.fullmatch(frame_id) is None:
        raise ValueError("frameId must be a token")
    width = payload["width"]
    height = payload["height"]
    stride = payload["rowStride"]
    for name, value in (("width", width), ("height", height), ("rowStride", stride)):
        if type(value) is not int or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive int")
    crop = payload["crop"]
    if crop not in _CROPS:
        raise ValueError("crop is unsupported")
    layout = payload["planeLayout"]
    if layout not in _LAYOUTS:
        raise ValueError("planeLayout is unsupported")
    alignment = payload["alignment"]
    if alignment not in _ALIGNMENTS:
        raise ValueError("alignment must be msb or lsb")
    unpacked = payload["unpackedCode"]
    expected = payload["expectedCode"]
    for name, code in (("unpackedCode", unpacked), ("expectedCode", expected)):
        if not isinstance(code, str) or _CODE.fullmatch(code) is None or int(code) > 1023:
            raise ValueError(f"{name} must be a canonical code from 0 through 1023")
    bounds_ok = payload["boundsOk"]
    if type(bounds_ok) is not bool:
        raise ValueError("boundsOk must be a bool")
    return frame_id, width, height, stride, crop, layout, alignment, unpacked, expected, bounds_ok


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-04 must not yield qualified or allowed")
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
