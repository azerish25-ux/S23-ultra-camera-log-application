"""TC-P110-08 Whole-clip acceptance.

Host fixture. A favorable mean must not hide catastrophic boundary frames.
"""

from __future__ import annotations

CASE_ID = "TC-P110-08"
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
NEGATIVE_TOKEN = "mean-score-hides-severe-boundary-failures"
FAVORABLE_MEAN = 0.7
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "scores", "catastrophic", "policy")
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


def _scores(values) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, "scores must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"scores[{index}] must be a number")
        number = float(item)
        _require(number == number and abs(number) != float("inf"), f"scores[{index}] must be finite")
        numbers.append(number)
    return numbers


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    scores = _scores(payload["scores"])
    catastrophic = payload["catastrophic"]
    _require(isinstance(catastrophic, list) and len(catastrophic) == len(scores),
             "catastrophic must match scores")
    _require(all(type(item) is bool for item in catastrophic), "catastrophic must be bools")
    policy = payload["policy"]
    _require(policy in {"mean-only", "limit-release"}, "policy must be mean-only or limit-release")
    mean = sum(scores) / len(scores)
    severe = [index for index, flag in enumerate(catastrophic) if flag]
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"mean {mean:.6g}; severe {len(severe)}",
    ]
    rejected: list[str] = []
    if policy == "mean-only" and severe:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if mean >= FAVORABLE_MEAN:
            reasons.append("favorable mean hid catastrophic boundary frames " + ",".join(str(index) for index in severe))
        else:
            reasons.append("mean alone hid catastrophic boundary frames " + ",".join(str(index) for index in severe))
    elif policy == "limit-release":
        decision = "recorded"
        if severe:
            reasons.append(
                "catastrophic frames "
                + ",".join(str(index) for index in severe)
                + " recorded separately; release settings limited"
            )
        else:
            reasons.append("no catastrophic frame; release limit not required by this clip")
    else:
        decision = "recorded"
        reasons.append("mean did not conceal a severe boundary failure")
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
