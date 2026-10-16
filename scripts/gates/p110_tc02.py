"""TC-P110-02 Disoccluded background.

Host fixture. Newly visible pixels must take current depth, not smeared history.
"""

from __future__ import annotations

CASE_ID = "TC-P110-02"
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "old-depth-fill-newly-visible"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "historyDepth", "historyValid", "currentDepth", "fill")
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


def _depths(values, name: str) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, name + " must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"{name}[{index}] must be a number")
        number = float(item)
        _require(number == number and abs(number) != float("inf"), f"{name}[{index}] must be finite")
        numbers.append(number)
    return numbers


def resolve_disocclusion(history: list[float], valid: list[bool], current: list[float], fill: str):
    output: list[float] = []
    uncertain: list[int] = []
    smeared = False
    for index, (old, ok, new) in enumerate(zip(history, valid, current)):
        if ok:
            output.append(0.5 * (old + new))
            continue
        if fill == "old-depth":
            output.append(old)
            smeared = True
        elif fill == "current-evidence":
            output.append(new)
            uncertain.append(index)
        else:
            raise ValueError("fill must be old-depth or current-evidence")
    return output, smeared, uncertain


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    history = _depths(payload["historyDepth"], "historyDepth")
    current = _depths(payload["currentDepth"], "currentDepth")
    valid = payload["historyValid"]
    _require(isinstance(valid, list) and len(valid) == len(history) == len(current),
             "historyValid length must match depths")
    _require(all(type(item) is bool for item in valid), "historyValid must be bools")
    fill = payload["fill"]
    _require(fill in {"old-depth", "current-evidence"}, "fill must be old-depth or current-evidence")
    _output, smeared, uncertain = resolve_disocclusion(history, valid, current, fill)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if smeared:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("newly visible pixels were filled with historical depth")
    else:
        decision = "recorded"
        if uncertain:
            reasons.append(
                "newly visible pixels "
                + ",".join(str(index) for index in uncertain)
                + " use current depth with uncertainty; historical foreground is not smeared"
            )
        else:
            reasons.append("no newly visible pixel required a disocclusion fill")
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
