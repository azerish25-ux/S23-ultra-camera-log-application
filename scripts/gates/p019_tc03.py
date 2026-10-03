"""TC-P019-03 interruption during an asynchronous transition.

Permission loss, camera loss, or a dropped screen attachment must reach a
legal terminal or recovery state. Footage already available is kept and held
resources are released. A permanently starting state, or a silent switch to
another capture contract, is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P019-03"
INTERVENTION = (
    "Interrupt permission, camera availability, or screen attachment halfway "
    "through an asynchronous transition."
)
EXPECTED = (
    "Reach a legal terminal or recovery state with resources released and "
    "available footage retained."
)
NEGATIVE = (
    "A permanently starting state or a silent switch to another capture contract must fail."
)
REPEAT = "Repeat at every state boundary with and without selected audio."
BOUNDARIES = (
    "opening",
    "preview",
    "configuring",
    "starting",
    "recording",
    "stopping",
    "finalizing",
    "failure",
)
INTERRUPTIONS = ("permission", "camera_availability", "screen_attachment")
_PAYLOAD_KEYS = (
    "boundary",
    "selectedAudio",
    "interruption",
    "permanentlyStarting",
    "silentContractSwitch",
    "availableFootage",
    "heldResources",
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
    """Leave the interrupted boundary without staying in starting."""
    fields = _payload(payload)
    footage = fields["availableFootage"]
    reasons = [
        f"boundary {fields['boundary']}",
        f"interruption {fields['interruption']}",
        "audio selected" if fields["selectedAudio"] else "audio not selected",
    ]
    rejected: list[str] = []
    if fields["permanentlyStarting"]:
        rejected.append("permanently-starting")
        reasons.append("a permanently starting state is not a legal terminal")
    if fields["silentContractSwitch"]:
        rejected.append("silent-contract-switch")
        reasons.append("a silent switch to another capture contract is rejected")

    if rejected:
        decision = "rejected"
        next_state = "failure"
        reasons.append("resources released")
    else:
        next_state, decision = _recover(fields["boundary"], fields["interruption"])
        reasons.append(f"reached {next_state}")
        reasons.append("resources released")
        reasons.append("available footage retained")

    if next_state == "starting":
        raise ValueError("interruption must not remain in starting")
    preserved = [f"footage:{item}" for item in footage]
    preserved.append("state:" + next_state)
    preserved.extend(f"released:{item}" for item in fields["heldResources"])
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P019-03 must not yield qualified or allowed")
    for item in footage:
        if f"footage:{item}" not in preserved:
            raise ValueError("available footage must be retained")
    return _result(decision, reasons, rejected, preserved, [])


def _recover(boundary: str, interruption: str) -> tuple[str, str]:
    if boundary == "failure":
        return "failure", "terminal"
    if boundary == "finalizing":
        return "finalizing", "terminal"
    if boundary == "stopping":
        return "stopping", "terminal"
    if interruption == "screen_attachment" and boundary in ("opening", "preview", "configuring"):
        return "preview", "recovered"
    if boundary == "recording" and interruption == "screen_attachment":
        return "stopping", "terminal"
    return "failure", "terminal"


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in BOUNDARIES:
        raise ValueError("boundary is not a capture state")
    interruption = payload["interruption"]
    if interruption not in INTERRUPTIONS:
        raise ValueError("interruption is not supported")
    return {
        "boundary": boundary,
        "selectedAudio": _bool(payload["selectedAudio"], "selectedAudio"),
        "interruption": interruption,
        "permanentlyStarting": _bool(payload["permanentlyStarting"], "permanentlyStarting"),
        "silentContractSwitch": _bool(payload["silentContractSwitch"], "silentContractSwitch"),
        "availableFootage": _tokens(payload["availableFootage"], "availableFootage"),
        "heldResources": _tokens(payload["heldResources"], "heldResources"),
    }


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(f"{name} must contain non-empty strings")
        if item in seen:
            raise ValueError(f"{name} must be unique")
        seen.add(item)
        items.append(item)
    return items


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
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
