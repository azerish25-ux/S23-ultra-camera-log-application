"""TC-P043-05 held-out scene failure.

Intervention: Use a fit that performs well on training patches but fails an
independent natural scene or illuminant.
Expected: Keep training and validation results separate and restrict the
profile to supported conditions.
Negative: Reporting only training error must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P043-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent "
    "natural scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile to "
    "supported conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("neutral-chart", "skin", "saturated-fabrics", "foliage", "narrow-band")
_HOLDOUTS = ("skin", "saturated-fabrics", "foliage", "narrow-band")
_PAYLOAD_KEYS = (
    "profileId",
    "scene",
    "trainingError",
    "validationError",
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
_DECISIONS = ("rejected", "restricted", "separated", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep training and validation errors apart. Training-only reports fail."""
    profile, scene, training, validation, training_only, supported = _payload(payload)
    preserved = [
        f"profile:{profile}",
        f"training:{training}",
        f"validation:{scene}:{validation}",
        f"claimedSupport:{str(supported).lower()}",
    ]
    failed = Decimal(validation) > Decimal(training)
    rejected: list[str] = []
    questions = ["training error is not validation error"]
    if training_only:
        decision = "rejected"
        rejected.append("training-only")
        if failed and scene in _HOLDOUTS:
            rejected.append(scene)
        reasons = [NEGATIVE, EXPECTED, "validation error retained beside training error"]
    elif failed and scene in _HOLDOUTS:
        decision = "restricted"
        rejected.append(scene)
        if supported:
            rejected.append("support-not-restricted")
        reasons = [
            EXPECTED,
            f"training {training} kept separate from validation {validation}",
            f"profile restricted against {scene}",
        ]
        questions.append(f"restricted:{scene}")
    elif failed:
        decision = "withheld"
        reasons = [EXPECTED, "chart disagreement is not a natural-scene restriction"]
        questions.append("not a natural holdout")
    elif supported:
        decision = "separated"
        reasons = [
            "training and validation stayed separate",
            "agreement on this host fixture is not physical validation",
        ]
        questions.append("separated errors are not a measured profile")
    else:
        decision = "withheld"
        reasons = [EXPECTED, "unsupported profile was not promoted"]
        questions.append("supported conditions were not claimed")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile = payload["profileId"]
    if not isinstance(profile, str) or not profile or profile != profile.strip():
        raise ValueError("profileId must be a non-empty string")
    scene = payload["scene"]
    if scene not in _SCENES:
        raise ValueError("scene is not a known holdout")
    training = payload["trainingError"]
    validation = payload["validationError"]
    for label, value in (("trainingError", training), ("validationError", validation)):
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{label} must be a canonical decimal string")
    training_only = _bool(payload["reportTrainingOnly"], "reportTrainingOnly")
    supported = _bool(payload["supported"], "supported")
    return profile, scene, training, validation, training_only, supported


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
        raise ValueError("holdout decision cannot be qualified or allowed")
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
