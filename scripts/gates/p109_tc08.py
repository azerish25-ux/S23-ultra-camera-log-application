"""TC-P109-08 Whole-clip acceptance.

Host fixture. A favorable mean must not hide severe boundary failures.
A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P109-08"
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
NEGATIVE_TOKEN = "mean-hides-severe-boundary-failures"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frameScores",
    "severities",
    "acceptByMean",
    "catastrophicRecordedSeparately",
    "releaseLimited",
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
    scores = payload["frameScores"]
    severities = payload["severities"]
    _require(isinstance(scores, list) and len(scores) >= 1, "frameScores must be a non-empty list")
    _require(isinstance(severities, list) and len(severities) == len(scores), "severities must match frameScores")
    _require(type(payload["acceptByMean"]) is bool, "acceptByMean must be a bool")
    _require(type(payload["catastrophicRecordedSeparately"]) is bool, "catastrophicRecordedSeparately must be a bool")
    _require(type(payload["releaseLimited"]) is bool, "releaseLimited must be a bool")
    values: list[float] = []
    for index, item in enumerate(scores):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"frameScore {index}")
        number = float(item)
        _require(number == number and 0.0 <= number <= 1.0, f"frameScore {index}")
        values.append(number)
        severity = severities[index]
        _require(type(severity) is int and severity >= 0, f"severity {index}")
    mean = sum(values) / len(values)
    severe = sum(1 for severity in severities if severity > 0)
    claims: list[str] = []
    if severe > 0 and payload["acceptByMean"]:
        claims.append(NEGATIVE_TOKEN)
    if severe > 0 and payload["catastrophicRecordedSeparately"] is False:
        claims.append("catastrophic-artifacts-not-recorded-separately")
    if severe > 0 and payload["releaseLimited"] is False:
        claims.append("release-not-limited-after-severe-failures")
    detail = f"mean-score {mean:.6f} severe {severe}"
    decision = "rejected" if claims else "recorded"
    return _finish(evidence, repeat, decision, claims, detail)
