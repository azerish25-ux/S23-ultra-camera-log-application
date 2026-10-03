"""TC-P062-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P062-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."
REPEAT = "Repeat with negative channels, saturated colors, and extreme exposure adjustments."

_CHANNELS = ("R", "G", "B")
_LOCI = ("highlight", "negative", "saturated", "extreme-exposure", "inside")
_PAYLOAD_KEYS = (
    "sampleId",
    "channel",
    "value",
    "locus",
    "domainFloor",
    "domainCeiling",
    "clippingPermitted",
    "silentClamp",
    "claimsFullRange",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Reject silent full-range clamps; record an authorized clip count."""
    sample, channel, value, locus, floor, ceiling, permitted, silent, full_range = _payload(payload)
    number = Decimal(value)
    outside = number < Decimal(floor) or number > Decimal(ceiling)
    dishonest = outside and (silent or full_range)
    authorized = outside and permitted and not silent and not full_range
    affected = "1" if authorized else "0"
    preserved = [
        sample,
        f"channel:{channel}",
        f"value:{value}",
        f"locus:{locus}",
        f"domain:{floor}..{ceiling}",
        f"affected:{affected}",
        "full-range-claim:" + ("yes" if full_range else "no"),
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT]
    if dishonest:
        rejected.append("silent-clamp-full-range")
        reasons.append(NEGATIVE)
        reasons.append(f"value {value} was not replaced; full retained range was not established")
        decision = "rejected"
    elif outside and not permitted:
        rejected.append("clipping-policy-required")
        reasons.append(f"value {value} is outside {floor}..{ceiling} without clipping permission")
        questions.append("explicit clipping policy required")
        decision = "rejected"
    elif authorized:
        reasons.append(f"authorized clip affected {affected} channel; original {value} was retained in the inventory")
        decision = "clipped_recorded"
    else:
        reasons.append(f"value {value} stays inside {floor}..{ceiling}")
        decision = "retained"
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    channel = payload["channel"]
    if channel not in _CHANNELS:
        raise ValueError("channel must be R, G, or B")
    value = _decimal(payload["value"], "value")
    floor = _decimal(payload["domainFloor"], "domainFloor")
    ceiling = _decimal(payload["domainCeiling"], "domainCeiling")
    if Decimal(floor) >= Decimal(ceiling):
        raise ValueError("domainFloor must be below domainCeiling")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    number = Decimal(value)
    low, high = Decimal(floor), Decimal(ceiling)
    if locus == "inside" and not low <= number <= high:
        raise ValueError("inside locus must lie in the domain")
    if locus == "negative" and number >= 0:
        raise ValueError("negative locus requires a negative value")
    if locus == "highlight" and number <= high:
        raise ValueError("highlight locus must exceed the domain ceiling")
    if locus == "saturated" and number <= high:
        raise ValueError("saturated locus must exceed the domain ceiling")
    if locus == "extreme-exposure" and number < 4:
        raise ValueError("extreme-exposure locus requires a value of at least 4")
    for name in ("clippingPermitted", "silentClamp", "claimsFullRange"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
    return (
        sample,
        channel,
        value,
        locus,
        floor,
        ceiling,
        payload["clippingPermitted"],
        payload["silentClamp"],
        payload["claimsFullRange"],
    )


def _decimal(value: object, name: str) -> str:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(name + " must be a canonical signed decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-05 must not yield qualified or allowed")
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
