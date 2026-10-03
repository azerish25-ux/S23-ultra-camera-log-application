"""TC-P035-03 oversized source record.

Intervention: Inject an impossible payload length or dimension into an
otherwise valid source header.
Expected: Reject before unbounded allocation or out-of-bounds reading,
preserving the original file.
Negative: Allocating directly from an unvalidated length field must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P035-03"
INTERVENTION = (
    "Inject an impossible payload length or dimension into an otherwise valid source header."
)
EXPECTED = (
    "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
)
NEGATIVE = "Allocating directly from an unvalidated length field must fail."

CANONICAL = re.compile(r"0|[1-9][0-9]*")
INT64_LIMIT = 1 << 63
DIM_LIMIT = 1 << 20
_PAYLOAD_KEYS = (
    "declaredLength",
    "declaredWidth",
    "declaredHeight",
    "maximumBytes",
    "headerComplete",
    "fileToken",
    "allocateUnvalidated",
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
    """Refuse unbounded allocation. The original file token stays intact."""
    length_text, width, height, maximum, complete, token, allocate = _payload(payload)
    preserved = [
        f"file:{token}",
        f"declared-length:{length_text}",
        f"declared-size:{width}x{height}",
    ]
    claims: list[str] = []
    if not complete:
        claims.append("truncated-header")
    overflow = len(length_text) > 18 or _exceeds_int64(length_text)
    if overflow:
        claims.append("integer-overflow")
    if width <= 0 or height <= 0 or width >= DIM_LIMIT or height >= DIM_LIMIT:
        claims.append("impossible-dimension")
    elif width * height > DIM_LIMIT or width * height * 2 > maximum:
        claims.append("impossible-dimension")
    if allocate:
        claims.append("unvalidated-length-allocation")
    length_value = None if overflow else int(length_text)
    if length_value is not None and length_value > maximum:
        claims.append("over-maximum")
    if claims:
        reasons = [EXPECTED, "rejected before allocation"]
        if "unvalidated-length-allocation" in claims:
            reasons.append(NEGATIVE)
        if "truncated-header" in claims:
            reasons.append("truncated header is not a readable record")
        if "integer-overflow" in claims:
            reasons.append("length field overflows the checked integer boundary")
        if "over-maximum" in claims:
            reasons.append("declared length is above the maximum")
        if "impossible-dimension" in claims:
            reasons.append("declared dimensions are not allocated")
        return _result("rejected", reasons, claims, preserved, ["original file preserved"])
    return _result(
        "bounded",
        [EXPECTED, "declared length is inside the maximum and was not allocated"],
        [],
        preserved,
        ["bounded acceptance is not physical S23 qualification"],
    )


def _exceeds_int64(text: str) -> bool:
    if len(text) > 19:
        return True
    return int(text) >= INT64_LIMIT


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    length = payload["declaredLength"]
    if not isinstance(length, str) or CANONICAL.fullmatch(length) is None:
        raise ValueError("declaredLength")
    width = payload["declaredWidth"]
    height = payload["declaredHeight"]
    maximum = payload["maximumBytes"]
    if type(width) is not int or type(height) is not int or type(maximum) is not int:
        raise ValueError("dimensions must be ints")
    if maximum <= 0:
        raise ValueError("maximumBytes must be positive")
    if type(payload["headerComplete"]) is not bool or type(payload["allocateUnvalidated"]) is not bool:
        raise ValueError("flags must be bools")
    token = payload["fileToken"]
    if not isinstance(token, str) or not token or token != token.strip():
        raise ValueError("fileToken")
    return (
        length,
        width,
        height,
        maximum,
        payload["headerComplete"],
        token,
        payload["allocateUnvalidated"],
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("length decision cannot be qualified or allowed")
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
