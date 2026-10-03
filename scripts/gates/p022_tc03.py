"""TC-P022-03 interruption during transition.

Interrupt permission, camera availability, or screen attachment halfway
through an asynchronous transition. Reach a legal terminal or recovery state
with resources released and available footage retained. A permanently starting
state or a silent switch to another capture contract must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-03"
INTERVENTION = (
    "Interrupt permission, camera availability, or screen attachment halfway "
    "through an asynchronous transition."
)
EXPECTED = (
    "Reach a legal terminal or recovery state with resources released and "
    "available footage retained."
)
NEGATIVE = "A permanently starting state or a silent switch to another capture contract must fail."
BOUNDARIES = ("permission", "camera_availability", "screen_attachment")
_TERMINALS = ("stopped", "recovering", "starting", "switched")
_PAYLOAD_KEYS = (
    "boundary",
    "audioSelected",
    "permanentlyStarting",
    "silentContractSwitch",
    "resourcesReleased",
    "footage",
    "terminalState",
    "cleanMasterHash",
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
    """Stop or recover. Do not stay starting or switch contracts silently."""
    data = _payload(payload)
    audio = "audio selected" if data["audioSelected"] else "audio not selected"
    reasons = [f"boundary {data['boundary']}", audio, f"terminal {data['terminalState']}"]
    rejected: list[str] = []
    if data["permanentlyStarting"] or data["terminalState"] == "starting":
        rejected.append("permanently-starting")
        reasons.append("a permanently starting state must fail")
    if data["silentContractSwitch"] or data["terminalState"] == "switched":
        rejected.append("silent-contract-switch")
        reasons.append("a silent switch to another capture contract must fail")
    if not data["resourcesReleased"]:
        rejected.append("resources-held")
        reasons.append("resources must be released")
    questions: list[str] = []
    if rejected:
        decision = "rejected"
    elif data["terminalState"] == "stopped":
        decision = "terminal"
        reasons.append("available footage retained")
    else:
        decision = "recovering"
        reasons.append("recovery state retains available footage")
        questions.append("recovery state is not a finished capture")
    preserved = list(data["footage"]) + [data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in BOUNDARIES:
        raise ValueError("boundary is not a declared repeat")
    terminal = payload["terminalState"]
    if terminal not in _TERMINALS:
        raise ValueError("terminalState is not legal to name")
    footage = _tokens(payload["footage"], "footage")
    return {
        "boundary": boundary,
        "audioSelected": _bool(payload["audioSelected"], "audioSelected"),
        "permanentlyStarting": _bool(payload["permanentlyStarting"], "permanentlyStarting"),
        "silentContractSwitch": _bool(payload["silentContractSwitch"], "silentContractSwitch"),
        "resourcesReleased": _bool(payload["resourcesReleased"], "resourcesReleased"),
        "footage": footage,
        "terminalState": terminal,
        "cleanMasterHash": _token(payload["cleanMasterHash"], "cleanMasterHash"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    items = [_token(item, name) for item in value]
    if len(items) != len(set(items)):
        raise ValueError(f"{name} must be unique")
    return items


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P022-03 must not yield qualified or allowed")
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
