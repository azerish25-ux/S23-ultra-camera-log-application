"""TC-P043-06 shading coordinate mismatch.

Intervention: Apply a measured spatial correction using a different crop,
orientation, or CFA origin.
Expected: Detect mismatch or transform the map through a separately verified
coordinate conversion.
Negative: Applying shading in display coordinates without source mapping must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P043-06"
INTERVENTION = "Apply a measured spatial correction using a different crop, orientation, or CFA origin."
EXPECTED = "Detect mismatch or transform the map through a separately verified coordinate conversion."
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
_ORIENTATIONS = ("native", "rotated")
_PAYLOAD_KEYS = (
    "mapId",
    "sourceCrop",
    "mapCrop",
    "sourceCfa",
    "mapCfa",
    "orientation",
    "sourceWidth",
    "sourceHeight",
    "displayCoordinates",
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
_DECISIONS = ("rejected", "converted", "coordinates_aligned")
_FORBIDDEN = {"qualified", "allowed"}
_CROP = re.compile(r"([1-9][0-9]*)x([1-9][0-9]*)\+(0|[1-9][0-9]*)\+(0|[1-9][0-9]*)")
_POSITIVE = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Detect crop, CFA, and orientation mismatch. Display space without a map fails."""
    parsed = _payload(payload)
    preserved = [
        f"map:{parsed['mapId']}",
        f"sourceCrop:{parsed['sourceCrop']}",
        f"mapCrop:{parsed['mapCrop']}",
        f"sourceCfa:{parsed['sourceCfa']}",
        f"mapCfa:{parsed['mapCfa']}",
        f"orientation:{parsed['orientation']}",
        f"source:{parsed['sourceWidth']}x{parsed['sourceHeight']}",
    ]
    claims = _mismatches(parsed)
    questions = ["display shading without a source map is not a correction"]
    if parsed["displayCoordinates"] and not parsed["verifiedConversion"]:
        decision = "rejected"
        claims.insert(0, "display-without-source-mapping")
        reasons = [NEGATIVE, EXPECTED, "source crops were kept"]
    elif parsed["verifiedConversion"] and (claims or parsed["displayCoordinates"]):
        decision = "converted"
        reasons = [EXPECTED, "separately verified coordinate conversion", "this conversion is not physical qualification"]
        questions.append("verified conversion is not a measured shading map")
        claims = []
    elif claims:
        decision = "rejected"
        reasons = [EXPECTED, "coordinate mismatch detected", "source crops were kept"]
    else:
        decision = "coordinates_aligned"
        reasons = [
            "crop, CFA, and orientation match the source",
            "alignment is not a physical shading measurement",
        ]
        questions.append("aligned coordinates are not lens-shading qualification")
    return _result(decision, reasons, claims, preserved, questions)


def _mismatches(parsed: dict) -> list[str]:
    source = parsed["sourceBox"]
    mapped = parsed["mapBox"]
    width = int(parsed["sourceWidth"])
    height = int(parsed["sourceHeight"])
    claims: list[str] = []
    if (source[2], source[3]) != (mapped[2], mapped[3]):
        claims.append("crop-mismatch")
    if (source[0], source[1]) != (mapped[0], mapped[1]):
        claims.append("crop-size-mismatch")
    if parsed["sourceCfa"] != parsed["mapCfa"]:
        claims.append("cfa-mismatch")
    if parsed["orientation"] == "rotated":
        claims.append("rotated-output")
    if source[2] % 2 or source[3] % 2 or mapped[2] % 2 or mapped[3] % 2:
        claims.append("odd-crop-origin")
    if source[0] + source[2] > width or source[1] + source[3] > height:
        claims.append("dimension-mismatch")
    if mapped[0] + mapped[2] > width or mapped[1] + mapped[3] > height:
        claims.append("dimension-mismatch")
    return list(dict.fromkeys(claims))


def _crop(value: object, label: str) -> tuple[str, tuple[int, int, int, int]]:
    if not isinstance(value, str) or _CROP.fullmatch(value) is None:
        raise ValueError(f"{label} must be widthxheight+left+top")
    match = _CROP.fullmatch(value)
    box = tuple(int(part) for part in match.groups())
    return value, box


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    map_id = payload["mapId"]
    if not isinstance(map_id, str) or not map_id or map_id != map_id.strip():
        raise ValueError("mapId must be a non-empty string")
    source_crop, source_box = _crop(payload["sourceCrop"], "sourceCrop")
    map_crop, map_box = _crop(payload["mapCrop"], "mapCrop")
    for label in ("sourceCfa", "mapCfa"):
        if payload[label] not in _CFA:
            raise ValueError(f"{label} must be a supported Bayer phase")
    if payload["orientation"] not in _ORIENTATIONS:
        raise ValueError("orientation must be native or rotated")
    for label in ("sourceWidth", "sourceHeight"):
        if not isinstance(payload[label], str) or _POSITIVE.fullmatch(payload[label]) is None:
            raise ValueError(f"{label} must be a canonical positive integer string")
    for label in ("displayCoordinates", "verifiedConversion"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    return {
        "mapId": map_id,
        "sourceCrop": source_crop,
        "mapCrop": map_crop,
        "sourceBox": source_box,
        "mapBox": map_box,
        "sourceCfa": payload["sourceCfa"],
        "mapCfa": payload["mapCfa"],
        "orientation": payload["orientation"],
        "sourceWidth": payload["sourceWidth"],
        "sourceHeight": payload["sourceHeight"],
        "displayCoordinates": payload["displayCoordinates"],
        "verifiedConversion": payload["verifiedConversion"],
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("coordinate decision cannot be qualified or allowed")
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
