"""TC-P110-04 Scene-cut contamination.

Host fixture. A continuous timestamp must not keep history across a real cut.
"""

from __future__ import annotations

CASE_ID = "TC-P110-04"
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "timestamps-alone-preserve-temporal-state-across-cut"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "cut", "timestampsContinuous", "history", "current", "policy")
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


def _samples(values, name: str) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, name + " must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{name}[{index}] must be a number")
        number = float(item)
        _require(number == number and abs(number) != float("inf"), f"{name}[{index}] must be finite")
        numbers.append(number)
    return numbers


def resolve_cut(history: list[float], current: list[float], cut: bool, policy: str):
    if policy == "reset":
        return list(current), False
    if policy != "preserve":
        raise ValueError("policy must be preserve or reset")
    mixed = [0.5 * (old + new) for old, new in zip(history, current)]
    if not cut:
        return mixed, False
    leaked = any(old != new and mixed_value != new for old, new, mixed_value in zip(history, current, mixed))
    return mixed, leaked


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["cut"]) is bool, "cut must be a bool")
    _require(type(payload["timestampsContinuous"]) is bool, "timestampsContinuous must be a bool")
    history = _samples(payload["history"], "history")
    current = _samples(payload["current"], "current")
    _require(len(history) == len(current), "history and current lengths must match")
    _output, leaked = resolve_cut(history, current, payload["cut"], payload["policy"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if leaked:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if payload["timestampsContinuous"]:
            reasons.append("continuous timestamps did not justify keeping history across the cut")
        else:
            reasons.append("previous-image values leaked into the new shot")
    else:
        decision = "recorded"
        if payload["cut"]:
            reasons.append("history was reset at the cut; previous colour and depth did not leak")
        else:
            reasons.append("no scene cut; temporal state was allowed to blend")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
