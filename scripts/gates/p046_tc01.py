"""TC-P046-01 neutral target invalidity.

Intervention: Replace the approved neutral patch with a clipped, textured,
specular, or incorrectly identified region.
Expected: Reject scale calibration or retain an explicitly provisional result
rather than fabricating a measured profile.
Negative: Whole-image average brightness cannot substitute for a known neutral
target.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, or "
    "incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result rather than "
    "fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_REGIONS = (
    "approved",
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "dark",
    "colored",
    "mixed-pixels",
    "partial-clip",
)
_PAYLOAD_KEYS = ("patchId", "region", "wholeImageAverage", "provisional", "meanChannels")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Reject a bad neutral, or keep an explicit provisional result."""
    patch_id, region, whole, provisional, mean = _payload(payload)
    preserved = [
        f"patch:{patch_id}",
        f"region:{region}",
        f"mean:{mean[0]},{mean[1]},{mean[2]}",
        f"provisional:{str(provisional).lower()}",
        f"whole-image-average:{str(whole).lower()}",
    ]
    reasons = [EXPECTED]
    rejected: list[str] = []
    questions: list[str] = []
    if whole:
        decision = "rejected"
        rejected.append("whole-image-average")
        if region != "approved":
            rejected.append(f"region:{region}")
        reasons.append(NEGATIVE)
        questions.append("whole-image average is not a neutral target")
    elif region != "approved" and not provisional:
        decision = "rejected"
        rejected.append(f"region:{region}")
        reasons.append(f"scale calibration rejected for region {region}")
        questions.append("neutral target invalid")
    elif provisional:
        decision = "provisional"
        reasons.append("explicitly provisional result is not a measured profile")
        questions.append("result is provisional and is not a measured profile")
    else:
        decision = "withheld"
        reasons.append("scale calibration withheld; no measured profile was fabricated")
        questions.append("approved patch does not by itself fabricate a measured profile")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, list[int]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    patch_id = payload["patchId"]
    if not isinstance(patch_id, str) or _TOKEN.fullmatch(patch_id) is None:
        raise ValueError("patchId must be a token")
    region = payload["region"]
    if region not in _REGIONS:
        raise ValueError("region is unknown")
    whole = payload["wholeImageAverage"]
    provisional = payload["provisional"]
    if type(whole) is not bool or type(provisional) is not bool:
        raise ValueError("wholeImageAverage and provisional must be bools")
    mean = payload["meanChannels"]
    if (
        not isinstance(mean, list)
        or len(mean) != 3
        or any(type(item) is not int for item in mean)
    ):
        raise ValueError("meanChannels must be three ints")
    return patch_id, region, whole, provisional, list(mean)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("neutral decision cannot be qualified or allowed")
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
