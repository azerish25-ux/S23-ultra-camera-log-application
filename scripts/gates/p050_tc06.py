"""TC-P050-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene feature
under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P050-06"
INTERVENTION = (
    "Place a persistent sensor defect beside a real small moving bright feature."
)
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the "
    "declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_PAYLOAD_KEYS = (
    "frameCount",
    "defectX",
    "defectY",
    "featureX",
    "featureY",
    "featureMoving",
    "saturated",
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
_DECISIONS = ("rejected", "defect_only")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Correct a persistent defect only. A moving highlight stays in the frame."""
    fields = _payload(payload)
    preserved = [
        f"frames:{fields['frameCount']}",
        f"defect:{fields['defectX']},{fields['defectY']}",
        f"feature:{fields['featureX']},{fields['featureY']}",
        f"moving:{str(fields['featureMoving']).lower()}",
        f"saturated:{str(fields['saturated']).lower()}",
    ]
    if fields["removeAllIsolated"]:
        reasons = [
            EXPECTED,
            NEGATIVE,
            "isolated-bright removal would delete the scene feature",
        ]
        return _result(
            "rejected",
            reasons,
            ["remove-every-isolated-bright"],
            preserved,
            ["feature was not removed"],
        )
    if not fields["featureMoving"]:
        reasons = [EXPECTED, "real scene feature is not a supported defect"]
        return _result(
            "rejected",
            reasons,
            ["feature-not-distinguished"],
            preserved,
            ["static bright pixel was not treated as a defect"],
        )
    reasons = [
        EXPECTED,
        "corrected only the persistent defect",
        "moving bright feature preserved",
    ]
    if fields["saturated"]:
        reasons.append("saturated boundary did not expand the defect mask")
    return _result("defect_only", reasons, [], preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frames = payload["frameCount"]
    if type(frames) is not int or frames < 2 or frames > 32:
        raise ValueError("frameCount must be an int from 2 through 32")
    coords = {}
    for key in ("defectX", "defectY", "featureX", "featureY"):
        value = payload[key]
        if type(value) is not int or value < 0 or value > 64:
            raise ValueError(key + " must be an int from 0 through 64")
        coords[key] = value
    if (coords["defectX"], coords["defectY"]) == (coords["featureX"], coords["featureY"]):
        raise ValueError("defect and feature must be different pixels")
    moving = payload["featureMoving"]
    saturated = payload["saturated"]
    remove_all = payload["removeAllIsolated"]
    for label, value in (
        ("featureMoving", moving),
        ("saturated", saturated),
        ("removeAllIsolated", remove_all),
    ):
        if type(value) is not bool:
            raise ValueError(label + " must be a bool")
    return {
        "frameCount": frames,
        **coords,
        "featureMoving": moving,
        "saturated": saturated,
        "removeAllIsolated": remove_all,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("defect decision cannot be qualified or allowed")
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
