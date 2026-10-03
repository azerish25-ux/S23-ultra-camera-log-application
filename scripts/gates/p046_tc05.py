"""TC-P046-05 held-out scene failure.

Intervention: Use a fit that performs well on training patches but fails an
independent natural scene or illuminant.
Expected: Keep training and validation results separate and restrict the
profile to supported conditions.
Negative: Reporting only training error must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-05"
INTERVENTION = (
    "Use a fit that performs well on training patches but fails an independent natural "
    "scene or illuminant."
)
EXPECTED = (
    "Keep training and validation results separate and restrict the profile to supported "
    "conditions."
)
NEGATIVE = "Reporting only training error must fail."

_SCENES = ("training", "natural", "skin", "saturated-fabric", "foliage", "narrow-band")
_PAYLOAD_KEYS = (
    "profileId",
    "trainingError",
    "validationScene",
    "validationError",
    "validationReported",
    "trainingOnly",
    "supportLimit",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_UINT = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Keep training and validation apart. Training-only reports fail."""
    (
        profile_id,
        training,
        scene,
        validation,
        reported,
        training_only,
        support,
    ) = _payload(payload)
    validation_token = validation if reported else "unreported"
    preserved = [
        f"profile:{profile_id}",
        f"training-error:{training}",
        f"validation-scene:{scene}",
        f"validation-error:{validation_token}",
        f"support:{support}",
    ]
    reasons = [EXPECTED]
    if training_only or not reported:
        decision = "rejected"
        rejected = ["training-only-error"]
        reasons.append(NEGATIVE)
        questions = ["validation was not part of the reported error"]
    elif scene != "training" and int(validation) > int(training):
        decision = "restricted"
        rejected = [f"held-out:{scene}"]
        reasons.append(f"profile restricted to {support}")
        questions = [f"held-out {scene}"]
    else:
        decision = "separated"
        rejected = []
        reasons.append("training and validation remain separate")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile_id = payload["profileId"]
    support = payload["supportLimit"]
    if not isinstance(profile_id, str) or _TOKEN.fullmatch(profile_id) is None:
        raise ValueError("profileId must be a token")
    if not isinstance(support, str) or _TOKEN.fullmatch(support) is None:
        raise ValueError("supportLimit must be a token")
    training = payload["trainingError"]
    if not isinstance(training, str) or _UINT.fullmatch(training) is None:
        raise ValueError("trainingError must be a canonical non-negative integer string")
    scene = payload["validationScene"]
    if scene not in _SCENES:
        raise ValueError("validationScene is unknown")
    reported = payload["validationReported"]
    training_only = payload["trainingOnly"]
    if type(reported) is not bool or type(training_only) is not bool:
        raise ValueError("validationReported and trainingOnly must be bools")
    validation = payload["validationError"]
    if reported:
        if not isinstance(validation, str) or _UINT.fullmatch(validation) is None:
            raise ValueError("validationError must be a canonical non-negative integer string")
    elif validation != "":
        raise ValueError("unreported validationError must be empty")
    return profile_id, training, scene, validation, reported, training_only, support


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
