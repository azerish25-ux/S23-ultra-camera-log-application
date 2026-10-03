"""TC-P027-03 gap concealed by average rate.

A long interval plus compensating short intervals can keep the average near
target. The source cadence defect is still reported and the original timing
evidence is kept. A mean-only validator must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-03"
INTERVENTION = (
    "Insert a long interval and compensating short intervals so average frame rate remains near target."
)
EXPECTED = "Report the source cadence defect and preserve the original timing evidence."
NEGATIVE = "A mean-only validator must be killed by this fixture."
PATTERNS = (
    "long-and-short-intervals",
    "duplicate-timestamps",
    "repeated-image-content",
    "missing-source-frame",
)
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_NUM = re.compile(r"[1-9][0-9]*")
_PAYLOAD_KEYS = {
    "pattern",
    "averageNearTarget",
    "meanOnlyValidator",
    "intervalsMs",
    "timingEvidence",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Kill a mean-only pass. Keep every original interval."""
    data = _payload(payload)
    reasons = [
        f"pattern {data['pattern']}",
        "average near target" if data["averageNearTarget"] else "average away from target",
        INTERVENTION,
    ]
    preserved = [data["timingEvidence"]] + [f"interval:{item}" for item in data["intervalsMs"]]
    if data["meanOnlyValidator"]:
        decision = "rejected"
        rejected = ["mean-only-validator"]
        reasons.append(NEGATIVE)
    else:
        decision = "cadence_defect"
        rejected = []
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    pattern = payload["pattern"]
    if pattern not in PATTERNS:
        raise ValueError("pattern is not a declared cadence defect")
    intervals = payload["intervalsMs"]
    if not isinstance(intervals, list) or not intervals:
        raise ValueError("intervalsMs must be a non-empty list")
    parsed = []
    for item in intervals:
        if not isinstance(item, str) or _NUM.fullmatch(item) is None:
            raise ValueError("intervalsMs entries must be canonical positive integer strings")
        parsed.append(item)
    evidence = payload["timingEvidence"]
    if not isinstance(evidence, str) or _TOKEN.fullmatch(evidence) is None:
        raise ValueError("timingEvidence must be a token")
    return {
        "pattern": pattern,
        "averageNearTarget": _bool(payload["averageNearTarget"], "averageNearTarget"),
        "meanOnlyValidator": _bool(payload["meanOnlyValidator"], "meanOnlyValidator"),
        "intervalsMs": parsed,
        "timingEvidence": evidence,
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-03 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
