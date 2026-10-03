"""TC-P027-02 timestamp domain confusion.

Offset one clock domain or change its origin while keeping plausible numbers.
Missing mappings stay unverified. Matching numeric units alone must not
establish clock equivalence.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-02"
INTERVENTION = (
    "Offset one clock domain or change its origin while keeping plausible-looking numerical values."
)
EXPECTED = (
    "Detect the missing mapping or report timing unverified instead of subtracting unrelated clocks."
)
NEGATIVE = "Matching numeric units alone must not establish clock equivalence."
DOMAINS = ("sensor", "audio_hardware", "monotonic_system", "encoded_presentation")
UNITS = ("ns", "us", "ms", "s")
_NUM = re.compile(r"0|[1-9][0-9]*")
_PAYLOAD_KEYS = {
    "leftDomain",
    "rightDomain",
    "leftUnits",
    "rightUnits",
    "leftValue",
    "rightValue",
    "originChanged",
    "mappingPresent",
    "subtractedUnrelated",
    "claimsEquivalence",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Refuse equivalence from units alone. Keep both numeric values."""
    data = _payload(payload)
    reasons = [
        f"domains {data['leftDomain']} and {data['rightDomain']}",
        f"units {data['leftUnits']} and {data['rightUnits']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    if data["subtractedUnrelated"]:
        rejected.append("unrelated-clock-subtraction")
        reasons.append("unrelated clocks were subtracted")
    if data["claimsEquivalence"] and not data["mappingPresent"]:
        rejected.append("numeric-units-not-equivalence")
        reasons.append(NEGATIVE)
    preserved = [
        data["leftDomain"],
        data["rightDomain"],
        data["leftValue"],
        data["rightValue"],
    ]
    if rejected:
        decision = "rejected"
    elif not data["mappingPresent"]:
        decision = "unverified"
        reasons.append(EXPECTED)
    else:
        decision = "mapped"
        reasons.append("identified mapping retained; numeric units alone were not treated as equivalence")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    left = payload["leftDomain"]
    right = payload["rightDomain"]
    if left not in DOMAINS or right not in DOMAINS:
        raise ValueError("domain is not a declared clock")
    origin = _bool(payload["originChanged"], "originChanged")
    if left == right and not origin:
        raise ValueError("same domain requires an origin change")
    left_units = payload["leftUnits"]
    right_units = payload["rightUnits"]
    if left_units not in UNITS or right_units not in UNITS:
        raise ValueError("units must be ns, us, ms, or s")
    return {
        "leftDomain": left,
        "rightDomain": right,
        "leftUnits": left_units,
        "rightUnits": right_units,
        "leftValue": _number(payload["leftValue"], "leftValue"),
        "rightValue": _number(payload["rightValue"], "rightValue"),
        "originChanged": origin,
        "mappingPresent": _bool(payload["mappingPresent"], "mappingPresent"),
        "subtractedUnrelated": _bool(payload["subtractedUnrelated"], "subtractedUnrelated"),
        "claimsEquivalence": _bool(payload["claimsEquivalence"], "claimsEquivalence"),
    }


def _number(value: object, name: str) -> str:
    if not isinstance(value, str) or _NUM.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical non-negative integer string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-02 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
