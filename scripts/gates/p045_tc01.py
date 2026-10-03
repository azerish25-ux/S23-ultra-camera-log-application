"""TC-P045-01 neutral target invalidity.

Intervention: Replace the approved neutral patch with a clipped, textured,
specular, or incorrectly identified region.
Expected: Reject scale calibration or retain an explicitly provisional result
rather than fabricating a measured profile.
Negative: Whole-image average brightness cannot substitute for a known neutral
target.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P045-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, "
    "or incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result "
    "rather than fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_PATCHES = (
    "approved",
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "dark",
    "mixed",
    "partial_clip",
)
_LIGHTS = ("neutral", "colored")
_INVALID = {
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "dark",
    "mixed",
    "partial_clip",
}
_PAYLOAD_KEYS = (
    "patchId",
    "patchClass",
    "illumination",
    "wholeImageAverage",
    "signalLevel",
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


def evaluate(payload: dict) -> dict:
    """Reject an invalid neutral or keep an explicitly provisional scale."""
    patch_id, patch_class, illumination, average, signal = _payload(payload)
    preserved = [
        patch_id,
        f"class:{patch_class}",
        f"light:{illumination}",
        f"signal:{signal}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION]
    if average:
        decision = "rejected"
        rejected.extend(["whole-image-average", "not-a-neutral-target"])
        reasons.append(NEGATIVE)
        questions.append("whole-image average was not used as a neutral target")
    elif patch_class in _INVALID or illumination == "colored":
        decision = "rejected"
        rejected.append(f"invalid-neutral:{patch_class}")
        if illumination == "colored":
            rejected.append("colored-illumination")
            reasons.append("colored illumination is not a neutral reference")
        reasons.append("invalid neutral evidence does not fabricate a measured profile")
        questions.append(f"{patch_class} under {illumination} was rejected")
    else:
        decision = "provisional"
        reasons.append("provisional scale is not a measured profile")
        questions.append("approved neutral remains provisional on this host fixture")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    patch_id = payload["patchId"]
    if not isinstance(patch_id, str) or _TOKEN.fullmatch(patch_id) is None:
        raise ValueError("patchId must be a token")
    patch_class = payload["patchClass"]
    if patch_class not in _PATCHES:
        raise ValueError("patchClass is unsupported")
    illumination = payload["illumination"]
    if illumination not in _LIGHTS:
        raise ValueError("illumination must be neutral or colored")
    average = payload["wholeImageAverage"]
    if type(average) is not bool:
        raise ValueError("wholeImageAverage must be a bool")
    signal = payload["signalLevel"]
    if not isinstance(signal, str) or _DECIMAL.fullmatch(signal) is None:
        raise ValueError("signalLevel must be a canonical decimal string")
    return patch_id, patch_class, illumination, average, signal


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-01 must not yield qualified or allowed")
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
