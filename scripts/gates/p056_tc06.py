"""TC-P056-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene feature
under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P056-06"
INTERVENTION = "Place a persistent sensor defect beside a real small moving bright feature."
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_PAYLOAD_KEYS = (
    "frameIndex",
    "defectId",
    "featureId",
    "defectCorrected",
    "featurePreserved",
    "removeAllIsolated",
    "nearSaturation",
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


def evaluate(payload: dict) -> dict:
    """Correct a supported defect without deleting the real moving highlight."""
    frame, defect, feature, corrected, preserved_feature, remove_all, saturated = _payload(payload)
    preserved = [
        f"frame:{frame}",
        f"defect:{defect}",
        f"feature:{feature}",
        "boundary:saturated" if saturated else "boundary:interior",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"frame {frame} keeps feature {feature}"]
    if remove_all:
        decision = "rejected"
        rejected.append("remove-all-isolated-bright")
        reasons.append(NEGATIVE)
        questions.append("isolated-bright removal was not applied to the real feature")
        if not preserved_feature:
            rejected.append("feature-removed")
    elif not preserved_feature:
        decision = "rejected"
        rejected.append("feature-removed")
        reasons.append("the real scene feature was not preserved")
        questions.append(f"feature {feature} remains in the inventory")
    elif not corrected:
        decision = "withheld"
        reasons.append("the supported defect was not corrected")
        questions.append(f"defect {defect} is still open")
    else:
        decision = "defect-only"
        reasons.append("only the supported defect was corrected")
        questions.append(f"feature {feature} preserved on frame {frame}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int, str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frame = payload["frameIndex"]
    if type(frame) is not int or frame < 0:
        raise ValueError("frameIndex must be a non-negative int")
    defect = payload["defectId"]
    feature = payload["featureId"]
    if not isinstance(defect, str) or _TOKEN.fullmatch(defect) is None:
        raise ValueError("defectId must be a token")
    if not isinstance(feature, str) or _TOKEN.fullmatch(feature) is None:
        raise ValueError("featureId must be a token")
    flags = []
    for name in ("defectCorrected", "featurePreserved", "removeAllIsolated", "nearSaturation"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return frame, defect, feature, flags[0], flags[1], flags[2], flags[3]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-06 must not yield qualified or allowed")
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
