"""TC-P111-04 Scene-cut contamination.

Host fixture. A real cut drops temporal state even when timestamps stay continuous.
"""

from __future__ import annotations

CASE_ID = "TC-P111-04"
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "continuous-timestamps-preserve-history-across-cut"
PAYLOAD_KEYS = ("evidenceId", "repeat", "cut", "timestampsContinuous", "historyCarried")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    for label in ("cut", "timestampsContinuous", "historyCarried"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    cut = payload["cut"]
    continuous = payload["timestampsContinuous"]
    carried = payload["historyCarried"]
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"cut={cut} timestamps_continuous={continuous} history_carried={carried}",
    ]
    rejected: list[str] = []
    if cut and carried:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("continuous timestamps did not authorize carrying history across the cut")
    else:
        decision = "recorded"
        if cut:
            reasons.append("history reset on the cut")
        elif carried:
            reasons.append("history retained inside one shot")
        else:
            reasons.append("history was already empty")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"history_carried:{carried}", f"cut:{cut}"],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
