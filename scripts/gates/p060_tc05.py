"""TC-P060-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P060-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."
REPEAT = "Repeat with negative channels, saturated colors, and extreme exposure adjustments."

_DOMAINS = ("limited-10", "full-10", "scene-linear")
_CODE_CHANNELS = ("Y", "Cb", "Cr")
_SCENE_CHANNELS = ("R", "G", "B")
_LOCI = ("highlight", "negative", "saturated", "extreme-exposure", "inside")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_PAYLOAD_KEYS = (
    "domain",
    "channel",
    "value",
    "clippingPermission",
    "claimFullRange",
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


def _limits(domain: str, channel: str) -> tuple[Decimal, Decimal]:
    if domain == "scene-linear":
        return Decimal(0), Decimal(1)
    if domain == "full-10":
        return Decimal(0), Decimal(1023)
    if channel == "Y":
        return Decimal(64), Decimal(940)
    return Decimal(64), Decimal(960)


def _canonical(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def evaluate(payload: dict) -> dict:
    """Reject unconsented clipping and a silent full-range claim."""
    domain, channel, value_text, value, permission, claim, locus = _payload(payload)
    low, high = _limits(domain, channel)
    outside = value < low or value > high
    clamped = min(high, max(low, value))
    preserved = [
        f"domain:{domain}",
        f"channel:{channel}",
        f"value:{value_text}",
        f"locus:{locus}",
        f"limits:{_canonical(low)}..{_canonical(high)}",
        f"permission:{'yes' if permission else 'no'}",
        f"claim-full-range:{'yes' if claim else 'no'}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"locus {locus} value {value_text}"]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if not outside:
        preserved.append("affected:0")
        preserved.append(f"stored:{value_text}")
        reasons.append(f"{value_text} is inside the selected delivery domain")
        decision = "retained"
    elif not permission:
        preserved.append("affected:0")
        preserved.append(f"stored:{value_text}")
        rejected.append("unconsented-clip")
        reasons.append("an explicit clipping policy is required")
        questions.append("value was not clamped")
        decision = "rejected"
    else:
        preserved.append("affected:1")
        preserved.append(f"stored:{value_text}")
        preserved.append(f"clamped:{_canonical(clamped)}")
        if claim:
            rejected.append("silent-full-range-claim")
            reasons.append(NEGATIVE)
            decision = "rejected"
        else:
            reasons.append("clipping was authorized and the affected count was recorded")
            decision = "clipped"
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    domain = payload["domain"]
    if domain not in _DOMAINS:
        raise ValueError("domain is unsupported")
    channel = payload["channel"]
    allowed = _SCENE_CHANNELS if domain == "scene-linear" else _CODE_CHANNELS
    if channel not in allowed:
        raise ValueError("channel is not valid for the domain")
    value_text = payload["value"]
    if not isinstance(value_text, str) or _SIGNED.fullmatch(value_text) is None or value_text == "-0":
        raise ValueError("value must be a canonical signed decimal")
    if domain != "scene-linear" and ("." in value_text or value_text.startswith("-")):
        raise ValueError("ten-bit domains use canonical non-negative integers")
    value = Decimal(value_text)
    permission = payload["clippingPermission"]
    claim = payload["claimFullRange"]
    if type(permission) is not bool or type(claim) is not bool:
        raise ValueError("clipping flags must be bools")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    low, high = _limits(domain, channel)
    outside = value < low or value > high
    if locus == "inside" and outside:
        raise ValueError("inside locus must be inside the domain")
    if locus != "inside" and not outside:
        raise ValueError("this locus must be outside the domain")
    if locus == "negative" and value >= 0:
        raise ValueError("negative locus requires a negative value")
    return domain, channel, value_text, value, permission, claim, locus


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-05 must not yield qualified or allowed")
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
