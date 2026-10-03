"""TC-P047-05 held-out scene failure.

Intervention: Use a fit that performs well on training patches but fails an
independent natural scene or illuminant.
Expected: Keep training and validation results separate and restrict the
profile to supported conditions.
Negative: Reporting only training error must fail.
"""

from __future__ import annotations

from decimal import Decimal

CASE_ID = "TC-P047-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent "
    "natural scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile to "
    "supported conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("skin", "saturated-fabrics", "foliage", "narrow-band")
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "profileId",
    "sceneClass",
    "trainingError",
    "validationError",
    "tolerance",
    "reportTrainingOnly",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "restricted", "separated")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep training and validation apart. Training-only reports fail."""
    profile, scene, training, validation, tolerance, training_only = _payload(payload)
    preserved = [
        "profile:" + profile,
        "scene:" + scene,
        "training-error:" + training,
        "validation-error:" + validation,
        "tolerance:" + tolerance,
    ]
    if training_only:
        return _result(
            "rejected",
            [
                NEGATIVE,
                EXPECTED,
                "training error was not reported alone",
            ],
            ["training-only-report"],
            preserved,
            ["validation error retained beside training error"],
        )
    if Decimal(validation) > Decimal(tolerance):
        return _result(
            "restricted",
            [
                EXPECTED,
                "validation error exceeds tolerance for " + scene,
                "training error was kept separate and was not the acceptance metric",
            ],
            ["held-out:" + scene],
            preserved,
            ["supported-conditions-exclude:" + scene],
        )
    return _result(
        "separated",
        [
            EXPECTED,
            "training and validation errors stayed separate",
            "profile is not a universal default",
        ],
        [],
        preserved,
        ["profile restricted to supported conditions"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scene = payload["sceneClass"]
    if scene not in _SCENES:
        raise ValueError("sceneClass is unsupported")
    training_only = payload["reportTrainingOnly"]
    if type(training_only) is not bool:
        raise ValueError("reportTrainingOnly must be a bool")
    profile = payload["profileId"]
    if not isinstance(profile, str) or not profile or any(char not in _TOKEN for char in profile):
        raise ValueError("profileId must be a canonical token")
    return (
        profile,
        scene,
        _decimal(payload["trainingError"], "trainingError"),
        _decimal(payload["validationError"], "validationError"),
        _positive(payload["tolerance"], "tolerance"),
        training_only,
    )


def _positive(value: object, label: str) -> str:
    text = _decimal(value, label)
    if Decimal(text) <= 0:
        raise ValueError(label + " must be positive")
    return text


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value[0] == "-":
        raise ValueError(label + " must be a canonical decimal string")
    if "." in value:
        whole, frac = value.split(".", 1)
        if (
            not frac
            or frac[-1] == "0"
            or not _digits(whole)
            or not _digits(frac)
            or (len(whole) > 1 and whole[0] == "0")
        ):
            raise ValueError(label + " must be a canonical decimal string")
        return value
    if not _digits(value) or (len(value) > 1 and value[0] == "0"):
        raise ValueError(label + " must be a canonical decimal string")
    return value


def _digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("held-out decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
