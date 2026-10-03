"""TC-P051-06 defect versus real highlight.

Intervention: Place a persistent sensor defect beside a real small moving
bright feature.
Expected: Correct only the supported defect and preserve the real scene feature
under the declared policy.
Negative: Removing every isolated bright pixel must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P051-06"
INTERVENTION = (
    "Place a persistent sensor defect beside a real small moving bright feature."
)
EXPECTED = (
    "Correct only the supported defect and preserve the real scene feature under the declared policy."
)
NEGATIVE = "Removing every isolated bright pixel must fail."

_POLICIES = ("defect-only", "remove-isolated-bright")
_FRAME_KEYS = (
    "id",
    "defectX",
    "defectY",
    "defectValue",
    "featureX",
    "featureY",
    "featureValue",
)
_PAYLOAD_KEYS = ("frames", "policy", "nearSaturation")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "feature_preserved")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Correct a persistent defect and keep the moving highlight."""
    frames, policy, near_saturation = _payload(payload)
    preserved = []
    for frame in frames:
        preserved.append(
            f"feature:{frame['id']}:{frame['featureX']},{frame['featureY']}:{frame['featureValue']}"
        )
        preserved.append(f"defect:{frame['id']}:{frame['defectX']},{frame['defectY']}")
    if near_saturation:
        preserved.append("saturated-boundary")
    if policy == "remove-isolated-bright":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "the moving highlight was not removed"],
            ["remove-every-isolated-bright"],
            preserved,
            ["isolated brightness is not a defect label"],
        )
    for frame in frames:
        preserved.append(f"corrected:{frame['id']}")
    return _result(
        "feature_preserved",
        [EXPECTED, "only the persistent defect was corrected"],
        [],
        preserved,
        [],
    )


def _payload(payload: object) -> tuple[list[dict], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frames = payload["frames"]
    if type(frames) is not list or not frames or len(frames) > 8:
        raise ValueError("frames must be a short non-empty list")
    parsed: list[dict] = []
    seen: set[str] = set()
    for item in frames:
        if not isinstance(item, dict) or set(item) != set(_FRAME_KEYS):
            raise ValueError("frame keys drifted")
        ident = item["id"]
        if not isinstance(ident, str) or not ident or ident != ident.strip() or ident in seen:
            raise ValueError("frame id must be a unique non-empty string")
        seen.add(ident)
        parsed.append(
            {
                "id": ident,
                "defectX": _coord(item["defectX"], "defectX"),
                "defectY": _coord(item["defectY"], "defectY"),
                "defectValue": _code(item["defectValue"], "defectValue"),
                "featureX": _coord(item["featureX"], "featureX"),
                "featureY": _coord(item["featureY"], "featureY"),
                "featureValue": _code(item["featureValue"], "featureValue"),
            }
        )
    defect = {(item["defectX"], item["defectY"]) for item in parsed}
    if len(defect) != 1:
        raise ValueError("the defect must stay on one pixel")
    if len(parsed) >= 2:
        feature = {(item["featureX"], item["featureY"]) for item in parsed}
        if len(feature) < 2:
            raise ValueError("the real feature must move across frames")
    policy = payload["policy"]
    if policy not in _POLICIES:
        raise ValueError("policy must be defect-only or remove-isolated-bright")
    near = payload["nearSaturation"]
    if type(near) is not bool:
        raise ValueError("nearSaturation must be a bool")
    return parsed, policy, near


def _coord(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 64:
        raise ValueError(label + " must be an int coordinate")
    return value


def _code(value: object, label: str) -> int:
    if type(value) is not int or not -100000 <= value <= 1000000:
        raise ValueError(label + " must be an int code")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("highlight decision cannot be qualified or allowed")
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
