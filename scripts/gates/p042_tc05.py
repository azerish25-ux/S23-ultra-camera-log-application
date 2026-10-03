"""TC-P042-05 held-out scene failure.

Training error and validation error stay in separate fields. A report that
quotes only the training error is rejected. The profile stays restricted to
the scene that was actually checked.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent "
    "natural scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile "
    "to supported conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("skin", "saturated_fabrics", "foliage", "narrow_band")
_REPORTS = ("training_only", "separated")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_UINT = re.compile(r"0|[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "profileId",
    "scene",
    "trainingError",
    "validationError",
    "report",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "restricted", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep both errors. Training-only reporting fails."""
    profile, scene, training, validation, report = _payload(payload)
    preserved = [
        f"profile:{profile}",
        f"scene:{scene}",
        f"training-error:{training}",
        f"validation-error:{validation}",
    ]
    if report == "training_only":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "validation error was not dropped from the inventory"],
            ["training-only-error"],
            preserved,
            ["training error is not the held-out result"],
        )
    if int(validation) > int(training):
        return _result(
            "restricted",
            [
                EXPECTED,
                INTERVENTION,
                "training and validation stay separate",
                f"profile restricted for {scene}",
            ],
            ["held-out-scene"],
            preserved,
            ["unsupported scenes are outside the profile"],
        )
    return _result(
        "withheld",
        [EXPECTED, "separated errors do not generalize beyond the recorded scene"],
        [],
        preserved,
        [f"{scene} was not promoted to a default profile"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile = _token(payload["profileId"], "profileId")
    scene = _choice(payload["scene"], _SCENES, "scene")
    training = _uint(payload["trainingError"], "trainingError")
    validation = _uint(payload["validationError"], "validationError")
    report = _choice(payload["report"], _REPORTS, "report")
    return profile, scene, training, validation, report


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} is not an allowed value")
    return value


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _uint(value: object, label: str) -> str:
    if not isinstance(value, str) or _UINT.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative integer string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-05 must not yield qualified or allowed")
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
