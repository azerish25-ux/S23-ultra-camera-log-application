"""TC-P041-05 held-out scene failure.

Training error and validation error stay separate. A fit that fails an
independent scene is restricted to supported conditions. Reporting only the
training error fails.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P041-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent natural "
    "scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile to supported conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("skin", "fabric", "foliage", "narrow-band", "chart")
_FINITE = re.compile(r"^(?:0|0\.[0-9]*[1-9]|[1-9][0-9]*(?:\.[0-9]*[1-9])?)$")
_PAYLOAD_KEYS = (
    "scene",
    "trainingError",
    "validationError",
    "reportTrainingOnly",
    "supportedConditions",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "restricted", "held_out_checked"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep training and validation apart. Do not hide a held-out failure."""
    scene, training, validation, training_only, supported = _payload(payload)
    preserved = [f"scene:{scene}", f"training:{training}"]
    preserved.append("validation:omitted" if validation is None else f"validation:{validation}")
    preserved.extend(f"supported:{item}" for item in supported)
    if training_only or validation is None:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "training error was not reported alone"],
            ["training-only-error"],
            preserved,
            ["validation result was not replaced by the training error"],
        )
    if Decimal(validation) > Decimal(training):
        questions = ["profile restricted to supported conditions"]
        if scene not in supported:
            questions.append(f"{scene} is outside the supported conditions")
        return _result(
            "restricted",
            [
                EXPECTED,
                f"training {training} stays separate from validation {validation}",
                f"held-out scene {scene} failed",
            ],
            [f"held-out:{scene}"],
            preserved,
            questions,
        )
    return _result(
        "held_out_checked",
        [
            EXPECTED,
            f"training {training} stays separate from validation {validation}",
        ],
        [],
        preserved,
        ["training and validation stay separate"],
    )


def _error(value: object, label: str) -> str:
    if not isinstance(value, str) or _FINITE.fullmatch(value) is None:
        raise ValueError(label + " must be a non-negative canonical decimal")
    return value


def _payload(payload: object) -> tuple[str, str, str | None, bool, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scene = payload["scene"]
    if scene not in _SCENES:
        raise ValueError("scene is not a known held-out class")
    training = _error(payload["trainingError"], "trainingError")
    validation = payload["validationError"]
    if validation != "omitted":
        validation = _error(validation, "validationError")
    else:
        validation = None
    training_only = payload["reportTrainingOnly"]
    if type(training_only) is not bool:
        raise ValueError("reportTrainingOnly must be a bool")
    supported = payload["supportedConditions"]
    if not isinstance(supported, list) or len(supported) > 8:
        raise ValueError("supportedConditions must be a list of at most 8 scenes")
    if any(item not in _SCENES for item in supported):
        raise ValueError("supportedConditions must name known scenes")
    if len(supported) != len(set(supported)):
        raise ValueError("supportedConditions must be unique")
    return scene, training, validation, training_only, list(supported)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-05 must not yield qualified or allowed")
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
