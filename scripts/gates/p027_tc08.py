"""TC-P027-08 physical sync disagreement.

Packet starts may align while a measured visible-audible offset remains.
Container timing and physical synchronization stay distinct, and the sync
gate fails. A packet-only lip-sync certificate must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-08"
INTERVENTION = (
    "Provide aligned packet starts but a measured visible-audible event offset or drift "
    "in the actual recording."
)
EXPECTED = (
    "Keep container timing and physical synchronization as distinct results and fail the "
    "relevant sync gate."
)
NEGATIVE = "A packet-only lip-sync certificate must fail."
POSITIONS = ("beginning", "middle", "end")
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_DISTANCE = re.compile(r"^[1-9][0-9]*(?:\.[0-9]+)?m$")
_PAYLOAD_KEYS = {
    "position",
    "packetStartsAligned",
    "measuredOffsetMs",
    "fixtureDistance",
    "packetOnlyCertificate",
    "containerTiming",
    "physicalSync",
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
    """Fail the sync gate without collapsing physical sync into packet timing."""
    data = _payload(payload)
    reasons = [
        f"position {data['position']}",
        f"fixture distance {data['fixtureDistance']}",
        INTERVENTION,
    ]
    preserved = [
        data["containerTiming"],
        data["physicalSync"],
        data["fixtureDistance"],
        data["position"],
    ]
    if data["packetOnlyCertificate"]:
        decision = "rejected"
        rejected = ["packet-only-lipsync"]
        reasons.append(NEGATIVE)
    elif data["measuredOffsetMs"] != 0:
        decision = "sync_failed"
        rejected = []
        reasons.append(EXPECTED)
        if data["packetStartsAligned"]:
            reasons.append("aligned packet starts were not treated as physical synchronization")
    else:
        decision = "withheld"
        rejected = []
        reasons.append("no measured visible-audible offset was supplied")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    position = payload["position"]
    if position not in POSITIONS:
        raise ValueError("position is not beginning, middle, or end")
    offset = payload["measuredOffsetMs"]
    if type(offset) is not int or offset < 0 or offset > 10000:
        raise ValueError("measuredOffsetMs must be an int in 0..10000")
    distance = payload["fixtureDistance"]
    if not isinstance(distance, str) or _DISTANCE.fullmatch(distance) is None:
        raise ValueError("fixtureDistance must look like 1.5m")
    container = _token(payload["containerTiming"], "containerTiming")
    physical = _token(payload["physicalSync"], "physicalSync")
    if container == physical:
        raise ValueError("container timing and physical sync must be distinct")
    return {
        "position": position,
        "packetStartsAligned": _bool(payload["packetStartsAligned"], "packetStartsAligned"),
        "measuredOffsetMs": offset,
        "fixtureDistance": distance,
        "packetOnlyCertificate": _bool(payload["packetOnlyCertificate"], "packetOnlyCertificate"),
        "containerTiming": container,
        "physicalSync": physical,
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{name} must be a token")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-08 must not yield qualified or allowed")
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
