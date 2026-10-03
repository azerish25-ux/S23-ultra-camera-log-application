"""TC-P033-04 interrupted source tail.

A source truncated after complete records stays a strict development
rejection unless the caller asks for explicit complete-prefix recovery.
Silently rewriting the original into a shorter valid-looking file fails.
"""

from __future__ import annotations

CASE_ID = "TC-P033-04"
INTERVENTION = "Truncate a source after complete records and within the next frame payload."
EXPECTED = (
    "Keep strict development rejection distinct from an explicit complete-prefix recovery operation."
)
NEGATIVE = "Silently rewriting the original into a shortened valid-looking source must fail."
REPEATS = ("header", "metadata", "payload", "checksum", "end-marker")
_BOUNDARIES = REPEATS
_MODES = ("strict", "recovery")
_PAYLOAD_KEYS = (
    "completeRecords",
    "recordIds",
    "boundary",
    "mode",
    "rewriteOriginal",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Keep strict rejection distinct from explicit prefix recovery."""
    data = _payload(payload)
    boundary = "truncated-" + data["boundary"]
    reasons = [
        "boundary " + data["boundary"],
        "complete records " + str(data["completeRecords"]),
        EXPECTED,
    ]
    rejected = [boundary]
    if data["rewriteOriginal"]:
        decision = "rejected"
        rejected = ["silent-rewrite", boundary]
        reasons.append(NEGATIVE)
        reasons.append("the original was not rewritten")
    elif data["mode"] == "strict":
        decision = "development_rejected"
        reasons.append("strict development rejection does not shorten the original")
    else:
        decision = "prefix_recovered"
        reasons.append("explicit recovery reports the complete prefix and leaves the original unmodified")
        reasons.append("prefix_recovered is not physical qualification")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-04 must not yield qualified or allowed")
    if data["rewriteOriginal"] and decision != "rejected":
        raise ValueError("a silent rewrite must not succeed")
    questions = ["original bytes were not replaced"]
    return _result(decision, reasons, rejected, _preserved(data), questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    count = payload["completeRecords"]
    if type(count) is not int or count < 0:
        raise ValueError("completeRecords must be a non-negative int")
    records = _tokens(payload["recordIds"], "recordIds", allow_empty=count == 0)
    if len(records) != count:
        raise ValueError("recordIds length must equal completeRecords")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is not a truncation boundary")
    mode = payload["mode"]
    if mode not in _MODES:
        raise ValueError("mode must be strict or recovery")
    return {
        "completeRecords": count,
        "recordIds": records,
        "boundary": boundary,
        "mode": mode,
        "rewriteOriginal": _bool(payload["rewriteOriginal"], "rewriteOriginal"),
    }


def _preserved(data: dict) -> list[str]:
    preserved = ["record:" + item for item in data["recordIds"]]
    preserved.extend([
        "boundary:" + data["boundary"],
        "mode:" + data["mode"],
        "complete:" + str(data["completeRecords"]),
        "original:unmodified",
    ])
    return preserved


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{name} must be a list of ids")
    items = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or item in seen:
            raise ValueError(f"{name} items must be unique non-empty strings")
        seen.add(item)
        items.append(item)
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-04 must not yield qualified or allowed")
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
