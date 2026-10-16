"""TC-P121-02 Mutable recipe during export.

Host fixture. A running job stays bound to the recipe frozen at start. Later
slider edits create a new version. Live slider values must not color successive
output frames.
"""

from __future__ import annotations


CASE_ID = "TC-P121-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
NEGATIVE_TOKEN = "live-slider-values-for-successive-frames"
REPEATS = ("stock", "focus", "grain-seed", "output-range", "source-interpretation")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "parameter",
    "frozenValue",
    "liveValue",
    "jobStarted",
    "framesUsedLiveValue",
    "editAfterStart",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Bind output frames to the frozen recipe. A later edit is a new version."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"parameter {fields['parameter']}"]
    changed = fields["liveValue"] != fields["frozenValue"]
    if fields["jobStarted"] and fields["framesUsedLiveValue"] and changed:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    version = fields["frozenValue"]
    if fields["jobStarted"] and fields["editAfterStart"] and changed and not fields["framesUsedLiveValue"]:
        version = fields["frozenValue"] + "+v2"
        reasons.append("subsequent edit created a new version")
    elif fields["jobStarted"] and changed and not fields["framesUsedLiveValue"] and not fields["editAfterStart"]:
        rejected.append("unversioned-recipe-drift")
        reasons.append("a changed value was neither frozen nor versioned")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("running job remained bound to the frozen recipe")
    preserved = [
        fields["evidenceId"],
        {
            "parameter": fields["parameter"],
            "frozenValue": fields["frozenValue"],
            "liveValue": fields["liveValue"],
            "boundValue": fields["frozenValue"],
            "newVersion": version if version != fields["frozenValue"] else None,
            "jobStarted": fields["jobStarted"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    parameter = payload["parameter"]
    if repeat not in REPEATS or parameter not in REPEATS:
        raise ValueError("repeat or parameter is unsupported")
    if repeat != parameter:
        raise ValueError("repeat must name the changed parameter")
    for label in ("jobStarted", "framesUsedLiveValue", "editAfterStart"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    return {
        "evidenceId": evidence,
        "repeat": repeat,
        "parameter": parameter,
        "frozenValue": _text(payload["frozenValue"], "frozenValue"),
        "liveValue": _text(payload["liveValue"], "liveValue"),
        "jobStarted": payload["jobStarted"],
        "framesUsedLiveValue": payload["framesUsedLiveValue"],
        "editAfterStart": payload["editAfterStart"],
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
