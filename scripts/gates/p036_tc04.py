"""TC-P036-04 interrupted source tail.

Intervention: Truncate a source after complete records and within the next
frame payload.
Expected: Keep strict development rejection distinct from an explicit
complete-prefix recovery operation.
Negative: Silently rewriting the original into a shortened valid-looking source
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P036-04"
INTERVENTION = "Truncate a source after complete records and within the next frame payload."
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix "
    "recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."

_BOUNDARIES = ("header", "metadata", "payload", "checksum", "end_marker")
_OPERATIONS = ("strict_development", "explicit_prefix_recovery", "silent_rewrite")
_PAYLOAD_KEYS = (
    "boundary",
    "completeRecords",
    "operation",
    "originalToken",
    "prefixToken",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "development_rejected", "prefix_recovered", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject a strict read of a truncated tail. Do not silently shorten it."""
    fields = _payload(payload)
    original = fields["originalToken"]
    prefix = fields["prefixToken"]
    rejected: list[str] = []
    questions: list[str] = []
    if fields["operation"] == "silent_rewrite":
        decision = "rejected"
        rejected.append("silent-rewrite")
        reasons = [NEGATIVE, EXPECTED, "original source was not rewritten"]
        preserved = [original]
        questions.append("shortened source was not substituted")
    elif fields["operation"] == "strict_development":
        decision = "development_rejected"
        reasons = [
            EXPECTED,
            f"strict development rejected the truncated {fields['boundary']}",
            "strict rejection is not prefix recovery",
        ]
        preserved = [original]
        questions.append("development rejected")
    elif fields["completeRecords"] > 0:
        decision = "prefix_recovered"
        reasons = [
            EXPECTED,
            (
                f"explicit prefix recovery kept {fields['completeRecords']} complete records "
                f"at {fields['boundary']}"
            ),
            "original source was not rewritten",
            "prefix recovery is not strict acceptance",
        ]
        preserved = [original, prefix]
        questions.append("prefix recovery is explicit")
    else:
        decision = "withheld"
        reasons = [
            EXPECTED,
            "no complete prefix was available to recover",
            "original source was not rewritten",
        ]
        preserved = [original]
        questions.append("no complete prefix")
    reasons.append(f"boundary:{fields['boundary']}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is not a truncation point")
    records = payload["completeRecords"]
    if type(records) is not int or records < 0:
        raise ValueError("completeRecords must be a non-negative int")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is not a known tail policy")
    original = payload["originalToken"]
    prefix = payload["prefixToken"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalToken must be a non-empty string")
    if not isinstance(prefix, str) or not prefix or prefix != prefix.strip():
        raise ValueError("prefixToken must be a non-empty string")
    if original == prefix:
        raise ValueError("prefixToken must differ from the original")
    return {
        "boundary": boundary,
        "completeRecords": records,
        "operation": operation,
        "originalToken": original,
        "prefixToken": prefix,
    }


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
