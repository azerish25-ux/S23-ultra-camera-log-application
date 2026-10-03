"""TC-P046-06 shading coordinate mismatch.

Intervention: Apply a measured spatial correction using a different crop,
orientation, or CFA origin.
Expected: Detect mismatch or transform the map through a separately verified
coordinate conversion.
Negative: Applying shading in display coordinates without source mapping must
fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-06"
INTERVENTION = (
    "Apply a measured spatial correction using a different crop, orientation, or CFA origin."
)
EXPECTED = (
    "Detect mismatch or transform the map through a separately verified coordinate conversion."
)
NEGATIVE = "Applying shading in display coordinates without source mapping must fail."

_SPACES = ("source", "display")
_ORIENTATIONS = ("native", "rotated-90", "rotated-180", "rotated-270")
_PAYLOAD_KEYS = (
    "mapId",
    "correctionSpace",
    "cropX",
    "cropY",
    "orientation",
    "sourceWidth",
    "sourceHeight",
    "mapWidth",
    "mapHeight",
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
_DECISIONS = ("rejected", "mismatch", "converted", "source_aligned")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Detect a shading-coordinate mismatch unless a verified conversion exists."""
    (
        map_id,
        space,
        crop_x,
        crop_y,
        orientation,
        source_w,
        source_h,
        map_w,
        map_h,
        verified,
    ) = _payload(payload)
    preserved = [
        f"map:{map_id}",
        f"space:{space}",
        f"crop:{crop_x},{crop_y}",
        f"orientation:{orientation}",
        f"source:{source_w}x{source_h}",
        f"map-size:{map_w}x{map_h}",
        f"verified-conversion:{str(verified).lower()}",
    ]
    mismatch: list[str] = []
    if crop_x != 0 or crop_y != 0:
        if crop_x % 2 != 0 or crop_y % 2 != 0:
            mismatch.append("odd-crop-origin")
        else:
            mismatch.append("crop-origin")
    if orientation != "native":
        mismatch.append("rotated-output")
    if (source_w, source_h) != (map_w, map_h):
        mismatch.append("source-dimension-mismatch")
    reasons = [EXPECTED]
    if space == "display" and not verified:
        decision = "rejected"
        rejected = ["display-without-source-mapping", *mismatch]
        reasons.append(NEGATIVE)
        questions = ["display coordinates lack a source mapping"]
    elif mismatch and not verified:
        decision = "mismatch"
        rejected = mismatch
        reasons.append("shading coordinates do not match the source")
        questions = list(mismatch)
    elif space == "display" or mismatch:
        decision = "converted"
        rejected = []
        reasons.append("map transformed through a separately verified coordinate conversion")
        questions = ["coordinate conversion was verified separately"]
    else:
        decision = "source_aligned"
        rejected = []
        reasons.append("shading map already uses source coordinates")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, int, int, str, int, int, int, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    map_id = payload["mapId"]
    if not isinstance(map_id, str) or _TOKEN.fullmatch(map_id) is None:
        raise ValueError("mapId must be a token")
    space = payload["correctionSpace"]
    if space not in _SPACES:
        raise ValueError("correctionSpace must be source or display")
    crop_x = payload["cropX"]
    crop_y = payload["cropY"]
    if type(crop_x) is not int or type(crop_y) is not int:
        raise ValueError("crop coordinates must be ints")
    orientation = payload["orientation"]
    if orientation not in _ORIENTATIONS:
        raise ValueError("orientation is unknown")
    sizes = (
        payload["sourceWidth"],
        payload["sourceHeight"],
        payload["mapWidth"],
        payload["mapHeight"],
    )
    if any(type(item) is not int or item <= 0 for item in sizes):
        raise ValueError("dimensions must be positive ints")
    verified = payload["verifiedConversion"]
    if type(verified) is not bool:
        raise ValueError("verifiedConversion must be a bool")
    return (
        map_id,
        space,
        crop_x,
        crop_y,
        orientation,
        sizes[0],
        sizes[1],
        sizes[2],
        sizes[3],
        verified,
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
