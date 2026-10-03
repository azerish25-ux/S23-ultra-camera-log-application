"""TC-P025-03 gap concealed by average rate.

Intervention: Insert a long interval and compensating short intervals so
average frame rate remains near target.
Expected: Report the source cadence defect and preserve the original timing
evidence.
Negative: A mean-only validator must be killed by this fixture.
"""

from __future__ import annotations

CASE_ID = "TC-P025-03"
INTERVENTION = (
    "Insert a long interval and compensating short intervals so average frame rate remains near target."
)
EXPECTED = "Report the source cadence defect and preserve the original timing evidence."
NEGATIVE = "A mean-only validator must be killed by this fixture."

_VALIDATORS = ("mean_only", "interval")
_PAYLOAD_KEYS = (
    "targetIntervalNs",
    "intervalsNs",
    "duplicateTimestamp",
    "repeatedImageContent",
    "missingSourceFrame",
    "validator",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "cadence_defect", "intervals_retained")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep every source interval. A mean near the target does not hide a gap."""
    target, intervals, duplicate, repeated, missing, validator = _payload(payload)
    preserved = [f"target:{target}"]
    preserved.extend(f"interval:{item}" for item in intervals)
    if duplicate:
        preserved.append("duplicate-timestamp")
    if repeated:
        preserved.append("repeated-image-content")
    if missing:
        preserved.append("missing-source-frame")

    long_gap = any(item > 2 * target for item in intervals)
    short_gap = any(item * 2 < target for item in intervals)
    defect = long_gap or short_gap or duplicate or repeated or missing
    total = sum(intervals)
    count = len(intervals)
    near = abs(total - target * count) * 100 <= target * count

    rejected: list[str] = []
    questions: list[str] = []
    if validator == "mean_only":
        decision = "rejected"
        rejected = ["mean-only-validator"]
        if defect:
            rejected.append("source-cadence-defect")
        questions = ["mean is not source cadence"]
        reasons = [
            NEGATIVE,
            EXPECTED,
            f"mean of {count} intervals is near target" if near else "mean is not near target",
            "original intervals are preserved",
        ]
    elif defect:
        decision = "cadence_defect"
        rejected = ["source-cadence-defect"]
        if long_gap:
            rejected.append("long-interval")
        if short_gap:
            rejected.append("short-interval")
        if duplicate:
            rejected.append("duplicate-timestamp")
        if repeated:
            rejected.append("repeated-image-content")
        if missing:
            rejected.append("missing-source-frame")
        questions = ["source cadence defect"]
        reasons = [EXPECTED, "original timing evidence is preserved", "average rate does not conceal the gap"]
    else:
        decision = "intervals_retained"
        questions = ["host intervals do not certify fixed cadence"]
        reasons = [
            "no concealed gap was present in the supplied intervals",
            "retaining intervals is not a fixed-cadence certificate",
        ]

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int, list[int], bool, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    target = payload["targetIntervalNs"]
    if type(target) is not int or target <= 0:
        raise ValueError("targetIntervalNs must be a positive int")
    intervals = payload["intervalsNs"]
    if (
        not isinstance(intervals, list)
        or len(intervals) < 2
        or any(type(item) is not int or item <= 0 for item in intervals)
    ):
        raise ValueError("intervalsNs must be a list of at least two positive ints")
    duplicate = _bool(payload["duplicateTimestamp"], "duplicateTimestamp")
    repeated = _bool(payload["repeatedImageContent"], "repeatedImageContent")
    missing = _bool(payload["missingSourceFrame"], "missingSourceFrame")
    validator = payload["validator"]
    if validator not in _VALIDATORS:
        raise ValueError("validator must be mean_only or interval")
    return target, list(intervals), duplicate, repeated, missing, validator


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("cadence decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
