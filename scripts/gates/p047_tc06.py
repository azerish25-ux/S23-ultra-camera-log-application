"""TC-P047-06 shading coordinate mismatch.

Intervention: Apply a measured spatial correction using a different crop,
orientation, or CFA origin.
Expected: Detect mismatch or transform the map through a separately verified
coordinate conversion.
Negative: Applying shading in display coordinates without source mapping must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P047-06"
INTERVENTION = (
    "Apply a measured spatial correction using a different crop, orientation, "
    "or CFA origin."
)
EXPECTED = (
    "Detect mismatch or transform the map through a separately verified "
    "coordinate conversion."
)
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
_ORIENTATIONS = (0, 90, 180, 270)
_CROP = re.compile(r"[1-9][0-9]*x[1-9][0-9]*\+(?:0|[1-9][0-9]*)\+(?:0|[1-9][0-9]*)")
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "mapId",
    "sourceCrop",
    "mapCrop",
    "sourceOrientation",
    "mapOrientation",
    "sourceCfa",
    "mapCfa",
    "sourceWidth",
    "sourceHeight",
    "mapWidth",
    "mapHeight",
    "displayWithoutMapping",
    "verifiedConversion",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "converted", "mapped")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Detect shading coordinate mismatch. Display coordinates without a map fail."""
    fields = _payload(payload)
    preserved = [
        "map:" + fields["mapId"],
        "sourceCrop:" + fields["sourceCrop"],
        "mapCrop:" + fields["mapCrop"],
        "sourceOrientation:" + str(fields["sourceOrientation"]),
        "mapOrientation:" + str(fields["mapOrientation"]),
        "sourceCfa:" + fields["sourceCfa"],
        "mapCfa:" + fields["mapCfa"],
        f"sourceSize:{fields['sourceWidth']}x{fields['sourceHeight']}",
        f"mapSize:{fields['mapWidth']}x{fields['mapHeight']}",
    ]
    odd = _odd(fields["sourceCrop"]) or _odd(fields["mapCrop"])
    mismatched = _mismatched(fields) or odd
    if fields["displayWithoutMapping"]:
        return _result(
            "rejected",
            [
                NEGATIVE,
                EXPECTED,
                "display coordinates were not applied without source mapping",
            ],
            ["display-coordinates-without-mapping"],
            preserved,
            ["source mapping was not invented"],
        )
    if mismatched and not fields["verifiedConversion"]:
        reasons = [EXPECTED, "coordinate mismatch detected"]
        if odd:
            reasons.append("odd crop origin detected")
        return _result(
            "rejected",
            reasons,
            ["coordinate-mismatch"],
            preserved,
            ["shading map not applied in mismatched coordinates"],
        )
    if mismatched and fields["verifiedConversion"]:
        return _result(
            "converted",
            [
                EXPECTED,
                "map transformed through a separately verified coordinate conversion",
            ],
            [],
            preserved,
            ["verified conversion is not physical shading qualification"],
        )
    return _result(
        "mapped",
        [
            EXPECTED,
            "source and map coordinates agree",
            "agreement is not display-space shading",
        ],
        [],
        preserved,
        ["mapped shading is not physical S23 qualification"],
    )


def _mismatched(fields: dict) -> bool:
    pairs = (
        ("sourceCrop", "mapCrop"),
        ("sourceOrientation", "mapOrientation"),
        ("sourceCfa", "mapCfa"),
        ("sourceWidth", "mapWidth"),
        ("sourceHeight", "mapHeight"),
    )
    return any(fields[left] != fields[right] for left, right in pairs)


def _odd(crop: str) -> bool:
    _, left, top = crop.split("+")
    return int(left) % 2 == 1 or int(top) % 2 == 1


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    parsed: dict = {}
    map_id = payload["mapId"]
    if not isinstance(map_id, str) or not map_id or any(char not in _TOKEN for char in map_id):
        raise ValueError("mapId must be a canonical token")
    parsed["mapId"] = map_id
    for key in ("sourceCrop", "mapCrop"):
        crop = payload[key]
        if not isinstance(crop, str) or _CROP.fullmatch(crop) is None:
            raise ValueError(key + " must be widthxheight+left+top")
        parsed[key] = crop
    for key in ("sourceOrientation", "mapOrientation"):
        value = payload[key]
        if value not in _ORIENTATIONS or type(value) is not int:
            raise ValueError(key + " must be 0, 90, 180, or 270")
        parsed[key] = value
    for key in ("sourceCfa", "mapCfa"):
        value = payload[key]
        if value not in _CFA:
            raise ValueError(key + " must be a Bayer phase")
        parsed[key] = value
    for key in ("sourceWidth", "sourceHeight", "mapWidth", "mapHeight"):
        value = payload[key]
        if type(value) is not int or value < 2 or value > 20000:
            raise ValueError(key + " must be a plausible dimension")
        parsed[key] = value
    for key in ("displayWithoutMapping", "verifiedConversion"):
        value = payload[key]
        if type(value) is not bool:
            raise ValueError(key + " must be a bool")
        parsed[key] = value
    return parsed


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("shading decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
