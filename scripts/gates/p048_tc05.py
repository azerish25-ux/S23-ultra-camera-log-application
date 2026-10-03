"""TC-P048-05 held-out scene failure.

Intervention: Use a fit that performs well on training patches but fails an
independent natural scene or illuminant.
Expected: Keep training and validation results separate and restrict the
profile to supported conditions.
Negative: Reporting only training error must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P048-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent natural "
    "scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile to supported "
    "conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("chart", "skin", "fabric", "foliage", "narrow_band", "natural")
_PAYLOAD_KEYS = (
    "trainingError",
    "validationError",
    "scene",
    "reportTrainingOnly",
    "supported",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "restricted", "training_separated", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_UINT = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Keep training and validation apart. A training-only report fails."""
    training, validation, scene, training_only, supported = _payload(payload)
    preserved = [
        f"training-error:{training}",
        f"validation-error:{validation}",
        f"scene:{scene}",
        f"supported:{str(supported).lower()}",
    ]
    reasons = [EXPECTED, "training and validation results stay separate"]
    if training_only:
        decision = "rejected"
        rejected = ["training-only-report"]
        reasons.append(NEGATIVE)
        questions = ["validation result was retained despite a training-only report"]
    elif int(validation) > int(training) and scene != "chart":
        decision = "restricted"
        rejected = ["held-out-failure"]
        reasons.append(f"profile restricted after held-out {scene} failure")
        questions = [f"profile restricted; {scene} is outside supported conditions"]
    elif scene == "chart" and int(validation) <= int(training):
        decision = "training_separated"
        rejected = []
        reasons.append("chart agreement does not cover a held-out natural scene")
        questions = ["held-out natural scenes were not exercised"]
    else:
        decision = "withheld"
        rejected = []
        reasons.append("held-out evidence does not widen the profile")
        questions = ["training and validation stay separate"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    training = payload["trainingError"]
    validation = payload["validationError"]
    if not isinstance(training, str) or _UINT.fullmatch(training) is None:
        raise ValueError("trainingError must be a canonical non-negative integer string")
    if not isinstance(validation, str) or _UINT.fullmatch(validation) is None:
        raise ValueError("validationError must be a canonical non-negative integer string")
    scene = payload["scene"]
    if scene not in _SCENES:
        raise ValueError("scene is unknown")
    training_only = payload["reportTrainingOnly"]
    supported = payload["supported"]
    if type(training_only) is not bool or type(supported) is not bool:
        raise ValueError("reportTrainingOnly and supported must be bools")
    return training, validation, scene, training_only, supported


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("held-out decision cannot be qualified or allowed")
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
