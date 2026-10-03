"""TC-P062-08 consumer round-trip discrepancy.

Intervention: Decode or import the accepted file in an independent consumer
using the documented settings.
Expected: Match the declared numeric and visual reference within the stated
codec and transform tolerance.
Negative: Successful file opening alone must not count as interoperability.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P062-08"
INTERVENTION = "Decode or import the accepted file in an independent consumer using the documented settings."
EXPECTED = "Match the declared numeric and visual reference within the stated codec and transform tolerance."
NEGATIVE = "Successful file opening alone must not count as interoperability."
REPEAT = "Repeat with exact consumer versions, range settings, and sidecar availability."

_RANGES = ("full", "video")
_PAYLOAD_KEYS = (
    "sampleId",
    "consumer",
    "consumerVersion",
    "rangeSetting",
    "sidecarAvailable",
    "opened",
    "compared",
    "numericDelta",
    "tolerance",
    "visualMatch",
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
_VERSION = re.compile(r"^[A-Za-z0-9._+-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Require a compared round trip; opening the file is not enough."""
    fields = _payload(payload)
    delta = Decimal(fields["numericDelta"])
    tolerance = Decimal(fields["tolerance"])
    numeric_ok = delta <= tolerance
    preserved = [
        fields["sampleId"],
        f"consumer:{fields['consumer']}",
        f"version:{fields['consumerVersion']}",
        f"range:{fields['rangeSetting']}",
        f"sidecar:{'yes' if fields['sidecarAvailable'] else 'no'}",
        f"opened:{'yes' if fields['opened'] else 'no'}",
        f"compared:{'yes' if fields['compared'] else 'no'}",
        f"delta:{fields['numericDelta']}",
        f"tolerance:{fields['tolerance']}",
        f"visual:{'yes' if fields['visualMatch'] else 'no'}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT]
    if not fields["opened"]:
        rejected.append("round-trip-not-run")
        reasons.append("the independent consumer did not open the file")
        decision = "rejected"
    elif not fields["compared"]:
        rejected.append("open-is-not-interop")
        reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        if not numeric_ok:
            rejected.append("outside-tolerance")
            reasons.append(f"delta {fields['numericDelta']} exceeds tolerance {fields['tolerance']}")
        if not fields["visualMatch"]:
            rejected.append("visual-mismatch")
            reasons.append("visual reference did not match")
        if rejected:
            decision = "rejected"
        elif not fields["sidecarAvailable"]:
            decision = "withheld"
            reasons.append("numeric and visual references matched but the sidecar was unavailable")
            questions.append("sidecar availability is unresolved")
        else:
            decision = "within_tolerance"
            reasons.append(
                f"delta {fields['numericDelta']} is within tolerance {fields['tolerance']} for {fields['consumerVersion']}"
            )
            reasons.append("within tolerance is not interoperability qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    if not isinstance(payload["sampleId"], str) or _TOKEN.fullmatch(payload["sampleId"]) is None:
        raise ValueError("sampleId must be a token")
    if not isinstance(payload["consumer"], str) or _TOKEN.fullmatch(payload["consumer"]) is None:
        raise ValueError("consumer must be a token")
    if not isinstance(payload["consumerVersion"], str) or _VERSION.fullmatch(payload["consumerVersion"]) is None:
        raise ValueError("consumerVersion must be a version token")
    if payload["rangeSetting"] not in _RANGES:
        raise ValueError("rangeSetting is unsupported")
    for name in ("sidecarAvailable", "opened", "compared", "visualMatch"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
    _decimal(payload["numericDelta"], "numericDelta")
    _decimal(payload["tolerance"], "tolerance")
    if Decimal(payload["tolerance"]) < 0:
        raise ValueError("tolerance must be non-negative")
    return payload


def _decimal(value: object, name: str) -> None:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(name + " must be a canonical non-negative decimal")


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-08 must not yield qualified or allowed")
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
