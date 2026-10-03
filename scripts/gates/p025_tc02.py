"""TC-P025-02 timestamp domain confusion.

Intervention: Offset one clock domain or change its origin while keeping
plausible-looking numerical values.
Expected: Detect the missing mapping or report timing unverified instead of
subtracting unrelated clocks.
Negative: Matching numeric units alone must not establish clock equivalence.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P025-02"
INTERVENTION = (
    "Offset one clock domain or change its origin while keeping plausible-looking numerical values."
)
EXPECTED = (
    "Detect the missing mapping or report timing unverified instead of subtracting unrelated clocks."
)
NEGATIVE = "Matching numeric units alone must not establish clock equivalence."

_DOMAINS = (
    "sensor",
    "audio_hardware",
    "monotonic_system",
    "encoded_presentation",
    "codec",
)
_UNITS = ("ns", "us", "ms", "s")
_METHODS = ("none", "measured_offset", "documented_epoch", "numeric_units_only")
_CANONICAL = re.compile(r"0|[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "leftDomain",
    "rightDomain",
    "leftUnits",
    "rightUnits",
    "leftValue",
    "rightValue",
    "leftOrigin",
    "rightOrigin",
    "mappingMethod",
    "retainedSamples",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "unverified", "correspondence_estimated")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Report unverified timing instead of subtracting unrelated clocks."""
    (
        left_domain,
        right_domain,
        left_units,
        right_units,
        left_value,
        right_value,
        left_origin,
        right_origin,
        method,
        retained,
    ) = _payload(payload)
    preserved = [
        f"{left_domain}:{left_origin}:{left_value}{left_units}",
        f"{right_domain}:{right_origin}:{right_value}{right_units}",
    ]
    units_match = left_units == right_units
    identified = method in {"measured_offset", "documented_epoch"} and retained >= 2

    if method == "numeric_units_only":
        decision = "rejected"
        rejected = ["numeric-unit-equivalence", "unrelated-domain-subtraction"]
        questions = ["timing unverified"]
        reasons = [NEGATIVE, EXPECTED, "numeric units were not subtracted"]
    elif identified:
        decision = "correspondence_estimated"
        rejected = []
        questions = ["physical synchronization unverified"]
        reasons = [
            f"identified method {method} retained {retained} samples",
            "the estimate does not equate the two clock domains",
            "original timestamps and origins are preserved",
        ]
    else:
        decision = "unverified"
        rejected = ["numeric-unit-equivalence"] if units_match else ["missing-mapping"]
        if left_origin != right_origin:
            rejected.append("origin-changed")
        questions = ["timing unverified"]
        reasons = [EXPECTED, "missing mapping; unrelated clocks were not subtracted"]
        if left_origin != right_origin:
            reasons.append("a changed origin keeps the numerical values from establishing equivalence")

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, str, str, str, str, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    left_domain = _choice(payload["leftDomain"], _DOMAINS, "leftDomain")
    right_domain = _choice(payload["rightDomain"], _DOMAINS, "rightDomain")
    if left_domain == right_domain:
        raise ValueError("clock domains must differ")
    left_units = _choice(payload["leftUnits"], _UNITS, "leftUnits")
    right_units = _choice(payload["rightUnits"], _UNITS, "rightUnits")
    left_value = _uint(payload["leftValue"], "leftValue")
    right_value = _uint(payload["rightValue"], "rightValue")
    left_origin = _text(payload["leftOrigin"], "leftOrigin")
    right_origin = _text(payload["rightOrigin"], "rightOrigin")
    method = _choice(payload["mappingMethod"], _METHODS, "mappingMethod")
    retained = payload["retainedSamples"]
    if type(retained) is not int or retained < 0:
        raise ValueError("retainedSamples must be a non-negative int")
    return (
        left_domain,
        right_domain,
        left_units,
        right_units,
        left_value,
        right_value,
        left_origin,
        right_origin,
        method,
        retained,
    )


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} is not an allowed value")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _uint(value: object, label: str) -> str:
    if not isinstance(value, str) or _CANONICAL.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative integer string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("domain decision cannot be qualified or allowed")
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
