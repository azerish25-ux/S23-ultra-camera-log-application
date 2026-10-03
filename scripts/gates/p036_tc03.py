"""TC-P036-03 oversized source record.

Intervention: Inject an impossible payload length or dimension into an otherwise
valid source header.
Expected: Reject before unbounded allocation or out-of-bounds reading, preserving
the original file.
Negative: Allocating directly from an unvalidated length field must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P036-03"
INTERVENTION = (
    "Inject an impossible payload length or dimension into an otherwise valid source header."
)
EXPECTED = (
    "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
)
NEGATIVE = "Allocating directly from an unvalidated length field must fail."

_INT64_MAX = 2**63 - 1
_PAYLOAD_KEYS = (
    "declaredMaxBytes",
    "claimedLength",
    "width",
    "height",
    "headerTruncated",
    "allocateFromUnvalidatedLength",
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
_DECISIONS = ("rejected", "rejected_before_alloc", "bounded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject impossible lengths before allocation. Keep the original file."""
    fields = _payload(payload)
    preserved = [
        fields["originalFile"],
        f"declaredMax:{fields['declaredMaxBytes']}",
        f"claimed:{fields['claimedLength']}",
        f"dimensions:{fields['width']}x{fields['height']}",
    ]
    safe = _safe(fields)
    rejected: list[str] = []
    questions: list[str] = []
    if fields["allocateFromUnvalidatedLength"]:
        decision = "rejected"
        rejected.append("unvalidated-length-allocation")
        reasons = [NEGATIVE, EXPECTED, "original file preserved"]
        questions.append("allocation was refused")
    elif safe:
        decision = "bounded"
        reasons = [
            EXPECTED,
            "length and dimensions stayed inside the declared maximum",
            "original file preserved",
        ]
    else:
        decision = "rejected_before_alloc"
        reasons = [EXPECTED, "rejected before unbounded allocation", "original file preserved"]
        if fields["headerTruncated"]:
            rejected.append("truncated-header")
            questions.append("truncated header")
        if fields["claimedLength"] < 0 or fields["claimedLength"] > _INT64_MAX:
            rejected.append("integer-overflow-boundary")
            questions.append("integer overflow boundary")
        elif fields["claimedLength"] == fields["declaredMaxBytes"] + 1:
            rejected.append("maximum-plus-one")
            questions.append("maximum plus one")
        elif fields["claimedLength"] > fields["declaredMaxBytes"]:
            rejected.append("length-above-maximum")
        if fields["width"] <= 0 or fields["height"] <= 0:
            rejected.append("impossible-dimension")
            questions.append("impossible dimension")
        if fields["claimedLength"] == 0:
            rejected.append("empty-length")
    return _result(decision, reasons, rejected, preserved, questions)


def _safe(fields: dict) -> bool:
    if fields["headerTruncated"]:
        return False
    if fields["width"] <= 0 or fields["height"] <= 0:
        return False
    length = fields["claimedLength"]
    if length <= 0 or length > _INT64_MAX:
        return False
    return length <= fields["declaredMaxBytes"]


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    declared = payload["declaredMaxBytes"]
    claimed = payload["claimedLength"]
    width = payload["width"]
    height = payload["height"]
    if type(declared) is not int or declared <= 0:
        raise ValueError("declaredMaxBytes must be a positive int")
    if type(claimed) is not int or type(width) is not int or type(height) is not int:
        raise ValueError("claimedLength, width, and height must be ints")
    truncated = payload["headerTruncated"]
    allocate = payload["allocateFromUnvalidatedLength"]
    if type(truncated) is not bool or type(allocate) is not bool:
        raise ValueError("headerTruncated and allocateFromUnvalidatedLength must be bools")
    original = payload["originalFile"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalFile must be a non-empty string")
    return {
        "declaredMaxBytes": declared,
        "claimedLength": claimed,
        "width": width,
        "height": height,
        "headerTruncated": truncated,
        "allocateFromUnvalidatedLength": allocate,
        "originalFile": original,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("source-length decision cannot be qualified or allowed")
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
