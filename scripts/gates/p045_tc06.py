"""TC-P045-06 shading coordinate mismatch.

Intervention: Apply a measured spatial correction using a different crop,
orientation, or CFA origin.
Expected: Detect mismatch or transform the map through a separately verified
coordinate conversion.
Negative: Applying shading in display coordinates without source mapping must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P045-06"
INTERVENTION = (
    "Apply a measured spatial correction using a different crop, orientation, "
    "or CFA origin."
)
EXPECTED = (
    "Detect mismatch or transform the map through a separately verified "
    "coordinate conversion."
)
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_ORIENTATION = ("sensor", "rotated", "display")
_CFA = ("matched", "odd", "shifted")
_PAYLOAD_KEYS = (
    "mapId",
    "sourceCrop",
    "appliedCrop",
    "sourceDimensions",
    "appliedDimensions",
    "orientation",
    "cfaOrigin",
    "verifiedConversion",
    "displayUnmapped",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_CROP = re.compile(r"[1-9][0-9]*x[1-9][0-9]*\+(?:0|[1-9][0-9]*)\+(?:0|[1-9][0-9]*)")
_DIMS = re.compile(r"[1-9][0-9]*x[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Detect a shading-map coordinate mismatch or require a verified conversion."""
    (
        map_id,
        source_crop,
        applied_crop,
        source_dims,
        applied_dims,
        orientation,
        cfa,
        verified,
        display_unmapped,
    ) = _payload(payload)
    preserved = [
        f"map:{map_id}",
        f"source-crop:{source_crop}",
        f"applied-crop:{applied_crop}",
        f"source-dimensions:{source_dims}",
        f"applied-dimensions:{applied_dims}",
        f"orientation:{orientation}",
        f"cfa:{cfa}",
    ]
    rejected: list[str] = []
    if source_crop != applied_crop:
        rejected.append("crop-mismatch")
    if source_dims != applied_dims:
        rejected.append("dimension-mismatch")
    if orientation != "sensor":
        rejected.append("orientation-mismatch")
    if cfa != "matched":
        rejected.append("cfa-origin-mismatch")
    reasons = [EXPECTED, INTERVENTION]
    questions: list[str] = []
    if display_unmapped:
        decision = "rejected"
        rejected.insert(0, "display-coordinates-unmapped")
        reasons.append(NEGATIVE)
        questions.append("display shading was not mapped back to the source")
    elif rejected and not verified:
        decision = "rejected"
        reasons.append("coordinate mismatch detected without a verified conversion")
        questions.append("shading map was not applied across a silent mismatch")
    elif rejected and verified:
        decision = "converted"
        reasons.append("separately verified coordinate conversion was recorded")
        questions.append("conversion does not qualify a physical shading measurement")
        rejected = []
    else:
        decision = "mapped"
        reasons.append("source coordinates match the shading map")
        questions.append("matched coordinates are not a physical S23 measurement")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(
    payload: object,
) -> tuple[str, str, str, str, str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    map_id = payload["mapId"]
    if not isinstance(map_id, str) or _TOKEN.fullmatch(map_id) is None:
        raise ValueError("mapId must be a token")
    source_crop = payload["sourceCrop"]
    applied_crop = payload["appliedCrop"]
    for name, value in (("sourceCrop", source_crop), ("appliedCrop", applied_crop)):
        if not isinstance(value, str) or _CROP.fullmatch(value) is None:
            raise ValueError(f"{name} must be widthxheight+left+top")
    source_dims = payload["sourceDimensions"]
    applied_dims = payload["appliedDimensions"]
    for name, value in (("sourceDimensions", source_dims), ("appliedDimensions", applied_dims)):
        if not isinstance(value, str) or _DIMS.fullmatch(value) is None:
            raise ValueError(f"{name} must be widthxheight")
    orientation = payload["orientation"]
    if orientation not in _ORIENTATION:
        raise ValueError("orientation is unsupported")
    cfa = payload["cfaOrigin"]
    if cfa not in _CFA:
        raise ValueError("cfaOrigin is unsupported")
    verified = payload["verifiedConversion"]
    display_unmapped = payload["displayUnmapped"]
    if type(verified) is not bool or type(display_unmapped) is not bool:
        raise ValueError("verifiedConversion and displayUnmapped must be bools")
    return (
        map_id,
        source_crop,
        applied_crop,
        source_dims,
        applied_dims,
        orientation,
        cfa,
        verified,
        display_unmapped,
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-06 must not yield qualified or allowed")
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
