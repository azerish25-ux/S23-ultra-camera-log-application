"""TC-P112-04 Scene-cut contamination.

Host fixture. A strictly increasing timestamp does not keep temporal state
across a real scene cut. This is not an applyNegative stub.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P112-04"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "continuous-timestamps-preserved-temporal-state-across-cut"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "frames"}
FRAME_KEYS = {"timestamp_s", "scene_id", "carried_history_scene"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_RESET = "reset"


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
            "timestamp_s": _number(frame["timestamp_s"], f"frame {index} timestamp_s"),
            "scene_id": _text(frame["scene_id"], f"frame {index} scene_id"),
            "carried_history_scene": _text(frame["carried_history_scene"], f"frame {index} carried_history_scene"),
        })
    for index in range(1, len(parsed)):
        _require(parsed[index]["timestamp_s"] > parsed[index - 1]["timestamp_s"],
                 "timestamps must be strictly increasing")
    return parsed


def evaluate(payload: dict) -> dict:
    """Reject history that survives a scene cut only because the clock kept running."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frames = _frames(payload["frames"])
    leaks: list[int] = []
    for index in range(1, len(frames)):
        previous = frames[index - 1]["scene_id"]
        current = frames[index]["scene_id"]
        carried = frames[index]["carried_history_scene"]
        cut = current != previous
        if cut and carried == previous:
            leaks.append(index)
        elif carried not in {current, _RESET}:
            leaks.append(index)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if leaks:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("temporal state crossed a cut at frames " + ",".join(str(index) for index in leaks))
    else:
        decision = "recorded"
        reasons.append("history was reset at the cut; continuous timestamps were not treated as the same shot")
    preserved = [evidence]
    preserved.extend(
        f"frame:{index}:t={frame['timestamp_s']}:scene={frame['scene_id']}:history={frame['carried_history_scene']}"
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
    return result
