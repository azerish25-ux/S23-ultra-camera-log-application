"""TC-P055-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene
feature under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-06"
INTERVENTION = "Place a persistent sensor defect beside a real small moving bright feature."
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."
REPEAT = "Repeat over several frames and near saturated boundaries."

_PAYLOAD_KEYS = (
    "defectId",
    "featureId",
    "frameCount",
    "nearSaturation",
    "removeAllIsolated",
    "defectPersistent",
    "featureMoving",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Correct a persistent defect without deleting the real highlight."""
    defect, feature, frames, saturated, remove_all, persistent, moving = _payload(payload)
    preserved = [
        f"defect:{defect}",
        f"feature:{feature}",
        f"frames:{frames}",
        f"near-saturation:{str(saturated).lower()}",
        f"persistent:{str(persistent).lower()}",
        f"moving:{str(moving).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    if remove_all:
        decision = "rejected"
        rejected = ["removed-every-isolated-bright-pixel"]
        reasons.append(NEGATIVE)
        questions.append(f"feature {feature} stayed in the inventory")
    elif persistent and moving:
        decision = "defect_only"
        rejected = []
        reasons.append(f"corrected only {defect}")
        reasons.append(f"preserved moving feature {feature}")
        if saturated:
            questions.append("near saturated boundary the feature was kept")
        if frames > 1:
            questions.append(f"policy held across {frames} frames")
    else:
        decision = "withheld"
        rejected = []
        reasons.append("defect policy preconditions were not met")
        questions.append("neither the defect nor the feature was deleted")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    defect = payload["defectId"]
    feature = payload["featureId"]
    if not isinstance(defect, str) or _TOKEN.fullmatch(defect) is None:
        raise ValueError("defectId must be a token")
    if not isinstance(feature, str) or _TOKEN.fullmatch(feature) is None:
        raise ValueError("featureId must be a token")
    if defect == feature:
        raise ValueError("defectId and featureId must differ")
    frames = payload["frameCount"]
    if type(frames) is not int or frames < 1:
        raise ValueError("frameCount must be a positive int")
    saturated = payload["nearSaturation"]
    remove_all = payload["removeAllIsolated"]
    persistent = payload["defectPersistent"]
    moving = payload["featureMoving"]
    for name, flag in (
        ("nearSaturation", saturated),
        ("removeAllIsolated", remove_all),
        ("defectPersistent", persistent),
        ("featureMoving", moving),
    ):
        if type(flag) is not bool:
            raise ValueError(name + " must be a bool")
    return defect, feature, frames, saturated, remove_all, persistent, moving


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-06 must not yield qualified or allowed")
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
