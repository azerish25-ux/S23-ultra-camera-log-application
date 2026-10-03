"""TC-P037-03 oversized source record.

Reject an impossible length or a truncated header before any allocation.
Allocating from an unvalidated length field is the negative control. The
original file token stays in the inventory either way.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P037-03"
INTERVENTION = "Inject an impossible payload length or dimension into an otherwise valid source header."
EXPECTED = "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
NEGATIVE = "Allocating directly from an unvalidated length field must fail."

_BOUNDARIES = ("declared_maximum", "maximum_plus_one", "integer_overflow", "truncated_header")
_INT32_MAX = 2147483647
_LENGTH = re.compile(r"0|-?[1-9][0-9]*")
_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PAYLOAD_KEYS = (
    "declaredMaximum",
    "lengthField",
    "headerBytes",
    "requiredHeaderBytes",
    "boundary",
    "allocateUnvalidated",
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
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject oversized or unvalidated lengths without allocating them."""
    fields = _payload(payload)
    reasons = [EXPECTED, f"boundary {fields['boundary']}", INTERVENTION]
    preserved = [
        f"file:{fields['originalFile']}",
        f"declaredMaximum:{fields['declaredMaximum']}",
        f"length:{fields['lengthField']}",
        f"headerBytes:{fields['headerBytes']}",
    ]
    rejected: list[str] = []
    if fields["allocateUnvalidated"]:
        rejected.append("unvalidated-length-allocation")
        reasons.append(NEGATIVE)
        reasons.append("rejected before allocation")
    if fields["boundary"] == "maximum_plus_one":
        rejected.append("oversized-record")
        reasons.append("rejected before allocation")
    elif fields["boundary"] == "integer_overflow":
        rejected.append("integer-overflow-length")
        reasons.append("rejected before allocation")
    elif fields["boundary"] == "truncated_header":
        rejected.append("truncated-header")
        reasons.append("rejected before out-of-bounds reading")
    if rejected:
        return _result("rejected", reasons, rejected, preserved, ["original file was not rewritten"])
    reasons.append("length is the declared maximum and the header is complete")
    reasons.append("no allocation was taken from an unvalidated field")
    return _result("bounded_accept", reasons, [], preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    declared = payload["declaredMaximum"]
    if type(declared) is not int or not 1 <= declared <= _INT32_MAX - 1:
        raise ValueError("declaredMaximum must be an int below the int32 maximum")
    length_text = payload["lengthField"]
    if not isinstance(length_text, str) or _LENGTH.fullmatch(length_text) is None:
        raise ValueError("lengthField must be a canonical integer string")
    if len(length_text) > 40:
        raise ValueError("lengthField is unreasonably long")
    length = int(length_text)
    header = payload["headerBytes"]
    required = payload["requiredHeaderBytes"]
    if type(header) is not int or header < 0 or type(required) is not int or required <= 0:
        raise ValueError("header sizes must be ints")
    if header > 1_000_000 or required > 1_000_000:
        raise ValueError("header sizes exceed the harness bound")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is not a TC-P037-03 repeat")
    allocate = payload["allocateUnvalidated"]
    if type(allocate) is not bool:
        raise ValueError("allocateUnvalidated must be a bool")
    original = payload["originalFile"]
    if not isinstance(original, str) or _FILE.fullmatch(original) is None:
        raise ValueError("originalFile must be a token")
    complete = header >= required
    if boundary == "declared_maximum":
        if length != declared or not complete or length < 0:
            raise ValueError("declared_maximum does not match the length and header")
    elif boundary == "maximum_plus_one":
        if length != declared + 1 or not complete or length > _INT32_MAX:
            raise ValueError("maximum_plus_one does not match the length")
    elif boundary == "integer_overflow":
        if not complete or not (length > _INT32_MAX or length < 0):
            raise ValueError("integer_overflow needs a length outside int32")
    elif header >= required or length != declared:
        raise ValueError("truncated_header needs a short header and the declared length")
    return {
        "declaredMaximum": declared,
        "lengthField": length_text,
        "headerBytes": header,
        "requiredHeaderBytes": required,
        "boundary": boundary,
        "allocateUnvalidated": allocate,
        "originalFile": original,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-03 must not yield qualified or allowed")
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
