"""TC-P042-06 shading coordinate mismatch.

A shading map applied with a different crop, orientation, or source size is
a mismatch unless a separately verified conversion is named. Display
coordinates without that mapping are rejected.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-06"
INTERVENTION = "Apply a measured spatial correction using a different crop, orientation, or CFA origin."
EXPECTED = (
    "Detect mismatch or transform the map through a separately verified "
    "coordinate conversion."
)
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_ORIENTATIONS = ("identity", "rotated")
_MAPPINGS = ("verified", "display", "none")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_PAYLOAD_KEYS = (
    "shadeId",
    "sourceWidth",
    "sourceHeight",
    "appliedWidth",
    "appliedHeight",
    "cropX",
    "cropY",
    "orientation",
    "mapping",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "converted", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject unmapped display shading. Keep the source geometry."""
    (
        shade_id,
        source_w,
        source_h,
        applied_w,
        applied_h,
        crop_x,
        crop_y,
        orientation,
        mapping,
    ) = _payload(payload)
    preserved = [
        f"shade:{shade_id}",
        f"source:{source_w}x{source_h}",
        f"applied:{applied_w}x{applied_h}",
        f"crop:{crop_x},{crop_y}",
        f"orientation:{orientation}",
    ]
    mismatch = (
        crop_x != 0
        or crop_y != 0
        or orientation != "identity"
        or applied_w != source_w
        or applied_h != source_h
    )
    if mapping == "display":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "display coordinates were not applied as a source map"],
            ["display-coordinates"],
            preserved,
            ["source geometry was retained"],
        )
    if mapping == "verified":
        return _result(
            "converted",
            [EXPECTED, "coordinate conversion was separately verified"],
            [],
            preserved,
            ["verified conversion is not a physical shading measurement"],
        )
    if mismatch:
        return _result(
            "rejected",
            [EXPECTED, INTERVENTION, "shading coordinates do not match the source"],
            ["coordinate-mismatch"],
            preserved,
            ["the map was not resampled in display space"],
        )
    return _result(
        "withheld",
        ["source coordinates already match", EXPECTED],
        [],
        preserved,
        ["matching coordinates are not a shading measurement"],
    )


def _payload(payload: object) -> tuple[str, int, int, int, int, int, int, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    shade_id = _token(payload["shadeId"], "shadeId")
    source_w = _dim(payload["sourceWidth"], "sourceWidth")
    source_h = _dim(payload["sourceHeight"], "sourceHeight")
    applied_w = _dim(payload["appliedWidth"], "appliedWidth")
    applied_h = _dim(payload["appliedHeight"], "appliedHeight")
    crop_x = _origin(payload["cropX"], "cropX")
    crop_y = _origin(payload["cropY"], "cropY")
    orientation = payload["orientation"]
    if orientation not in _ORIENTATIONS:
        raise ValueError("orientation must be identity or rotated")
    mapping = payload["mapping"]
    if mapping not in _MAPPINGS:
        raise ValueError("mapping must be verified, display, or none")
    return (
        shade_id,
        source_w,
        source_h,
        applied_w,
        applied_h,
        crop_x,
        crop_y,
        orientation,
        mapping,
    )


def _dim(value: object, label: str) -> int:
    if type(value) is not int or value < 1 or value > 8192:
        raise ValueError(f"{label} must be an int from 1 to 8192")
    return value


def _origin(value: object, label: str) -> int:
    if type(value) is not int or value < 0 or value > 8192:
        raise ValueError(f"{label} must be an int from 0 to 8192")
    return value


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-06 must not yield qualified or allowed")
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
