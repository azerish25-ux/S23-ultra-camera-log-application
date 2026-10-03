"""TC-P058-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P058-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."

_CHANNELS = ("highlight", "negative", "saturated", "exposure", "mid")
_PAYLOAD_KEYS = (
    "domainMin",
    "domainMax",
    "sample",
    "channel",
    "clippingPermitted",
    "silentClamp",
    "claimsFullRange",
    "affectedCount",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Reject silent full-range clamps and unconsented out-of-domain samples."""
    low, high, sample, channel, permitted, silent, full_range, affected = _payload(payload)
    preserved = [
        f"domain:{low}..{high}",
        f"sample:{sample}",
        f"channel:{channel}",
        "clipping:" + ("permitted" if permitted else "denied"),
        "silent-clamp:" + ("true" if silent else "false"),
        "claims-full-range:" + ("true" if full_range else "false"),
        f"affected:{affected}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions: list[str] = []
    outside = Decimal(sample) < Decimal(low) or Decimal(sample) > Decimal(high)
    if channel == "negative":
        reasons.append("negative channel retained")
    if channel == "saturated":
        reasons.append("saturated color retained")
    if channel == "exposure":
        reasons.append("extreme exposure adjustment retained")
    if silent and full_range:
        decision = "rejected"
        rejected.append("silent-clamp-full-range")
        reasons.append(NEGATIVE)
        questions.append("full retained range was claimed after a silent clamp")
    elif outside and not permitted:
        decision = "rejected"
        rejected.append("unconsented-out-of-domain")
        reasons.append("explicit clipping policy required")
        questions.append("explicit clipping policy required")
    elif outside and permitted:
        if affected < 1:
            decision = "rejected"
            rejected.append("missing-affected-count")
            reasons.append("authorized clipping without an affected count was rejected")
        elif full_range:
            decision = "rejected"
            rejected.append("full-range-claim")
            reasons.append("authorized clipping cannot claim a full retained range")
        else:
            decision = "clip_recorded"
            reasons.append(f"authorized clipping recorded affected count {affected}")
            questions.append("recorded clipping is not a retained full range")
    else:
        decision = "inside_domain"
        reasons.append("sample is inside the delivery domain")
        questions.append("an inside sample is not a qualified delivery")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    low = payload["domainMin"]
    high = payload["domainMax"]
    sample = payload["sample"]
    for name, value in (("domainMin", low), ("domainMax", high), ("sample", sample)):
        if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
            raise ValueError(name + " must be a canonical decimal")
    if Decimal(low) >= Decimal(high):
        raise ValueError("domainMin must be below domainMax")
    channel = payload["channel"]
    if channel not in _CHANNELS:
        raise ValueError("channel is unsupported")
    permitted = payload["clippingPermitted"]
    silent = payload["silentClamp"]
    full_range = payload["claimsFullRange"]
    for name, value in (
        ("clippingPermitted", permitted),
        ("silentClamp", silent),
        ("claimsFullRange", full_range),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    affected = payload["affectedCount"]
    if type(affected) is not int or affected < 0:
        raise ValueError("affectedCount must be a non-negative int")
    return low, high, sample, channel, permitted, silent, full_range, affected


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-05 must not yield qualified or allowed")
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
