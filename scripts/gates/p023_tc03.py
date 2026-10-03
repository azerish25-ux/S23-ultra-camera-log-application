"""TC-P023-03 interruption during an asynchronous transition.

Permission, camera availability, or screen attachment may break a transition
at a state boundary. The legal endings are stopped, failed_visible, or
recovered, with resources released and footage retained. A permanently
starting state or a silent capture-contract switch fails.
"""

from __future__ import annotations

CASE_ID = "TC-P023-03"
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
BOUNDARIES = (
    "idle_to_opening",
    "opening_to_configured",
    "configured_to_starting",
    "starting_to_active",
    "active_to_stopping",
    "stopping_to_final",
)
INTERRUPTS = ("permission", "camera_availability", "screen_attachment")
TERMINALS = ("stopped", "failed", "recovered", "starting", "switched")
_LEGAL = {"stopped": "stopped", "failed": "failed_visible", "recovered": "recovered"}
_PAYLOAD_KEYS = (
    "boundary",
    "audioSelected",
    "interrupt",
    "terminal",
    "resourcesReleased",
    "footageRetained",
    "footageId",
    "silentContractSwitch",
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
    """Require a legal terminal. Permanent start and silent switches are rejected."""
    fields = _payload(payload)
    reasons = [
        f"boundary {fields['boundary']} interrupt {fields['interrupt']} "
        f"audio {fields['audioSelected']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    switched = fields["silentContractSwitch"] or fields["terminal"] == "switched"
    if fields["terminal"] == "starting":
        rejected.append("permanently-starting")
    if switched:
        rejected.append("silent-contract-switch")
    if not fields["resourcesReleased"]:
        rejected.append("resources-held")
    if not fields["footageRetained"]:
        rejected.append("footage-dropped")

    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("transition did not reach a legal terminal with footage retained")
    else:
        decision = _LEGAL[fields["terminal"]]
        reasons.append(EXPECTED)
        reasons.append(f"terminal {decision} released resources and retained footage")

    preserved = [
        fields["footageId"],
        "audio-selected" if fields["audioSelected"] else "audio-not-selected",
    ]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in BOUNDARIES:
        raise ValueError("boundary is not a TC-P023-03 repeat")
    interrupt = payload["interrupt"]
    if interrupt not in INTERRUPTS:
        raise ValueError("interrupt must be permission, camera_availability, or screen_attachment")
    terminal = payload["terminal"]
    if terminal not in TERMINALS:
        raise ValueError("terminal is not a known transition ending")
    footage = payload["footageId"]
    if not isinstance(footage, str) or not footage or footage != footage.strip() or " " in footage:
        raise ValueError("footageId must be a non-empty token")
    return {
        "boundary": boundary,
        "audioSelected": _bool(payload["audioSelected"], "audioSelected"),
        "interrupt": interrupt,
        "terminal": terminal,
        "resourcesReleased": _bool(payload["resourcesReleased"], "resourcesReleased"),
        "footageRetained": _bool(payload["footageRetained"], "footageRetained"),
        "footageId": footage,
        "silentContractSwitch": _bool(payload["silentContractSwitch"], "silentContractSwitch"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P023-03 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
