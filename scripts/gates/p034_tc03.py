"""TC-P034-03 oversized source record.

Reject an impossible length, dimension, overflow, or truncated header before
allocation. The original file token stays in the result. Allocating from an
unvalidated length field is the negative control.
"""

from __future__ import annotations

CASE_ID = "TC-P034-03"
INTERVENTION = (
    "Inject an impossible payload length or dimension into an otherwise valid source header."
)
EXPECTED = (
    "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
)
NEGATIVE = "Allocating directly from an unvalidated length field must fail."

_PAYLOAD_KEYS = (
    "declaredMaximum",
    "lengthField",
    "width",
    "height",
    "maxDimension",
    "overflow",
    "truncatedHeader",
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
_DECISIONS = {"rejected", "bounded"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject unvalidated sizes before allocation and keep the original file."""
    fields = _payload(payload)
    preserved = [
        f"file:{fields['originalFile']}",
        f"declared:{fields['declaredMaximum']}",
        f"length:{fields['lengthField']}",
        f"dim:{fields['width']}x{fields['height']}",
    ]
    rejected: list[str] = []
    if fields["allocateFromLength"]:
        rejected.append("unvalidated-length-allocation")
    if fields["overflow"]:
        rejected.append("integer-overflow")
    if fields["truncatedHeader"]:
        rejected.append("truncated-header")
    if fields["lengthField"] > fields["declaredMaximum"]:
        rejected.append("length-exceeds-maximum")
    if fields["width"] > fields["maxDimension"] or fields["height"] > fields["maxDimension"]:
        rejected.append("impossible-dimension")
    reasons = [INTERVENTION, EXPECTED]
    if rejected:
        reasons.append(
            NEGATIVE if "unvalidated-length-allocation" in rejected
            else "rejected before allocation; original file preserved"
        )
        return _result("rejected", reasons, rejected, preserved, ["original file preserved"])
    reasons.append("length and dimensions sit inside the declared bounds")
    reasons.append("no allocation was taken from an unvalidated length")
    return _result("bounded", reasons, [], preserved, ["not a physical source qualification"])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    for label in ("declaredMaximum", "maxDimension"):
        if type(payload[label]) is not int or payload[label] <= 0:
            raise ValueError(f"{label} must be a positive int")
    if type(payload["lengthField"]) is not int or payload["lengthField"] < 0:
        raise ValueError("lengthField must be a non-negative int")
    for label in ("width", "height"):
        if type(payload[label]) is not int or payload[label] <= 0:
            raise ValueError(f"{label} must be a positive int")
    for label in ("overflow", "truncatedHeader", "allocateFromLength"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    name = payload["originalFile"]
    if not isinstance(name, str) or not name or name != name.strip() or "/" in name:
        raise ValueError("originalFile must be a non-empty file name")
    return payload


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
