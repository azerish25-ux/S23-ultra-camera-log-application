"""TC-P054-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene
feature under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P054-06"
INTERVENTION = "Place a persistent sensor defect beside a real small moving bright feature."
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_PAYLOAD_KEYS = (
    "defectId",
    "featureId",
    "frameCount",
    "defectPersistent",
    "featureMoving",
    "nearSaturation",
    "featureCode",
    "removeAllIsolated",
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
_POSITIVE = re.compile(r"[1-9][0-9]*")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Correct a persistent defect only. Do not delete every isolated highlight."""
    (
        defect_id,
        feature_id,
        frames,
        persistent,
        moving,
        saturated,
        code,
        remove_all,
    ) = _payload(payload)
    preserved = [
        defect_id,
        feature_id,
        f"frames:{frames}",
        f"feature-code:{code}",
        "near-saturation:yes" if saturated else "near-saturation:no",
        "real-feature:preserved",
    ]
    reasons = [EXPECTED, INTERVENTION, f"defect {defect_id} beside {feature_id}"]
    rejected: list[str] = []
    questions: list[str] = []
    if saturated:
        questions.append(f"{feature_id} near saturation stays in the inventory")
    if remove_all:
        decision = "rejected"
        rejected.append("every-isolated-bright-pixel")
        reasons.append(NEGATIVE)
        questions.append("real moving feature was not removed with the isolated pixels")
    elif not persistent:
        decision = "withheld"
        reasons.append("defect is not persistent, so no correction was applied")
        questions.append("non-persistent defect was left uncorrected")
    elif not moving:
        decision = "withheld"
        reasons.append("bright feature is not confirmed as motion, so correction stays withheld")
        questions.append("static bright sample was not treated as a defect")
    else:
        decision = "defect-only"
        reasons.append("only the persistent defect is eligible for correction")
        questions.append(f"feature {feature_id} preserved across {frames} frames")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool, bool, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    defect_id = _token(payload["defectId"], "defectId")
    feature_id = _token(payload["featureId"], "featureId")
    frames = payload["frameCount"]
    if not isinstance(frames, str) or _POSITIVE.fullmatch(frames) is None:
        raise ValueError("frameCount must be a canonical positive integer string")
    persistent = _bool(payload["defectPersistent"], "defectPersistent")
    moving = _bool(payload["featureMoving"], "featureMoving")
    saturated = _bool(payload["nearSaturation"], "nearSaturation")
    code = payload["featureCode"]
    if not isinstance(code, str) or _DECIMAL.fullmatch(code) is None:
        raise ValueError("featureCode must be a canonical decimal string")
    remove_all = _bool(payload["removeAllIsolated"], "removeAllIsolated")
    return defect_id, feature_id, frames, persistent, moving, saturated, code, remove_all


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


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
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-06 must not yield qualified or allowed")
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
