"""TC-P112-01 History without reprojection.

Host fixture. History must sit on the object's current pixel. A stationary-pixel
average that leaves depth trails is rejected. This is not an applyNegative stub.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P112-01"
PHASE = "P112"
WORKSTREAM = 14
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average-depth-trail"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "frames"}
FRAME_KEYS = {"object_x", "history_x", "depth"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_ALIGN = 1e-6


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number), label + " must be finite")
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _frames(value: object) -> list[dict[str, float]]:
    _require(isinstance(value, list) and len(value) >= 2, "frames must contain at least 2 objects")
    parsed: list[dict[str, float]] = []
    for index, frame in enumerate(value):
        _require(isinstance(frame, dict), f"frame {index} must be an object")
        missing = FRAME_KEYS - set(frame)
        extra = set(frame) - FRAME_KEYS
        _require(not missing, f"frame {index} missing fields: " + ", ".join(sorted(missing)))
        _require(not extra, f"frame {index} has unexpected fields: " + ", ".join(sorted(extra)))
        parsed.append({
            "object_x": _number(frame["object_x"], f"frame {index} object_x"),
            "history_x": _number(frame["history_x"], f"frame {index} history_x"),
            "depth": _number(frame["depth"], f"frame {index} depth"),
        })
    return parsed


def evaluate(payload: dict) -> dict:
    """Reject history that stays on the original pixel after the object moves."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frames = _frames(payload["frames"])
    trails = [
        index
        for index, frame in enumerate(frames)
        if abs(frame["history_x"] - frame["object_x"]) > _ALIGN
    ]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if trails:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("unaligned history at frames " + ",".join(str(index) for index in trails))
    else:
        decision = "recorded"
        reasons.append("history warped onto the object pixel before temporal blending")
    preserved = [evidence]
    preserved.extend(
        f"frame:{index}:object_x={frame['object_x']}:history_x={frame['history_x']}:depth={frame['depth']}"
        for index, frame in enumerate(frames)
    )
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
