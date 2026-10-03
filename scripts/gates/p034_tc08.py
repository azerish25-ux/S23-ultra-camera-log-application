"""TC-P034-08 throughput stage conflation.

Acquisition rate and saved-source rate stay separate. A retained complete
path is a host label only. Advertising discarded-frame acquisition speed as
saved RAW recording performance fails.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P034-08"
INTERVENTION = (
    "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
)
EXPECTED = (
    "Report separate stage rates and qualify only the successfully retained complete path."
)
NEGATIVE = (
    "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."
)

THERMALS = ("nominal", "warm", "hot", "critical")
_FPS = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_PAYLOAD_KEYS = (
    "acquisitionFps",
    "savedFps",
    "savedComplete",
    "discardedFrames",
    "advertiseAcquisitionAsSaved",
    "durationS",
    "storagePressure",
    "audioSelected",
    "thermal",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "stages_separated", "retained_complete"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep acquisition and saved-source rates distinct."""
    fields = _payload(payload)
    preserved = [
        f"acquisition:{fields['acquisitionFps']}",
        f"saved:{fields['savedFps']}",
        f"discarded:{fields['discardedFrames']}",
        f"duration:{fields['durationS']}",
        f"storage:{fields['storagePressure']}",
        f"audio:{fields['audioSelected']}",
        f"thermal:{fields['thermal']}",
    ]
    reasons = [
        INTERVENTION,
        EXPECTED,
        f"acquisition stage {fields['acquisitionFps']}",
        f"saved stage {fields['savedFps']}",
    ]
    if fields["advertiseAcquisitionAsSaved"]:
        reasons.append(NEGATIVE)
        reasons.append("acquisition fps was not reported as saved RAW performance")
        return _result(
            "rejected",
            reasons,
            ["acquisition-advertised-as-saved"],
            preserved,
            ["saved performance not established"],
        )
    if fields["savedComplete"]:
        reasons.append("retained complete path is not acquisition speed")
        reasons.append("retained complete path is not physical S23 qualification")
        return _result(
            "retained_complete",
            reasons,
            [],
            preserved,
            ["physical recording performance unverified"],
        )
    reasons.append("saved source did not complete; acquisition speed is not a recording result")
    return _result(
        "stages_separated",
        reasons,
        [],
        preserved,
        ["saved source not retained"],
    )


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    for label in ("acquisitionFps", "savedFps"):
        value = payload[label]
        if not isinstance(value, str) or _FPS.fullmatch(value) is None or value == "0":
            raise ValueError(f"{label} must be a positive decimal string")
    if type(payload["savedComplete"]) is not bool:
        raise ValueError("savedComplete must be a bool")
    if type(payload["discardedFrames"]) is not int or payload["discardedFrames"] < 0:
        raise ValueError("discardedFrames must be a non-negative int")
    if type(payload["advertiseAcquisitionAsSaved"]) is not bool:
        raise ValueError("advertiseAcquisitionAsSaved must be a bool")
    if type(payload["durationS"]) is not int or payload["durationS"] <= 0:
        raise ValueError("durationS must be a positive int")
    if type(payload["storagePressure"]) is not bool or type(payload["audioSelected"]) is not bool:
        raise ValueError("storagePressure and audioSelected must be bools")
    if payload["thermal"] not in THERMALS:
        raise ValueError("thermal is not a known state")
    return payload


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("throughput decision cannot be qualified or allowed")
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
