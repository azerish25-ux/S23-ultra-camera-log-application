"""TC-P030-08 physical sync disagreement.

Intervention: Provide aligned packet starts but a measured visible-audible
event offset or drift in the actual recording.
Expected: Keep container timing and physical synchronization as distinct
results and fail the relevant sync gate.
Negative: A packet-only lip-sync certificate must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P030-08"
INTERVENTION = (
    "Provide aligned packet starts but a measured visible-audible event offset or drift "
    "in the actual recording."
)
EXPECTED = (
    "Keep container timing and physical synchronization as distinct results and fail the "
    "relevant sync gate."
)
NEGATIVE = "A packet-only lip-sync certificate must fail."

_POSITIONS = ("beginning", "middle", "end")
_DISTANCE = re.compile(r"(?:[1-9][0-9]*|0\.\d*[1-9]|[1-9][0-9]*\.\d*[1-9])")
_OFFSET = re.compile(r"0|-?[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "position",
    "fixtureDistanceM",
    "packetStartsAligned",
    "visibleAudibleOffsetMs",
    "drift",
    "packetOnlyCertificate",
    "containerTiming",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "sync_failed", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep container timing and physical sync distinct. Packet alignment is not a certificate."""
    position, distance, aligned, offset, drift, certificate, container = _payload(payload)
    physical = f"physical:{position}:{offset}ms:distance={distance}"
    preserved = [container, physical]
    disagreement = offset != "0" or drift

    rejected: list[str] = []
    if certificate:
        rejected.append("packet-only-lip-sync-certificate")
    if disagreement and drift and offset == "0":
        rejected.append("physical-drift")
    elif disagreement:
        rejected.append("physical-sync")
        if drift:
            rejected.append("physical-drift")

    if certificate:
        decision = "rejected"
        questions = ["container timing is not physical synchronization"]
        reasons = [NEGATIVE, EXPECTED, "container timing and physical synchronization are distinct results"]
    elif disagreement:
        decision = "sync_failed"
        questions = ["container timing is not physical synchronization"]
        reasons = [EXPECTED, "container timing and physical synchronization are distinct results"]
        if aligned:
            reasons.append("aligned packet starts do not pass the sync gate")
    else:
        decision = "withheld"
        questions = ["physical synchronization unverified on host"]
        reasons = [
            EXPECTED,
            "container timing and physical synchronization are distinct results",
            "a zero offset on this host fixture is not a lip-sync certificate",
        ]
    if not aligned and decision != "rejected":
        reasons.append("packet starts were not aligned")

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, str, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    position = payload["position"]
    if position not in _POSITIONS:
        raise ValueError("position must be beginning, middle, or end")
    distance = payload["fixtureDistanceM"]
    if not isinstance(distance, str) or _DISTANCE.fullmatch(distance) is None:
        raise ValueError("fixtureDistanceM must be a canonical positive decimal string")
    aligned = _bool(payload["packetStartsAligned"], "packetStartsAligned")
    offset = payload["visibleAudibleOffsetMs"]
    if not isinstance(offset, str) or _OFFSET.fullmatch(offset) is None:
        raise ValueError("visibleAudibleOffsetMs must be a canonical integer string")
    drift = _bool(payload["drift"], "drift")
    certificate = _bool(payload["packetOnlyCertificate"], "packetOnlyCertificate")
    container = payload["containerTiming"]
    if not isinstance(container, str) or not container or container != container.strip():
        raise ValueError("containerTiming must be a non-empty string")
    if container == f"physical:{position}:{offset}ms:distance={distance}":
        raise ValueError("container timing must stay distinct from the physical result")
    return position, distance, aligned, offset, drift, certificate, container


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("sync decision cannot be qualified or allowed")
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
