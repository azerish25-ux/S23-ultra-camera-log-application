"""TC-P062-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and
exact unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P062-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."
REPEAT = "Repeat with padded rows, chroma endpoints, and unsupported plane layouts."

_LAYOUTS = ("p010", "i420", "nv12", "planar-rgb")
_ALIGNMENTS = ("msb", "lsb")
_PLANES = ("luma", "chroma")
_CROPS = ("none", "in-bounds", "out-of-bounds")
_PAYLOAD_KEYS = (
    "sampleId",
    "width",
    "height",
    "rowStride",
    "x",
    "y",
    "plane",
    "planeLayout",
    "alignment",
    "crop",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Accept only MSB P010 layouts that unpack to the written code."""
    fields = _payload(payload)
    word = fields["code"] << 6 if fields["alignment"] == "msb" else fields["code"]
    unpacked = word >> 6
    offset = fields["y"] * fields["rowStride"] + fields["x"] * 2
    limit = fields["rowStride"] * fields["height"]
    in_frame = (
        0 <= fields["x"] < fields["width"]
        and 0 <= fields["y"] < fields["height"]
        and offset + 2 <= limit
    )
    preserved = [
        fields["sampleId"],
        f"nominal:{fields['width']}x{fields['height']}",
        f"stride:{fields['rowStride']}",
        f"plane:{fields['plane']}",
        f"layout:{fields['planeLayout']}",
        f"alignment:{fields['alignment']}",
        f"crop:{fields['crop']}",
        f"code:{fields['code']}",
        f"unpacked:{unpacked}",
        f"sample:{fields['x']},{fields['y']}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT]
    if fields["planeLayout"] != "p010":
        rejected.append("unsupported-plane-layout")
        reasons.append(f"plane layout {fields['planeLayout']} is not an explicitly supported P010 layout")
    if fields["alignment"] == "lsb":
        rejected.append("low-six-bit-alignment")
        reasons.append(NEGATIVE)
        reasons.append(f"unpacked {unpacked} does not equal written code {fields['code']}")
    elif unpacked != fields["code"]:
        rejected.append("unpacked-code-mismatch")
        reasons.append("unpacked code does not match the written ten-bit code")
    if fields["rowStride"] < fields["width"] * 2:
        rejected.append("stride-too-small")
        reasons.append("row stride is below the nominal width")
    if fields["crop"] == "out-of-bounds" or not in_frame:
        rejected.append("bounds")
        reasons.append("crop or sample coordinate failed the bounds check")
    if rejected:
        decision = "rejected"
    else:
        decision = "layout_checked"
        reasons.append(f"unpacked code {unpacked} matches {fields['code']} on {fields['planeLayout']}")
        reasons.append("layout check is not ten-bit fidelity qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    for name in ("width", "height", "rowStride", "x", "y", "code"):
        _int(payload[name], name)
    if payload["width"] < 1 or payload["height"] < 1 or payload["rowStride"] < 1:
        raise ValueError("dimensions and stride must be positive")
    if not 0 <= payload["code"] <= 1023:
        raise ValueError("code must be a ten-bit value")
    if payload["plane"] not in _PLANES:
        raise ValueError("plane is unsupported")
    if payload["planeLayout"] not in _LAYOUTS:
        raise ValueError("planeLayout is unsupported")
    if payload["alignment"] not in _ALIGNMENTS:
        raise ValueError("alignment is unsupported")
    if payload["crop"] not in _CROPS:
        raise ValueError("crop is unsupported")
    return payload


def _int(value: object, name: str) -> None:
    if type(value) is not int or isinstance(value, bool):
        raise ValueError(name + " must be an int")


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-04 must not yield qualified or allowed")
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
