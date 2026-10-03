"""TC-P044-06 shading coordinate mismatch.

Intervention: Apply a measured spatial correction using a different crop,
orientation, or CFA origin.
Expected: Detect mismatch or transform the map through a separately verified
coordinate conversion.
Negative: Applying shading in display coordinates without source mapping must
fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P044-06"
INTERVENTION = (
    "Apply a measured spatial correction using a different crop, orientation, or CFA origin."
)
EXPECTED = (
    "Detect mismatch or transform the map through a separately verified coordinate conversion."
)
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_ORIENTATIONS = ("native", "rotated")
_PAYLOAD_KEYS = (
    "sourceCrop",
    "appliedCrop",
    "orientation",
    "cfaOrigin",
    "displayCoordinates",
    "verifiedConversion",
    "sourceWidth",
    "sourceHeight",
    "mapWidth",
    "mapHeight",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "converted", "aligned")
_FORBIDDEN = {"qualified", "allowed"}
_PAIR = re.compile(r"^(?:0|[1-9][0-9]*),(?:0|[1-9][0-9]*)$")


def evaluate(payload: dict) -> dict:
    """Detect a shading-coordinate mismatch unless conversion was verified."""
    (
        source_crop,
        applied_crop,
        orientation,
        cfa,
        display,
        verified,
        source_w,
        source_h,
        map_w,
        map_h,
    ) = _payload(payload)
    preserved = [
        f"source-crop:{source_crop}",
        f"applied-crop:{applied_crop}",
        f"orientation:{orientation}",
        f"cfa:{cfa}",
        f"source-size:{source_w}x{source_h}",
        f"map-size:{map_w}x{map_h}",
        f"display:{str(display).lower()}",
    ]
    mismatch = (
        source_crop != applied_crop
        or orientation != "native"
        or cfa != "0,0"
        or map_w != source_w
        or map_h != source_h
    )
    reasons = [EXPECTED]
    if display and not verified:
        decision = "rejected"
        rejected = ["display-coordinates-unmapped"]
        reasons.append(NEGATIVE)
        questions = ["display coordinates were applied without source mapping"]
    elif mismatch and verified:
        decision = "converted"
        rejected = []
        reasons.append("map transformed through a separately verified coordinate conversion")
        questions = ["coordinate conversion was separately verified"]
    elif mismatch:
        decision = "rejected"
        rejected = ["coordinate-mismatch"]
        reasons.append("shading coordinate mismatch detected")
        questions = ["source mapping was not verified"]
    else:
        decision = "aligned"
        rejected = []
        reasons.append("source coordinates match the shading map")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _pair(value: object, label: str) -> str:
    if not isinstance(value, str) or _PAIR.fullmatch(value) is None:
        raise ValueError(label + " must look like x,y")
    return value


def _size(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source_crop = _pair(payload["sourceCrop"], "sourceCrop")
    applied_crop = _pair(payload["appliedCrop"], "appliedCrop")
    orientation = payload["orientation"]
    if orientation not in _ORIENTATIONS:
        raise ValueError("orientation must be native or rotated")
    cfa = _pair(payload["cfaOrigin"], "cfaOrigin")
    display = payload["displayCoordinates"]
    verified = payload["verifiedConversion"]
    if type(display) is not bool or type(verified) is not bool:
        raise ValueError("displayCoordinates and verifiedConversion must be bools")
    return (
        source_crop,
        applied_crop,
        orientation,
        cfa,
        display,
        verified,
        _size(payload["sourceWidth"], "sourceWidth"),
        _size(payload["sourceHeight"], "sourceHeight"),
        _size(payload["mapWidth"], "mapWidth"),
        _size(payload["mapHeight"], "mapHeight"),
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("shading decision cannot be qualified or allowed")
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
