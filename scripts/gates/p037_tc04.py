"""TC-P037-04 interrupted source tail.

Strict development rejects a truncated tail. An explicit complete-prefix
recovery is a different operation and does not rewrite the original. Silently
shortening the source into a valid-looking file is rejected.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P037-04"
INTERVENTION = "Truncate a source after complete records and within the next frame payload."
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."

_CUTS = ("header", "metadata", "payload", "checksum", "end_marker")
_OPERATIONS = ("strict", "recover_prefix", "silent_rewrite")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PAYLOAD_KEYS = ("completeRecords", "cutAt", "operation", "originalSource")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep strict rejection distinct from explicit prefix recovery."""
    records, cut_at, operation, original = _payload(payload)
    preserved = [f"original:{original}"]
    preserved.extend(f"complete:{item}" for item in records)
    reasons = [EXPECTED, f"cut {cut_at}", INTERVENTION]
    if operation == "silent_rewrite":
        reasons.append(NEGATIVE)
        reasons.append("original source was not rewritten")
        return _result(
            "rejected",
            reasons,
            ["silent-rewrite"],
            preserved,
            ["shortened source was not substituted"],
        )
    if operation == "strict":
        reasons.append("strict development rejection is not prefix recovery")
        return _result(
            "development_rejected",
            reasons,
            ["incomplete-tail"],
            preserved,
            ["strict rejection was not rewritten into a shortened source"],
        )
    if cut_at == "header" or not records:
        reasons.append("no complete prefix is available to recover")
        return _result(
            "rejected",
            reasons,
            ["no-complete-prefix"],
            preserved,
            ["recovery was refused"],
        )
    reasons.append("explicit prefix recovery left the original source unchanged")
    preserved.extend(f"recovered:{item}" for item in records)
    return _result("prefix_recovered", reasons, [], preserved, [f"recovered {len(records)} complete records"])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    records = payload["completeRecords"]
    if not isinstance(records, list) or len(records) > 16:
        raise ValueError("completeRecords must be a list of at most 16")
    parsed: list[str] = []
    for item in records:
        if not isinstance(item, str) or _TOKEN.fullmatch(item) is None:
            raise ValueError("completeRecords must be tokens")
        if item in parsed:
            raise ValueError("completeRecords must be unique")
        parsed.append(item)
    cut_at = payload["cutAt"]
    if cut_at not in _CUTS:
        raise ValueError("cutAt is not a TC-P037-04 boundary")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is unknown")
    original = payload["originalSource"]
    if not isinstance(original, str) or _TOKEN.fullmatch(original) is None:
        raise ValueError("originalSource must be a token")
    if cut_at == "header" and parsed:
        raise ValueError("a header cut cannot already contain complete records")
    return parsed, cut_at, operation, original


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-04 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
