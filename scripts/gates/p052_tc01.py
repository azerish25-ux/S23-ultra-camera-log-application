"""TC-P052-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P052-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_LOCI = ("around-zero", "source-white", "encoding-boundary")
_PAYLOAD_KEYS = (
    "sampleId",
    "locus",
    "value",
    "stored",
    "unitClamped",
    "storageLimit",
    "displayLimit",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range samples until the declared storage limit."""
    sample, locus, value, stored, unit_clamped, storage, display = _payload(payload)
    number = Decimal(value)
    kept = Decimal(stored)
    limit = Decimal(storage)
    shown = Decimal(display)
    expected = number if abs(number) <= limit else (limit if number > 0 else -limit)
    preserved = [
        f"sample:{sample}",
        f"locus:{locus}",
        f"value:{value}",
        f"stored:{stored}",
        f"storage-limit:{storage}",
        f"display-limit:{display}",
        f"expected:{_canon(expected)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = ["signed and over-range values stay in the inventory"]
    unit_hit = unit_clamped or (
        (number < 0 or number > 1)
        and kept == (Decimal(0) if number < 0 else Decimal(1))
        and kept != expected
    )
    early_display = (
        not unit_hit
        and shown < limit
        and abs(number) <= limit
        and abs(number) > shown
        and kept == (shown if number > 0 else -shown)
        and kept != expected
    )
    if unit_hit:
        decision = "rejected"
        rejected.append("implicit-unit-clamp")
        reasons.append(NEGATIVE)
        questions.append("implicit zero-to-one clamp rejected")
    elif early_display:
        decision = "rejected"
        rejected.append("early-display-clamp")
        reasons.append("display limit was applied before the declared storage boundary")
    elif kept != expected:
        decision = "rejected"
        rejected.append("storage-mismatch")
        reasons.append("stored value missed the declared storage limit")
    else:
        decision = "preserved"
        reasons.append("value kept until the declared storage limit")
        questions.append("preserved intermediate is not a physical S23 measurement")
    return _result(decision, reasons, rejected, preserved, questions)


def _canon(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _payload(payload: object) -> tuple[str, str, str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    value = payload["value"]
    stored = payload["stored"]
    for name, item in (("value", value), ("stored", stored)):
        if not isinstance(item, str) or _SIGNED.fullmatch(item) is None or item == "-0":
            raise ValueError(f"{name} must be a canonical signed decimal")
    unit_clamped = payload["unitClamped"]
    if type(unit_clamped) is not bool:
        raise ValueError("unitClamped must be a bool")
    storage = payload["storageLimit"]
    display = payload["displayLimit"]
    for name, item in (("storageLimit", storage), ("displayLimit", display)):
        if not isinstance(item, str) or _DECIMAL.fullmatch(item) is None:
            raise ValueError(f"{name} must be a canonical decimal")
        if Decimal(item) <= 0:
            raise ValueError(f"{name} must be positive")
    return sample, locus, value, stored, unit_clamped, storage, display


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-01 must not yield qualified or allowed")
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
