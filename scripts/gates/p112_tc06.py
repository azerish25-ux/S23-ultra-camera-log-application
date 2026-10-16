"""TC-P112-06 Subject identity crossing.

Host fixture. Focus follows the selected identity and holds when that target
is lost. Choosing the nearest face independently is rejected. Focus-distance
variance is reported. This is not an applyNegative stub.
"""

from __future__ import annotations

import math
import statistics

CASE_ID = "TC-P112-06"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
NEGATIVE_TOKEN = "nearest-face-independently-every-frame"
JUMP_TOKEN = "unexplained-focus-jump"
HOLD = "hold"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "frames"}
FRAME_KEYS = {"selected_id", "selected_visible", "focus_id", "nearest_face_id", "focus_distance"}
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
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number) and number > 0.0, label + " must be a finite number > 0")
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    _require(type(value) is bool, label + " must be a bool")
    return value


def _unique(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _frames(value: object) -> list[dict]:
    _require(isinstance(value, list) and len(value) >= 2, "frames must contain at least 2 objects")
    parsed: list[dict] = []
    for index, frame in enumerate(value):
        _require(isinstance(frame, dict), f"frame {index} must be an object")
        missing = FRAME_KEYS - set(frame)
        extra = set(frame) - FRAME_KEYS
        _require(not missing, f"frame {index} missing fields: " + ", ".join(sorted(missing)))
        _require(not extra, f"frame {index} has unexpected fields: " + ", ".join(sorted(extra)))
        parsed.append({
            "selected_id": _text(frame["selected_id"], f"frame {index} selected_id"),
            "selected_visible": _bool(frame["selected_visible"], f"frame {index} selected_visible"),
            "focus_id": _text(frame["focus_id"], f"frame {index} focus_id"),
            "nearest_face_id": _text(frame["nearest_face_id"], f"frame {index} nearest_face_id"),
            "focus_distance": _number(frame["focus_distance"], f"frame {index} focus_distance"),
        })
    selected = {frame["selected_id"] for frame in parsed}
    _require(len(selected) == 1, "selected_id must stay the documented target")
    _require(HOLD not in selected, "selected_id cannot be the hold token")
    return parsed


def evaluate(payload: dict) -> dict:
    """Keep the selected identity. Do not retarget the nearest face, and do not hide breathing."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frames = _frames(payload["frames"])
    selected = frames[0]["selected_id"]
    failures: list[str] = []
    for frame in frames:
        nearest = frame["nearest_face_id"]
        focus = frame["focus_id"]
        if frame["selected_visible"]:
            if focus == nearest and nearest != selected:
                failures.append(NEGATIVE_TOKEN)
            elif focus != selected:
                failures.append(JUMP_TOKEN)
        elif focus == nearest and nearest != selected:
            failures.append(NEGATIVE_TOKEN)
        elif focus != HOLD:
            failures.append(JUMP_TOKEN)
    rejected = _unique(failures)
    distances = [frame["focus_distance"] for frame in frames]
    variance = float(statistics.variance(distances))
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"focus_distance_variance={variance!r}",
        "breathing reported; focus_distance variance is not hidden",
    ]
    if rejected:
        decision = "rejected"
        if NEGATIVE_TOKEN in rejected:
            reasons.append(NEGATIVE)
        if JUMP_TOKEN in rejected:
            reasons.append("focus left the selected identity without the hold policy")
    else:
        decision = "recorded"
        reasons.append("focus followed the selected identity and the hold policy on target loss")
    preserved = [evidence, f"selected_id={selected}", f"focus_distance_variance={variance!r}"]
    preserved.extend(
        f"frame:{index}:visible={str(frame['selected_visible']).lower()}:"
        f"focus={frame['focus_id']}:nearest={frame['nearest_face_id']}:"
        f"distance={frame['focus_distance']}"
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
    _require(decision in {"recorded", "rejected"} and decision not in {"qualified", "allowed"},
             "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    _require(any(item.startswith("focus_distance_variance=") for item in result["preservedResults"]),
             "focus distance variance hidden")
    return result
