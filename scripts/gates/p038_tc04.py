"""TC-P038-04 interrupted source tail.

Intervention: Truncate a source after complete records and within the next
frame payload.
Expected: Keep strict development rejection distinct from an explicit
complete-prefix recovery operation.
Negative: Silently rewriting the original into a shortened valid-looking source
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-04"
INTERVENTION = "Truncate a source after complete records and within the next frame payload."
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix "
    "recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."

_BOUNDARIES = ("header", "metadata", "payload", "checksum", "end-marker")
_OPERATIONS = ("strict", "recover-prefix", "silent-rewrite")
_USABLE = ("metadata", "payload", "checksum", "end-marker")
_PAYLOAD_KEYS = (
    "boundary",
    "completeRecords",
    "truncatedInsideNext",
    "operation",
    "originalToken",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "prefix_recovered")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject strict development of a truncated tail. Do not rewrite the original."""
    boundary, complete, truncated, operation, original = _payload(payload)
    preserved = [original, f"boundary:{boundary}", f"completeRecords:{complete}"]
    if operation == "silent-rewrite":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "original token was not replaced by a shortened source"],
            ["silent-rewrite"],
            preserved,
            ["original bytes unchanged"],
        )
    if not truncated:
        return _result(
            "withheld",
            [EXPECTED, "an intact tail is not a recovery and not a development qualification"],
            [],
            preserved,
            ["source tail is intact"],
        )
    if operation == "strict":
        return _result(
            "rejected",
            [EXPECTED, "strict development rejected", "recovery was not implied"],
            ["strict-development-rejected"],
            preserved,
            [f"truncated at {boundary}"],
        )
    if boundary not in _USABLE or complete <= 0:
        return _result(
            "withheld",
            [EXPECTED, "explicit recovery found no complete prefix"],
            [],
            preserved,
            ["header truncation has no complete prefix"],
        )
    preserved = preserved + [f"recoveredRecords:{complete}"]
    return _result(
        "prefix_recovered",
        [
            EXPECTED,
            "explicit complete-prefix recovery is distinct from strict rejection",
            "original token retained beside the recovery artifact",
        ],
        [],
        preserved,
        ["recovered prefix is not a qualified development"],
    )


def _payload(payload: object) -> tuple[str, int, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is not a known source boundary")
    complete = payload["completeRecords"]
    if type(complete) is not int or complete < 0:
        raise ValueError("completeRecords must be a non-negative int")
    truncated = payload["truncatedInsideNext"]
    if type(truncated) is not bool:
        raise ValueError("truncatedInsideNext must be a bool")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is not strict, recover-prefix, or silent-rewrite")
    original = payload["originalToken"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalToken must be a non-empty string")
    return boundary, complete, truncated, operation, original


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
