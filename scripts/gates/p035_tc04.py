"""TC-P035-04 interrupted source tail.

Intervention: Truncate a source after complete records and within the next
frame payload.
Expected: Keep strict development rejection distinct from an explicit
complete-prefix recovery operation.
Negative: Silently rewriting the original into a shortened valid-looking
source must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P035-04"
INTERVENTION = (
    "Truncate a source after complete records and within the next frame payload."
)
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix "
    "recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."

BOUNDARIES = ("header", "metadata", "payload", "checksum", "end_marker")
OPERATIONS = ("strict", "recover_prefix", "rewrite_short")
_PAYLOAD_KEYS = ("boundary", "completeRecords", "operation", "originalToken")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "strict_rejected", "prefix_recovered")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Separate strict rejection, explicit prefix recovery, and silent rewrite."""
    boundary, count, operation, token = _payload(payload)
    preserved = [
        f"original:{token}",
        f"boundary:{boundary}",
        f"complete-records:{count}",
    ]
    if operation == "rewrite_short":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "the original token is not replaced by a shortened file"],
            ["silent-rewrite"],
            preserved,
            ["original file preserved"],
        )
    if operation == "strict":
        return _result(
            "strict_rejected",
            [EXPECTED, "strict development rejection is distinct from prefix recovery"],
            [],
            preserved,
            [f"{boundary} tail rejected"],
        )
    preserved.append(f"prefix-records:{count}")
    return _result(
        "prefix_recovered",
        [
            EXPECTED,
            "explicit complete-prefix recovery leaves the original token unchanged",
        ],
        [],
        preserved,
        ["recovered prefix is not a completed source"],
    )


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    boundary = payload["boundary"]
    operation = payload["operation"]
    count = payload["completeRecords"]
    token = payload["originalToken"]
    if boundary not in BOUNDARIES or operation not in OPERATIONS:
        raise ValueError("boundary or operation")
    if type(count) is not int or count < 0:
        raise ValueError("completeRecords")
    if boundary == "header" and count != 0:
        raise ValueError("a header boundary has no complete records")
    if boundary != "header" and count < 1:
        raise ValueError("a frame boundary needs a complete prefix count")
    if not isinstance(token, str) or not token or token != token.strip():
        raise ValueError("originalToken")
    return boundary, count, operation, token


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
