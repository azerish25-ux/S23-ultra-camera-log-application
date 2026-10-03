"""TC-P027-04 codec output contradicts the request.

An actual stream may differ in depth, dimensions, transfer tags, or tracks.
The output contract fails and useful media stays under an accurate status.
Trusting only configure parameters must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-04"
INTERVENTION = (
    "Emit an actual stream with different depth, dimensions, transfer tags, or selected "
    "tracks than requested."
)
EXPECTED = "Fail the corresponding output contract while retaining useful media under an accurate status."
NEGATIVE = "Trusting only configure parameters must fail."
CONTRADICTIONS = (
    "eight-bit-after-ten-bit",
    "wrong-color-range",
    "wrong-dimensions",
    "wrong-tracks",
)
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_PAYLOAD_KEYS = {
    "contradiction",
    "trustConfigureOnly",
    "usefulMedia",
    "accurateStatus",
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
    """Fail the output contract. Keep the useful media identity."""
    data = _payload(payload)
    reasons = [f"contradiction {data['contradiction']}", INTERVENTION]
    preserved = [data["usefulMedia"], data["contradiction"]]
    rejected: list[str] = []
    if data["trustConfigureOnly"]:
        rejected.append("configure-parameters-trusted")
        reasons.append(NEGATIVE)
    if not data["accurateStatus"]:
        rejected.append("inaccurate-status")
        reasons.append("useful media was not kept under an accurate status")
    if rejected:
        decision = "rejected"
    else:
        decision = "contract_failed"
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    contradiction = payload["contradiction"]
    if contradiction not in CONTRADICTIONS:
        raise ValueError("contradiction is not a declared output mismatch")
    media = payload["usefulMedia"]
    if not isinstance(media, str) or _TOKEN.fullmatch(media) is None:
        raise ValueError("usefulMedia must be a token")
    return {
        "contradiction": contradiction,
        "trustConfigureOnly": _bool(payload["trustConfigureOnly"], "trustConfigureOnly"),
        "usefulMedia": media,
        "accurateStatus": _bool(payload["accurateStatus"], "accurateStatus"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-04 must not yield qualified or allowed")
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
