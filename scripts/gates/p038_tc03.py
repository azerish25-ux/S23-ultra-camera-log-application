"""TC-P038-03 oversized source record.

Intervention: Inject an impossible payload length or dimension into an
otherwise valid source header.
Expected: Reject before unbounded allocation or out-of-bounds reading,
preserving the original file.
Negative: Allocating directly from an unvalidated length field must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-03"
INTERVENTION = (
    "Inject an impossible payload length or dimension into an otherwise valid source header."
)
EXPECTED = (
    "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
)
NEGATIVE = "Allocating directly from an unvalidated length field must fail."

_INT64_MAX = 9223372036854775807
_DIM_MAX = 65535
_PAYLOAD_KEYS = (
    "declaredMaxBytes",
    "payloadLength",
    "width",
    "height",
    "headerTruncated",
    "allocateFromLength",
    "originalFile",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "bounded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Refuse unvalidated lengths before any allocation. Keep the original file."""
    declared, length, width, height, truncated, allocate, original = _payload(payload)
    preserved = [
        original,
        f"declaredMaxBytes:{declared}",
        f"width:{width}",
        f"height:{height}",
    ]
    rejected: list[str] = []
    if allocate:
        rejected.append("unvalidated-length-allocation")
    if truncated:
        rejected.append("truncated-header")
    if length > _INT64_MAX:
        rejected.append("integer-overflow")
    elif length > declared:
        rejected.append("oversize")
    if width > _DIM_MAX or height > _DIM_MAX:
        rejected.append("impossible-dimension")
    if rejected:
        reasons = [EXPECTED, "allocation was not performed", "original file preserved"]
        if allocate:
            reasons.append(NEGATIVE)
        return _result("rejected", reasons, rejected, preserved, ["no buffer was allocated"])
    reasons = [
        EXPECTED,
        "length stayed inside the declared maximum",
        "original file preserved",
        "bounded acceptance is not a physical capture qualification",
    ]
    return _result("bounded", reasons, [], preserved, ["host bound only"])


def _payload(payload: object) -> tuple[int, int, int, int, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    declared = _uint(payload["declaredMaxBytes"], "declaredMaxBytes")
    length = _uint(payload["payloadLength"], "payloadLength")
    width = _uint(payload["width"], "width")
    height = _uint(payload["height"], "height")
    if declared <= 0 or width <= 0 or height <= 0:
        raise ValueError("declared maximum and dimensions must be positive")
    truncated = payload["headerTruncated"]
    allocate = payload["allocateFromLength"]
    if type(truncated) is not bool or type(allocate) is not bool:
        raise ValueError("header flags must be bools")
    original = payload["originalFile"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalFile must be a non-empty string")
    return declared, length, width, height, truncated, allocate, original


def _uint(value: object, label: str) -> int:
    if type(value) is not str or not value or not value.isdigit():
        raise ValueError(label + " must be a canonical integer string")
    if value != "0" and value[0] == "0":
        raise ValueError(label + " must be canonical")
    return int(value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("size decision cannot be qualified or allowed")
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
