"""TC-P056-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

import re
from fractions import Fraction


CASE_ID = "TC-P056-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared storage "
    "or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_BOUNDARIES = ("zero", "source-white", "encoding-boundary")
_PAYLOAD_KEYS = (
    "sampleId",
    "value",
    "boundary",
    "implicitClamp",
    "storageLimit",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_NOTES = {
    "zero": "signed values around zero stay signed",
    "source-white": "values around the source white reference stay over-range when above one",
    "encoding-boundary": "the encoding boundary is not an implicit zero-to-one clamp",
}


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range samples until a declared limit. Detect a unit clamp."""
    sample_id, value, boundary, clamp, limit = _payload(payload)
    preserved = [
        sample_id,
        f"value:{value}",
        f"boundary:{boundary}",
        f"limit:{limit}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, _NOTES[boundary]]
    number = Fraction(value)
    if clamp:
        decision = "rejected"
        rejected.append("implicit-zero-to-one-clamp")
        reasons.append(NEGATIVE)
        reasons.append("the original sample was not replaced by a zero-to-one clamp")
        questions.append("implicit clamp detected; stored value remains the input")
    elif limit != "none" and abs(number) > Fraction(limit):
        decision = "withheld"
        rejected.append("beyond-storage-limit")
        reasons.append("the sample is past the declared storage limit and was not silently stored")
        questions.append(f"{sample_id} exceeds storage limit {limit}")
    else:
        decision = "preserved"
        reasons.append("signed and over-range information remains until a declared limit")
        questions.append(f"{boundary} sample {sample_id} was not clamped")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample_id = payload["sampleId"]
    if not isinstance(sample_id, str) or _TOKEN.fullmatch(sample_id) is None:
        raise ValueError("sampleId must be a token")
    value = payload["value"]
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value in {"-0"}:
        raise ValueError("value must be a canonical signed decimal")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    clamp = payload["implicitClamp"]
    if type(clamp) is not bool:
        raise ValueError("implicitClamp must be a bool")
    limit = payload["storageLimit"]
    if limit != "none" and (not isinstance(limit, str) or _SIGNED.fullmatch(limit) is None or limit in {"-0"}):
        raise ValueError("storageLimit must be none or a canonical signed decimal")
    if limit != "none" and Fraction(limit) <= 0:
        raise ValueError("storageLimit must be positive")
    return sample_id, value, boundary, clamp, limit


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-01 must not yield qualified or allowed")
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
