"""TC-P017-03 interruption during transition.

Permission, camera availability, or screen attachment can fail halfway through
a transition. The owner reaches a legal terminal or recovery state, releases
resources, and keeps available footage. A stuck starting state or a silent
capture-contract switch is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-03"
INTERVENTION = (
    "Interrupt permission, camera availability, or screen attachment halfway "
    "through an asynchronous transition."
)
EXPECTED = (
    "Reach a legal terminal or recovery state with resources released and "
    "available footage retained."
)
NEGATIVE = "A permanently starting state or a silent switch to another capture contract must fail."
BOUNDARIES = (
    "opening",
    "preview",
    "configuring",
    "starting",
    "recording",
    "stopping",
    "finalizing",
)
INTERRUPTIONS = ("permission", "camera_availability", "screen_attachment")
_PAYLOAD_KEYS = (
    "boundary",
    "interruption",
    "audioSelected",
    "permanentStarting",
    "silentContractSwitch",
    "footageIds",
    "releasedResourceIds",
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
    """End in terminal or recovery. Permanent starting is rejected."""
    data = _payload(payload)
    reasons = [
        f"boundary {data['boundary']}",
        f"interruption {data['interruption']}",
        "audio selected" if data["audioSelected"] else "audio not selected",
        INTERVENTION,
        EXPECTED,
    ]
    rejected: list[str] = []
    if data["permanentStarting"]:
        rejected.append("permanent-starting")
    if data["silentContractSwitch"]:
        rejected.append("silent-contract-switch")
    if rejected:
        reasons.append(NEGATIVE)
        decision = "rejected"
    elif data["interruption"] == "screen_attachment":
        decision = "recovery"
        reasons.append("legal recovery")
        reasons.append("resources released: " + ",".join(data["releasedResourceIds"]))
        reasons.append("available footage retained")
    else:
        decision = "terminal"
        reasons.append("legal terminal")
        reasons.append("resources released: " + ",".join(data["releasedResourceIds"]))
        reasons.append("available footage retained")
    if decision == "starting":
        raise ValueError("interruption must not remain permanently starting")
    preserved = list(data["footageIds"])
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    interruption = payload["interruption"]
    if boundary not in BOUNDARIES:
        raise ValueError("boundary is not a TC-P017-03 repeat")
    if interruption not in INTERRUPTIONS:
        raise ValueError("interruption is not permission, camera availability, or screen attachment")
    audio = _bool(payload["audioSelected"], "audioSelected")
    permanent = _bool(payload["permanentStarting"], "permanentStarting")
    silent = _bool(payload["silentContractSwitch"], "silentContractSwitch")
    footage = _ids(payload["footageIds"], "footageIds")
    released = _ids(payload["releasedResourceIds"], "releasedResourceIds")
    return {
        "boundary": boundary,
        "interruption": interruption,
        "audioSelected": audio,
        "permanentStarting": permanent,
        "silentContractSwitch": silent,
        "footageIds": footage,
        "releasedResourceIds": released,
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _ids(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(f"{name} entries must be non-empty strings")
        if item in seen:
            raise ValueError(f"{name} entries must be unique")
        seen.add(item)
    return list(value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P017-03 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
