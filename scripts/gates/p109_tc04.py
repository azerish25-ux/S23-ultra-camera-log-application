"""TC-P109-04 Scene-cut contamination.

Host fixture. Continuous timestamps do not keep history across a real cut.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-04"
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "continuous-timestamps-preserve-state-across-cut"
PAYLOAD_KEYS = ("evidenceId", "repeat", "sceneCut", "timestampsContinuous", "historyRetained")
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


def _finish(evidence: str, repeat: str, decision: str, rejected: list[str], detail: str) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, detail]
    if decision == "rejected":
        reasons.append(NEGATIVE)
    else:
        reasons.append("narrower software result retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    scene_cut = payload["sceneCut"]
    continuous = payload["timestampsContinuous"]
    retained = payload["historyRetained"]
    _require(type(scene_cut) is bool, "sceneCut must be a bool")
    _require(type(continuous) is bool, "timestampsContinuous must be a bool")
    _require(type(retained) is bool, "historyRetained must be a bool")
    if scene_cut and retained:
        detail = (
            "history retained across a scene cut; "
            f"timestampsContinuous={continuous} is not permission to keep the previous shot"
        )
        return _finish(evidence, repeat, "rejected", [NEGATIVE_TOKEN], detail)
    if scene_cut:
        detail = f"history reset at the cut; timestampsContinuous={continuous}"
        return _finish(evidence, repeat, "recorded", [], detail)
    detail = f"no scene cut; historyRetained={retained}; timestampsContinuous={continuous}"
    return _finish(evidence, repeat, "recorded", [], detail)
