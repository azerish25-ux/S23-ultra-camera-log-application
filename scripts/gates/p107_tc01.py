"""TC-P107-01 History without reprojection.

Host reference. Unaligned history and a stationary-pixel average are rejected.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P107-01"
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average"
PAYLOAD_KEYS = ("evidenceId", "repeat", "dx", "dy", "history_warped", "stationary_pixel_average")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    value_f = float(value)
    _require(math.isfinite(value_f), f"{label} must be finite")
    return value_f


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(), "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["history_warped"]) is bool, "history_warped must be a bool")
    _require(type(payload["stationary_pixel_average"]) is bool, "stationary_pixel_average must be a bool")
    dx = _number(payload["dx"], "dx")
    dy = _number(payload["dy"], "dy")
    motion = math.hypot(dx, dy)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, f"motion_px={format(motion, '.12g')}"]
    rejected: list[str] = []
    if payload["stationary_pixel_average"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("depth trail length equals the unwarped motion")
    elif motion > 0.0 and not payload["history_warped"]:
        rejected.append("unaligned-history")
        reasons.append("previous depth stayed in its original pixel coordinates")
    elif motion > 0.0:
        reasons.append("history warped before temporal blending")
    else:
        reasons.append("no object motion; original coordinates still match")
    decision = "rejected" if rejected else "recorded"
    questions = ["physical S23 was not run", REPEAT]
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"motion_px={format(motion, '.12g')}"],
        "openQuestions": questions,
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
