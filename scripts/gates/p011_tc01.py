"""TC-P011-01 partial characteristic failure.

One throwing characteristic query must not erase readable candidates or the
rational timing inventory. The failed property is reported explicitly.
Container timestamps do not certify native fixed 24.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-01"
INTERVENTION = (
    "Make one camera characteristic query throw while unrelated formats and routes remain readable."
)
EXPECTED = (
    "Retain unaffected capabilities and report the failed property explicitly "
    "rather than returning an empty device inventory."
)
NEGATIVE = "A single exception that erases every candidate must fail."
FAILED_PROPERTIES = ("route_metadata", "timing_arrays", "dynamic_range", "codec")
_CANDIDATE_KEYS = ("id", "queryError")
_PAYLOAD_KEYS = (
    "failedProperty",
    "candidates",
    "aeMin",
    "aeMax",
    "requestedFps",
    "manualConfirmed",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Keep readable candidates and the AE inventory when one query throws."""
    failed, candidates, ae_min, ae_max, requested, manual_confirmed, timestamps = _payload(payload)
    preserved = [item["id"] for item in candidates if item["queryError"] is None]
    preserved.append(f"ae:{_text(ae_min)}-{_text(ae_max)}")
    preserved.append(f"requested:{_text(requested)}")
    rejected = [failed]
    rejected.extend(item["id"] for item in candidates if item["queryError"] is not None)
    reasons = [
        f"failed property {failed} reported without clearing the device inventory",
        "readable formats and routes retained",
    ]
    if any(item["queryError"] is not None for item in candidates):
        reasons.append("a throwing characteristic query does not drop readable candidates")
    reasons.append("advertisement is not operational qualification")
    open_questions = []
    if not manual_confirmed:
        open_questions.append("manual timing has not been confirmed")
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify native fixed 24")
    if not preserved:
        raise ValueError(NEGATIVE)
    decision = "partial"
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    failed = payload["failedProperty"]
    if failed not in FAILED_PROPERTIES:
        raise ValueError("failedProperty must be route_metadata, timing_arrays, dynamic_range, or codec")
    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    parsed = [_candidate(item) for item in candidates]
    ids = [item["id"] for item in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate ids must be unique")
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    manual_confirmed = payload["manualConfirmed"]
    timestamps = payload["containerTimestampsAssigned"]
    if type(manual_confirmed) is not bool or type(timestamps) is not bool:
        raise ValueError("manualConfirmed and containerTimestampsAssigned must be bools")
    return failed, parsed, ae_min, ae_max, requested, manual_confirmed, timestamps


def _candidate(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(_CANDIDATE_KEYS):
        raise ValueError("invalid candidate fields")
    identity = value["id"]
    if not isinstance(identity, str) or not identity or identity != identity.strip():
        raise ValueError("candidate id must be a non-empty string")
    query = value["queryError"]
    if query is not None and (not isinstance(query, str) or not query or query != query.strip()):
        raise ValueError("queryError must be a non-empty string or null")
    return {"id": identity, "queryError": query}


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-01 must not yield qualified, allowed, or native_fixed_24")
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
