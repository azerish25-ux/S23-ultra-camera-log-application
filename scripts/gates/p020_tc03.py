"""TC-P020-03 interruption during transition.

Permission, camera availability, or screen attachment may fail halfway through
an asynchronous transition. The legal outcome is a terminal or recovery state
with resources released and footage retained. A permanently starting state or
a silent switch to another capture contract is rejected.

Baseline white-balance inventory stays in preservedResults. This host module
does not touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P020-03"
INTERVENTION = (
    "Interrupt permission, camera availability, or screen attachment halfway "
    "through an asynchronous transition."
)
EXPECTED = (
    "Reach a legal terminal or recovery state with resources released and "
    "available footage retained."
)
NEGATIVE = "A permanently starting state or a silent switch to another capture contract must fail."
REPEATS = (
    "permission",
    "camera_availability",
    "screen_attachment",
)
WB_INVENTORY = (
    "hardware.namespace:hardware.white_balance",
    "hardware.preset:daylight",
    "hardware.locked:true",
    "hardware.gains:1.42,1.00,1.78",
    "hardware.kelvin:unavailable",
    "scene.namespace:scene.calibration",
    "scene.profile:raw-neutral-v1",
    "scene.version:1",
    "scene.neutral:1.00,1.00,1.00",
    "creative.namespace:creative.preview",
    "creative.slider:warm",
    "creative.recipe:preview-warm-v1",
    "creative.tint:12",
    "source.metadata:unchanged",
)
_PAYLOAD_KEYS = {
    "boundary",
    "audioSelected",
    "permanentlyStarting",
    "silentContractSwitch",
    "footageIds",
    "releasedResources",
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
    """Recover or reject an interrupted transition without dropping footage."""
    boundary, audio, permanent, silent, footage, released = _payload(payload)
    preserved = list(WB_INVENTORY)
    preserved.append("audio:" + ("selected" if audio else "absent"))
    preserved.extend("footage:" + item for item in footage)
    reasons = [EXPECTED, "repeat boundary " + boundary + " audio " + str(audio).lower()]
    rejected: list[str] = []

    if permanent or silent:
        decision = "rejected"
        reasons.append(NEGATIVE)
        if permanent:
            rejected.append("permanently-starting")
            reasons.append("permanently starting state is not a legal terminal")
        if silent:
            rejected.append("silent-contract-switch")
            reasons.append("silent switch to another capture contract is rejected")
    else:
        decision = "recovered"
        reasons.append("legal terminal or recovery state reached")
        reasons.append(
            "resources released: " + (", ".join(released) if released else "none")
        )
        reasons.append("available footage retained")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P020-03 must not decide qualified or allowed")
    if footage and not any(item.startswith("footage:") for item in preserved):
        raise ValueError("available footage must be retained")
    for item in WB_INVENTORY:
        if item not in preserved:
            raise ValueError("white-balance inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in REPEATS:
        raise ValueError("boundary is not a TC-P020-03 repeat")
    return (
        boundary,
        _bool(payload["audioSelected"], "audioSelected"),
        _bool(payload["permanentlyStarting"], "permanentlyStarting"),
        _bool(payload["silentContractSwitch"], "silentContractSwitch"),
        _tokens(payload["footageIds"], "footageIds"),
        _tokens(payload["releasedResources"], "releasedResources"),
    )


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(name + " must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(name + " must be a list")
    seen: set[str] = set()
    tokens: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(name + " entries must be non-empty strings")
        if item in seen:
            raise ValueError(name + " entries must be unique")
        seen.add(item)
        tokens.append(item)
    return tokens


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must not be qualified or allowed")
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

