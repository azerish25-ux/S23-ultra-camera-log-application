"""TC-P059-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P059-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."

_REPEATS = ("none", "negative-channel", "saturated-color", "extreme-exposure")
_PAYLOAD_KEYS = (
    "channel",
    "value",
    "domainMin",
    "domainMax",
    "clippingPermitted",
    "silentClamp",
    "claimsFullRange",
    "affectedCount",
    "repeat",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "clip_recorded")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"[a-z][a-z0-9-]{0,31}")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Reject silent or unpermitted clipping and keep the original value."""
    channel, value, low, high, permitted, silent, full_range, count, repeat = _payload(payload)
    preserved = [
        "channel:" + channel,
        "value:" + value,
        "domain:" + low + ".." + high,
        f"affected-count:{count}",
        "repeat:" + repeat,
        "clipping-permitted:" + ("true" if permitted else "false"),
    ]
    numeric = Decimal(value)
    outside = numeric < Decimal(low) or numeric > Decimal(high)
    reasons = [EXPECTED, INTERVENTION]
    if silent and full_range:
        reasons.append(NEGATIVE)
        reasons.append("original value was not replaced by a silent clamp")
        return _result(
            "rejected",
            reasons,
            ["silent-clamp-full-range"],
            preserved,
            ["silent clamp was refused"],
        )
    if outside and not permitted:
        reasons.append("value is outside the delivery domain without clipping permission")
        return _result(
            "rejected",
            reasons,
            ["unconsented-clip"],
            preserved,
            ["explicit clipping policy required"],
        )
    if outside and permitted and count <= 0:
        reasons.append("authorized clipping did not record an affected count")
        return _result(
            "rejected",
            reasons,
            ["missing-affected-count"],
            preserved,
            ["affected count was not recorded"],
        )
    if outside and permitted:
        reasons.append(f"authorized clipping recorded {count} affected samples")
        return _result(
            "clip_recorded",
            reasons,
            [],
            preserved,
            ["recorded clipping is not a retained-range claim"],
        )
    reasons.append("value remains inside the selected delivery domain")
    return _result(
        "withheld",
        reasons,
        [],
        preserved,
        ["in-domain value is not ten-bit fidelity"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool, bool, int, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    channel = payload["channel"]
    if not isinstance(channel, str) or _TOKEN.fullmatch(channel) is None:
        raise ValueError("channel must be a lowercase token")
    value = _number(payload["value"], "value")
    low = _number(payload["domainMin"], "domainMin")
    high = _number(payload["domainMax"], "domainMax")
    if Decimal(low) >= Decimal(high):
        raise ValueError("domainMin must be below domainMax")
    permitted = payload["clippingPermitted"]
    silent = payload["silentClamp"]
    full_range = payload["claimsFullRange"]
    if type(permitted) is not bool or type(silent) is not bool or type(full_range) is not bool:
        raise ValueError("clipping flags must be bools")
    count = payload["affectedCount"]
    if type(count) is not int or count < 0:
        raise ValueError("affectedCount must be a non-negative int")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    return channel, value, low, high, permitted, silent, full_range, count, repeat


def _number(value: object, label: str) -> str:
    if not isinstance(value, str) or _NUMBER.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical decimal string")
    if value in {"-0"} or value.startswith("-0."):
        # "-0.2" is a canonical magnitude; reject a negative zero integer only.
        if value == "-0":
            raise ValueError(label + " must not be negative zero")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-05 must not yield qualified or allowed")
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
