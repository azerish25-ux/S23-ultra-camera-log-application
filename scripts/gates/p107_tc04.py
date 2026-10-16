"""TC-P107-04 Scene-cut contamination.

Host reference. A real cut resets history even when timestamps stay continuous.
"""

from __future__ import annotations

CASE_ID = "TC-P107-04"
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "continuous-timestamps-preserve-state"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scene_cut",
    "timestamps_continuous",
    "history_reset",
    "leaked_depth",
    "leaked_color",
)
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


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(), "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    flags = ("scene_cut", "timestamps_continuous", "history_reset", "leaked_depth", "leaked_color")
    for name in flags:
        _require(type(payload[name]) is bool, f"{name} must be a bool")
    scene_cut = payload["scene_cut"]
    continuous = payload["timestamps_continuous"]
    reset = payload["history_reset"]
    leaked_depth = payload["leaked_depth"]
    leaked_color = payload["leaked_color"]
    contamination = int(scene_cut and not reset) + int(leaked_depth) + int(leaked_color)
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"contamination={contamination}",
    ]
    rejected: list[str] = []
    if scene_cut and continuous and not reset:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if scene_cut and not reset and NEGATIVE_TOKEN not in rejected:
        rejected.append("history-not-reset")
        reasons.append("history was not reset at the cut")
    if leaked_depth or leaked_color:
        rejected.append("previous-image-leak")
        reasons.append("previous-image depth or color leaked into the new shot")
    if not rejected:
        reasons.append("history policy retained for this host fixture")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"contamination={contamination}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
