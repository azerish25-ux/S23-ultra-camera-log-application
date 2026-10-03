"""TC-P045-05 held-out scene failure.

Intervention: Use a fit that performs well on training patches but fails an
independent natural scene or illuminant.
Expected: Keep training and validation results separate and restrict the
profile to supported conditions.
Negative: Reporting only training error must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P045-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent "
    "natural scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile "
    "to supported conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("skin", "saturated_fabric", "foliage", "narrow_band", "chart")
_LIGHTS = ("training", "independent")
_PAYLOAD_KEYS = (
    "profileId",
    "scene",
    "illuminant",
    "trainingError",
    "validationError",
    "trainingOnlyReport",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_TRAIN_LIMIT = Decimal("0.02")
_FAIL = Decimal("0.15")


def evaluate(payload: dict) -> dict:
    """Keep training and validation errors apart. Training-only reports fail."""
    profile, scene, illuminant, training, validation, training_only = _payload(payload)
    preserved = [
        f"profile:{profile}",
        f"scene:{scene}",
        f"illuminant:{illuminant}",
        f"training-error:{training}",
        f"validation-error:{validation}",
    ]
    train_number = Decimal(training)
    valid_number = Decimal(validation)
    reasons = [EXPECTED, INTERVENTION]
    questions = ["training error and validation error were stored separately"]
    rejected: list[str] = []
    failed = valid_number >= _FAIL or (scene != "chart" and illuminant == "independent")
    if training_only:
        decision = "rejected"
        rejected.append("training-only-report")
        if failed:
            rejected.append(f"withheld-validation:{scene}")
        reasons.append(NEGATIVE)
        reasons.append("validation error was not omitted from the inventory")
        questions.append("training-only report rejected")
    elif failed:
        decision = "restricted"
        rejected.append(f"validation:{scene}")
        if illuminant == "independent":
            rejected.append("independent-illuminant")
        if train_number > _TRAIN_LIMIT:
            rejected.append("training-error")
        reasons.append("profile restricted to supported conditions")
        questions.append(f"{scene} validation stays separate from training error")
    else:
        decision = "separated"
        reasons.append("training and validation were both reported")
        questions.append("separated errors are not a measured camera profile")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile = payload["profileId"]
    if not isinstance(profile, str) or _TOKEN.fullmatch(profile) is None:
        raise ValueError("profileId must be a token")
    scene = payload["scene"]
    if scene not in _SCENES:
        raise ValueError("scene is unsupported")
    illuminant = payload["illuminant"]
    if illuminant not in _LIGHTS:
        raise ValueError("illuminant must be training or independent")
    training = payload["trainingError"]
    validation = payload["validationError"]
    for name, value in (("trainingError", training), ("validationError", validation)):
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{name} must be a canonical decimal string")
    training_only = payload["trainingOnlyReport"]
    if type(training_only) is not bool:
        raise ValueError("trainingOnlyReport must be a bool")
    return profile, scene, illuminant, training, validation, training_only


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-05 must not yield qualified or allowed")
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
