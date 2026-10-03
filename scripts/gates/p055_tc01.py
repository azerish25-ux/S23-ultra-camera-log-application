"""TC-P055-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P055-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."
REPEAT = (
    "Repeat around zero, the source white reference, and the chosen output encoding boundary."
)

_LOCI = (
    "below-black",
    "around-zero",
    "source-white",
    "above-white",
    "encoding-boundary",
    "inside",
)
_LIMITS = ("storage", "display")
_CHANNELS = ("R", "G", "B")
_PAYLOAD_KEYS = (
    "sampleId",
    "channel",
    "value",
    "locus",
    "implicitClamp",
    "declaredLimit",
    "storageFloor",
    "storageCeiling",
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
    """Keep signed and over-range samples until a declared limit."""
    sample, channel, value, locus, implicit, limit, floor, ceiling = _payload(payload)
    preserved = [
        sample,
        f"channel:{channel}",
        f"value:{value}",
        f"locus:{locus}",
        f"limit:{limit}",
        f"storage:{floor}..{ceiling}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if implicit:
        decision = "rejected"
        rejected.append("implicit-zero-to-one-clamp")
        reasons.append(NEGATIVE)
        questions.append("original signed value was kept; the clamp was not applied")
    else:
        number = Decimal(value)
        if limit == "display":
            low, high = Decimal(0), Decimal(1)
            bound = "display"
        else:
            low, high = Decimal(floor), Decimal(ceiling)
            bound = "storage"
        if low <= number <= high:
            decision = "retained"
            reasons.append(f"{value} stays inside the declared {bound} limit")
        else:
            decision = "bounded"
            reasons.append(f"{value} meets the declared {bound} limit and is not an implicit clamp")
            questions.append(f"declared {bound} limit is explicit")
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
    value = payload["value"]
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError("value must be a canonical signed decimal")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    implicit = payload["implicitClamp"]
    if type(implicit) is not bool:
        raise ValueError("implicitClamp must be a bool")
    limit = payload["declaredLimit"]
    if limit not in _LIMITS:
        raise ValueError("declaredLimit must be storage or display")
    floor = payload["storageFloor"]
    ceiling = payload["storageCeiling"]
    if not isinstance(floor, str) or _SIGNED.fullmatch(floor) is None or floor == "-0":
        raise ValueError("storageFloor must be a canonical signed decimal")
    if not isinstance(ceiling, str) or _SIGNED.fullmatch(ceiling) is None or ceiling == "-0":
        raise ValueError("storageCeiling must be a canonical signed decimal")
    if Decimal(floor) >= Decimal(ceiling):
        raise ValueError("storageFloor must be below storageCeiling")
    return sample, channel, value, locus, implicit, limit, floor, ceiling


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-01 must not yield qualified or allowed")
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
