"""TC-P063-05 unconsented clipping.

Values outside the delivery domain need an explicit clipping policy and an
affected count when clipping is authorized. A silent clamp that claims full
retained range fails. This host case does not qualify a physical S23.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P063-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."
REPEAT = "Repeat with negative channels, saturated colors, and extreme exposure adjustments."

_CHANNELS = ("R", "G", "B")
_LOCI = ("negative", "saturated", "extreme-exposure", "highlight")
_PAYLOAD_KEYS = (
    "sampleId",
    "channel",
    "value",
    "domainFloor",
    "domainCeiling",
    "clippingPermitted",
    "silentClamp",
    "claimsFullRange",
    "affectedCount",
    "locus",
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
_UINT = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Request a clipping policy, or reject a silent full-range clamp."""
    (
        sample,
        channel,
        value,
        floor,
        ceiling,
        permitted,
        silent,
        claims_full,
        affected,
        locus,
    ) = _payload(payload)
    preserved = [
        sample,
        f"channel:{channel}",
        f"value:{value}",
        f"domain:{floor}..{ceiling}",
        f"locus:{locus}",
        f"affected:{affected}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    number = Decimal(value)
    outside = number < Decimal(floor) or number > Decimal(ceiling)
    if silent and claims_full:
        decision = "rejected"
        rejected = ["silent-clamp-full-range"]
        reasons.append(NEGATIVE)
        questions.append(f"original value {value} was kept; the clamp was not applied")
    elif silent:
        decision = "rejected"
        rejected = ["silent-clamp"]
        reasons.append("silent clamping without a recorded policy was rejected")
        questions.append(f"original value {value} was kept")
    elif outside and not permitted:
        decision = "policy_required"
        rejected = ["unconsented-out-of-domain"]
        reasons.append(f"{value} is outside {floor}..{ceiling} without clipping permission")
        questions.append("an explicit clipping policy is required")
    elif outside and permitted:
        if affected == "0":
            decision = "rejected"
            rejected = ["missing-affected-count"]
            reasons.append("authorized clipping without an affected count was rejected")
        else:
            decision = "clip_recorded"
            rejected = []
            reasons.append(f"authorized clipping recorded affected count {affected}")
            questions.append("clip_recorded is not full retained range and not qualification")
    else:
        decision = "in_domain"
        rejected = []
        reasons.append(f"{value} is inside the delivery domain")
        questions.append("in-domain is not qualification")
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
    value = _signed(payload["value"], "value")
    floor = _signed(payload["domainFloor"], "domainFloor")
    ceiling = _signed(payload["domainCeiling"], "domainCeiling")
    if Decimal(floor) >= Decimal(ceiling):
        raise ValueError("domainFloor must be below domainCeiling")
    permitted = payload["clippingPermitted"]
    silent = payload["silentClamp"]
    claims_full = payload["claimsFullRange"]
    for name, flag in (
        ("clippingPermitted", permitted),
        ("silentClamp", silent),
        ("claimsFullRange", claims_full),
    ):
        if type(flag) is not bool:
            raise ValueError(f"{name} must be a bool")
    affected = payload["affectedCount"]
    if not isinstance(affected, str) or _UINT.fullmatch(affected) is None:
        raise ValueError("affectedCount must be a canonical non-negative integer string")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    return sample, channel, value, floor, ceiling, permitted, silent, claims_full, affected, locus


def _signed(value: object, label: str) -> str:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(f"{label} must be a canonical signed decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-05 must not yield qualified or allowed")
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
