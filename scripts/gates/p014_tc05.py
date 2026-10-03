"""TC-P014-05 ambiguous timing on an high-resolution experiment matrix.

Timing arrays are constraints. A variable AE range that merely includes a
nominal frame rate is not fixed cadence, and constant container timestamps
must not upgrade variable sensor timing. Advertised sizes stay preserved.
"""

from __future__ import annotations

CASE_ID = "TC-P014-05"
INTERVENTION = (
    "Offer a variable AE range that includes the desired nominal frame rate but no fixed-rate evidence."
)
EXPECTED = (
    "Keep the rate strategy explicit and withhold native fixed-cadence certification "
    "pending measured results."
)
NEGATIVE = (
    "Assigning constant container timestamps must not upgrade variable sensor "
    "timing into native cadence."
)
_PAYLOAD_KEYS = (
    "nominalFps",
    "aeRangeIncludesNominal",
    "fixedRateEvidence",
    "constantContainerTimestamps",
    "manualTimingPending",
    "rateClass",
    "advertisedSize",
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


def evaluate(payload: dict) -> dict:
    """Withhold fixed cadence unless fixed-rate evidence is actually present."""
    nominal, ae_includes, fixed, constant_ts, manual_pending, rate_class, advertised = _payload(
        payload
    )
    reasons = [f"rate strategy {rate_class} nominal {nominal}"]
    rejected: list[str] = []
    open_questions: list[str] = []

    if constant_ts:
        rejected.append(_CONSTANT_TIMESTAMPS)
        reasons.append(
            "constant container timestamps do not upgrade variable sensor timing"
        )
    if ae_includes and not fixed:
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

    if decision in {"qualified", "allowed", "fixed_cadence"} and not fixed:
        raise ValueError("variable timing must not yield qualified, allowed, or fixed cadence")
    if constant_ts and not fixed and decision in {"qualified", "allowed", "fixed_cadence"}:
        raise ValueError("constant container timestamps must not upgrade variable sensor timing")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P014-05 must not yield qualified or allowed")

    preserved = [nominal, advertised]
    if advertised not in preserved or nominal not in preserved:
        raise ValueError("nominal fps and advertised size must be preserved")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[str, bool, bool, bool, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    rate_class = payload["rateClass"]
    if rate_class not in _RATE_CLASSES:
        raise ValueError("rateClass must be integer or fractional")
    nominal = _nominal_fps(payload["nominalFps"], rate_class)
    advertised = _advertised_size(payload["advertisedSize"])
    return (
        nominal,
        _bool(payload["aeRangeIncludesNominal"], "aeRangeIncludesNominal"),
        _bool(payload["fixedRateEvidence"], "fixedRateEvidence"),
        _bool(payload["constantContainerTimestamps"], "constantContainerTimestamps"),
        _bool(payload["manualTimingPending"], "manualTimingPending"),
        rate_class,
        advertised,
    )


def _nominal_fps(value: object, rate_class: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("nominalFps must be a non-empty string")
    if rate_class == "integer":
        if not _digits(value) or value[0] == "0":
            raise ValueError("integer nominalFps must be a canonical positive integer string")
        return value
    whole, dot, frac = value.partition(".")
    if (
        dot != "."
        or not _digits(whole)
        or whole[0] == "0"
        or not _digits(frac)
        or frac[-1] == "0"
    ):
        raise ValueError("fractional nominalFps must be a canonical non-integer decimal string")
    return value


def _advertised_size(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("advertisedSize must be a string")
    width, sep, height = value.partition("x")
    if sep != "x" or not _digits(width) or width[0] == "0" or not _digits(height) or height[0] == "0":
        raise ValueError("advertisedSize must look like 3840x2160")
    return value


def _digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision != "allowed" and not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
