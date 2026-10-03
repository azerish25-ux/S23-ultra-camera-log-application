"""TC-P011-05 ambiguous timing support.

A variable AE range that includes a nominal rate is not fixed cadence.
Constant container timestamps must not upgrade variable sensor timing.
Manual timing awaiting a result stays withheld. The AE upper bound is kept
as stated and is not replaced by the nominal cinematic rate.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-05"
INTERVENTION = (
    "Offer a variable AE range that includes the desired nominal frame rate but no fixed-rate evidence."
)
EXPECTED = (
    "Keep the rate strategy explicit and withhold native fixed-cadence certification "
    "pending measured results."
)
NEGATIVE = (
    "Assigning constant container timestamps must not upgrade variable sensor timing into native cadence."
)
_PAYLOAD_KEYS = (
    "nominal",
    "aeMin",
    "aeMax",
    "fixedRateEvidence",
    "constantContainerTimestamps",
    "manualTimingPending",
    "rateClass",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_RATE_CLASSES = ("integer", "fractional")
_AE_ONLY = "variable AE range only"
_MANUAL_PENDING = "manual timing awaiting result confirmation"
_CONSTANT_TIMESTAMPS = "constant-timestamps"
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Withhold fixed cadence unless fixed-rate evidence is actually present."""
    nominal, ae_min, ae_max, fixed, constant_ts, manual_pending, rate_class = _payload(payload)
    reasons = [f"rate strategy {rate_class} nominal {_text(nominal)}"]
    rejected: list[str] = []
    open_questions: list[str] = []
    if constant_ts:
        rejected.append(_CONSTANT_TIMESTAMPS)
        reasons.append("constant container timestamps do not upgrade variable sensor timing")
    includes = _cmp(ae_min, nominal) <= 0 and _cmp(nominal, ae_max) <= 0
    if includes and not fixed:
        open_questions.append(_AE_ONLY)
        reasons.append("variable AE range includes the nominal rate without fixed-rate evidence")
    if manual_pending:
        open_questions.append(_MANUAL_PENDING)
        reasons.append(_MANUAL_PENDING)
    if fixed and not manual_pending:
        decision = "fixed_cadence"
        reasons.append("fixed-rate evidence supports fixed cadence")
    else:
        decision = "withheld"
        reasons.append("native fixed-cadence certification withheld pending measured results")
    reasons.append(f"AE upper bound {_text(ae_max)} was not rounded to nominal {_text(nominal)}")
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-05 must not yield qualified, allowed, or native_fixed_24")
    if constant_ts and not fixed and decision == "fixed_cadence":
        raise ValueError(NEGATIVE)
    preserved = [_text(nominal), f"ae:{_text(ae_min)}-{_text(ae_max)}"]
    if f"ae:{_text(ae_min)}-{_text(ae_max)}" not in preserved:
        raise ValueError("AE bounds must be preserved")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    rate_class = payload["rateClass"]
    if rate_class not in _RATE_CLASSES:
        raise ValueError("rateClass must be integer or fractional")
    nominal = _rate(payload["nominal"], "nominal", rate_class)
    ae_min = _rate(payload["aeMin"], "aeMin", None)
    ae_max = _rate(payload["aeMax"], "aeMax", None)
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    fixed = _bool(payload["fixedRateEvidence"], "fixedRateEvidence")
    constant_ts = _bool(payload["constantContainerTimestamps"], "constantContainerTimestamps")
    manual_pending = _bool(payload["manualTimingPending"], "manualTimingPending")
    return nominal, ae_min, ae_max, fixed, constant_ts, manual_pending, rate_class


def _rate(value: object, context: str, rate_class: str | None) -> tuple[int, int]:
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
    if rate_class == "integer" and denominator != 1:
        raise ValueError("integer nominal must have denominator 1")
    if rate_class == "fractional" and denominator == 1:
        raise ValueError("fractional nominal must not be an integer")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-05 must not yield qualified, allowed, or native_fixed_24")
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
