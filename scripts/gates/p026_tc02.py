"""TC-P026-02 timestamp domain confusion.

Offset one clock domain or change its origin while the numbers still look
plausible. Missing mappings stay unverified. Matching nanosecond units do
not make unrelated clocks equivalent, and the originals are not subtracted.
"""

from __future__ import annotations

CASE_ID = "TC-P026-02"
INTERVENTION = (
    "Offset one clock domain or change its origin while keeping plausible-looking numerical values."
)
EXPECTED = "Detect the missing mapping or report timing unverified instead of subtracting unrelated clocks."
NEGATIVE = "Matching numeric units alone must not establish clock equivalence."
DOMAINS = (
    "sensor",
    "audio_hardware",
    "monotonic_system",
    "encoded_presentation",
)
_PAYLOAD_KEYS = (
    "leftDomain",
    "rightDomain",
    "leftUnit",
    "rightUnit",
    "leftOrigin",
    "rightOrigin",
    "leftTimestamp",
    "rightTimestamp",
    "mappingDocumented",
    "claimsEquivalenceFromUnits",
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
    """Keep clock domains distinct. Do not subtract unrelated timestamps."""
    fields = _payload(payload)
    reasons = [
        INTERVENTION,
        f"domains {fields['leftDomain']} {fields['rightDomain']}",
        f"units {fields['leftUnit']} {fields['rightUnit']}",
    ]
    domains_differ = (
        fields["leftDomain"] != fields["rightDomain"] or fields["leftOrigin"] != fields["rightOrigin"]
    )
    units_match = fields["leftUnit"] == fields["rightUnit"]
    rejected: list[str] = []
    if fields["claimsEquivalenceFromUnits"] and units_match and domains_differ:
        rejected.append("unit-equivalence")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
    elif domains_differ and fields["mappingDocumented"]:
        decision = "mapping_recorded"
        reasons.append("documented mapping recorded; unrelated clocks were not subtracted")
    elif domains_differ:
        decision = "timing_unverified"
        reasons.append(EXPECTED)
        reasons.append("unrelated clocks were not subtracted")
    else:
        decision = "same_domain"
        reasons.append("both timestamps already share a domain and origin")
    preserved = [
        f"{fields['leftDomain']}:{fields['leftTimestamp']}",
        f"{fields['rightDomain']}:{fields['rightTimestamp']}",
    ]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    left = payload["leftDomain"]
    right = payload["rightDomain"]
    if left not in DOMAINS or right not in DOMAINS:
        raise ValueError("domain is not a declared repeat")
    return {
        "leftDomain": left,
        "rightDomain": right,
        "leftUnit": _unit(payload["leftUnit"], "leftUnit"),
        "rightUnit": _unit(payload["rightUnit"], "rightUnit"),
        "leftOrigin": _token(payload["leftOrigin"], "leftOrigin"),
        "rightOrigin": _token(payload["rightOrigin"], "rightOrigin"),
        "leftTimestamp": _stamp(payload["leftTimestamp"], "leftTimestamp"),
        "rightTimestamp": _stamp(payload["rightTimestamp"], "rightTimestamp"),
        "mappingDocumented": _bool(payload["mappingDocumented"], "mappingDocumented"),
        "claimsEquivalenceFromUnits": _bool(
            payload["claimsEquivalenceFromUnits"], "claimsEquivalenceFromUnits"
        ),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _unit(value: object, name: str) -> str:
    if value not in {"ns", "us"}:
        raise ValueError(f"{name} must be ns or us")
    return value


def _stamp(value: object, name: str) -> str:
    text = _token(value, name)
    if text != "0" and (not text.isdigit() or text[0] == "0"):
        raise ValueError(f"{name} must be a canonical non-negative integer string")
    if not text.isdigit():
        raise ValueError(f"{name} must be a canonical non-negative integer string")
    return text


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-02 must not yield qualified or allowed")
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
