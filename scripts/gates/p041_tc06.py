"""TC-P041-06 shading coordinate mismatch.

A spatial correction with a different crop, orientation, or CFA origin is
detected, or it is transformed through a separately verified conversion.
Display coordinates without a source map fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P041-06"
INTERVENTION = "Apply a measured spatial correction using a different crop, orientation, or CFA origin."
EXPECTED = "Detect mismatch or transform the map through a separately verified coordinate conversion."
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_ORIENTATIONS = ("source", "rotated", "display")
_CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
_CONVERSIONS = ("none", "verified")
_CROP = re.compile(r"^([1-9][0-9]*)x([1-9][0-9]*)\+(0|[1-9][0-9]*)\+(0|[1-9][0-9]*)$")
_PAYLOAD_KEYS = (
    "sourceCrop",
    "mapCrop",
    "sourceCfa",
    "mapCfa",
    "orientation",
    "conversion",
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
_DECISIONS = {"rejected", "coordinate_converted", "coordinates_matched"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Detect a shading-map mismatch or require a verified conversion."""
    fields = _payload(payload)
    preserved = [
        f"sourceCrop:{fields['sourceCrop']}",
        f"mapCrop:{fields['mapCrop']}",
        f"sourceCfa:{fields['sourceCfa']}",
        f"mapCfa:{fields['mapCfa']}",
        f"orientation:{fields['orientation']}",
        f"source:{fields['sourceWidth']}x{fields['sourceHeight']}",
        f"map:{fields['mapWidth']}x{fields['mapHeight']}",
    ]
    mismatch = _mismatch_claims(fields)
    if fields["orientation"] == "display" and fields["conversion"] == "none":
        claims = ["display-coordinates-without-source-map", *mismatch]
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "display coordinates were not applied without a source map"],
            claims,
            preserved,
            ["source mapping was not invented"],
        )
    if mismatch and fields["conversion"] == "none":
        return _result(
            "rejected",
            [EXPECTED, "coordinate mismatch detected", *mismatch],
            ["coordinate-mismatch", *mismatch],
            preserved,
            ["shading map was not applied"],
        )
    if mismatch and fields["conversion"] == "verified":
        return _result(
            "coordinate_converted",
            [EXPECTED, "map transformed through a separately verified coordinate conversion"],
            [],
            preserved,
            ["conversion is not a measured shading certificate"],
        )
    return _result(
        "coordinates_matched",
        [EXPECTED, "crop, orientation, CFA origin, and dimensions matched"],
        [],
        preserved,
        ["matched coordinates are not a measured shading certificate"],
    )


def _odd(crop: str) -> bool:
    match = _CROP.fullmatch(crop)
    if match is None:
        return False
    left = int(match.group(3))
    top = int(match.group(4))
    return left % 2 == 1 or top % 2 == 1


def _mismatch_claims(fields: dict) -> list[str]:
    claims: list[str] = []
    if fields["sourceCrop"] != fields["mapCrop"]:
        claims.append("crop-mismatch")
    if _odd(fields["sourceCrop"]) or _odd(fields["mapCrop"]):
        claims.append("odd-crop-origin")
    if fields["orientation"] == "rotated":
        claims.append("rotated-output")
    if (fields["sourceWidth"], fields["sourceHeight"]) != (fields["mapWidth"], fields["mapHeight"]):
        claims.append("dimension-change")
    if fields["sourceCfa"] != fields["mapCfa"]:
        claims.append("cfa-origin-mismatch")
    return claims


def _crop(value: object, label: str) -> str:
    if not isinstance(value, str) or _CROP.fullmatch(value) is None:
        raise ValueError(label + " must look like 4000x3000+0+0")
    return value


def _size(value: object, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 8192:
        raise ValueError(label + " must be an int from 1 to 8192")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    orientation = payload["orientation"]
    conversion = payload["conversion"]
    source_cfa = payload["sourceCfa"]
    map_cfa = payload["mapCfa"]
    if orientation not in _ORIENTATIONS:
        raise ValueError("orientation must be source, rotated, or display")
    if conversion not in _CONVERSIONS:
        raise ValueError("conversion must be none or verified")
    if source_cfa not in _CFAS or map_cfa not in _CFAS:
        raise ValueError("CFA origin must be a Bayer phase")
    return {
        "sourceCrop": _crop(payload["sourceCrop"], "sourceCrop"),
        "mapCrop": _crop(payload["mapCrop"], "mapCrop"),
        "sourceCfa": source_cfa,
        "mapCfa": map_cfa,
        "orientation": orientation,
        "conversion": conversion,
        "sourceWidth": _size(payload["sourceWidth"], "sourceWidth"),
        "sourceHeight": _size(payload["sourceHeight"], "sourceHeight"),
        "mapWidth": _size(payload["mapWidth"], "mapWidth"),
        "mapHeight": _size(payload["mapHeight"], "mapHeight"),
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-06 must not yield qualified or allowed")
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
