"""TC-P064-05 unconsented clipping.

Intervention: Supply encoded or intermediate values outside the selected
delivery domain without clipping permission.
Expected: Reject or request an explicit clipping policy and record affected
counts when clipping is authorized.
Negative: Silently clamping highlights while claiming full retained range must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P064-05"
INTERVENTION = (
    "Supply encoded or intermediate values outside the selected delivery domain without clipping permission."
)
EXPECTED = (
    "Reject or request an explicit clipping policy and record affected counts when clipping is authorized."
)
NEGATIVE = "Silently clamping highlights while claiming full retained range must fail."
REPEAT = "Repeat with negative channels, saturated colors, and extreme exposure adjustments."

_LOCI = ("highlight", "negative-channel", "saturated-color", "extreme-exposure", "inside")
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_PAYLOAD_KEYS = (
    "sampleId",
    "locus",
    "outsideDomain",
    "clippingPermission",
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


def evaluate(payload: dict) -> dict:
    """Request a clipping policy, or record an authorized count. Never silent-clamp."""
    sample, locus, outside, permission, silent, full_range, count = _payload(payload)
    preserved = [
        sample,
        f"locus:{locus}",
        f"outside:{_flag(outside)}",
        f"permission:{_flag(permission)}",
        f"silent-clamp:{_flag(silent)}",
        f"claims-full-range:{_flag(full_range)}",
        f"affected-count:{count}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT]
    rejected: list[str] = []
    if silent and full_range:
        rejected.append("silent-clamp-full-range")
        reasons.append(NEGATIVE)
        questions.append("original sample was kept; the silent clamp was not accepted")
        decision = "rejected"
    elif outside and not permission:
        rejected.append("unconsented-out-of-domain")
        reasons.append("explicit clipping policy required")
        questions.append("explicit clipping policy required")
        decision = "policy_required"
    elif outside and permission:
        if count <= 0:
            rejected.append("missing-affected-count")
            reasons.append("authorized clipping needs a recorded affected count")
            decision = "rejected"
        else:
            reasons.append(f"authorized clipping recorded affected count {count}")
            questions.append("recorded count is not retained-range certification")
            decision = "clipped_recorded"
    elif silent:
        rejected.append("silent-clamp")
        reasons.append("silent clamp without a full-range claim is still unconsented")
        decision = "rejected"
    else:
        reasons.append("sample is inside the delivery domain")
        decision = "withheld"
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
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
    outside = payload["outsideDomain"]
    permission = payload["clippingPermission"]
    silent = payload["silentClamp"]
    full_range = payload["claimsFullRange"]
    for name, value in (
        ("outsideDomain", outside),
        ("clippingPermission", permission),
        ("silentClamp", silent),
        ("claimsFullRange", full_range),
    ):
        if type(value) is not bool:
            raise ValueError(name + " must be a bool")
    if locus == "inside" and outside:
        raise ValueError("inside locus cannot be outside the domain")
    if locus != "inside" and not outside:
        raise ValueError("named outside loci must be outside the domain")
    count = payload["affectedCount"]
    if type(count) is not int or isinstance(count, bool) or count < 0:
        raise ValueError("affectedCount must be a non-negative int")
    return sample, locus, outside, permission, silent, full_range, count


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-05 must not yield qualified or allowed")
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
