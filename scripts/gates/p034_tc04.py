"""TC-P034-04 interrupted source tail.

Strict development rejection and explicit complete-prefix recovery are
different decisions. Both keep the original id. A silent rewrite into a
shorter valid-looking source fails.
"""

from __future__ import annotations

CASE_ID = "TC-P034-04"
INTERVENTION = (
    "Truncate a source after complete records and within the next frame payload."
)
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix "
    "recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."

BOUNDARIES = ("header", "metadata", "payload", "checksum", "end_marker")
OPERATIONS = ("strict_reject", "prefix_recovery", "silent_rewrite")
_PAYLOAD_KEYS = ("boundary", "completeRecords", "operation", "originalId")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "development_rejected", "prefix_recovered"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Separate a strict tail rejection from an explicit prefix recovery."""
    boundary, complete, operation, original = _payload(payload)
    preserved = [
        f"original:{original}",
        f"complete:{complete}",
        f"boundary:{boundary}",
    ]
    reasons = [INTERVENTION, EXPECTED, f"boundary {boundary}"]
    if operation == "silent_rewrite":
        reasons.append(NEGATIVE)
        reasons.append("the original id was not replaced by a shortened source")
        return _result(
            "rejected",
            reasons,
            ["silent-rewrite"],
            preserved,
            ["original preserved"],
        )
    if operation == "strict_reject":
        reasons.append("strict development rejection is not prefix recovery")
        return _result(
            "development_rejected",
            reasons,
            [],
            preserved,
            [f"rejected-at:{boundary}"],
        )
    preserved.append(f"recovered-prefix:{complete}")
    reasons.append("explicit prefix recovery is not a silent rewrite and not development acceptance")
    return _result(
        "prefix_recovered",
        reasons,
        [],
        preserved,
        ["explicit prefix recovery is not development acceptance"],
    )


def _payload(payload: object) -> tuple[str, int, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in BOUNDARIES:
        raise ValueError("boundary is not a known tail boundary")
    complete = payload["completeRecords"]
    if type(complete) is not int or complete < 0:
        raise ValueError("completeRecords must be a non-negative int")
    operation = payload["operation"]
    if operation not in OPERATIONS:
        raise ValueError("operation is not a known tail operation")
    original = payload["originalId"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalId must be a non-empty string")
    return boundary, complete, operation, original


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("tail decision cannot be qualified or allowed")
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
