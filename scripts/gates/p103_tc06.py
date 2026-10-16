"""TC-P103-06 Stale depth result.

Host fixture. A float array without temporal and geometric identity is not accepted.
"""

from __future__ import annotations

CASE_ID = "TC-P103-06"
NAME = "Stale depth result"
INTERVENTION = "Delay inference until its result no longer matches the current source timestamp or crop."
EXPECTED = "Reject or explicitly reproject the result under a validated policy rather than applying it blindly."
NEGATIVE = "A float array without temporal and geometric identity must not be accepted."
REPEAT = "Repeat rapid camera movement, rotation, source switches, and scene cuts."
NEGATIVE_TOKEN = "float-array-without-temporal-geometric-identity"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "hasTemporalIdentity",
    "hasGeometricIdentity",
    "timestampsMatch",
    "cropMatches",
    "reprojected",
    "reprojectionPolicyValidated",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    for name in (
        "applyNegative",
        "applyMutant",
        "hasTemporalIdentity",
        "hasGeometricIdentity",
        "timestampsMatch",
        "cropMatches",
        "reprojected",
        "reprojectionPolicyValidated",
    ):
        _bool(payload[name], name)
    missing_identity = not payload["hasTemporalIdentity"] or not payload["hasGeometricIdentity"]
    validated_reprojection = payload["reprojected"] is True and payload["reprojectionPolicyValidated"] is True
    blind_accept = missing_identity and not validated_reprojection
    stale = (not payload["timestampsMatch"] or not payload["cropMatches"]) and not validated_reprojection
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"temporal={payload['hasTemporalIdentity']}; geometric={payload['hasGeometricIdentity']}",
        f"timestampsMatch={payload['timestampsMatch']}; cropMatches={payload['cropMatches']}",
        f"reprojected={payload['reprojected']}; policyValidated={payload['reprojectionPolicyValidated']}",
    ]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"] or blind_accept:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if stale and NEGATIVE_TOKEN not in rejected:
        rejected.append("stale-depth-applied-without-validated-reprojection")
        reasons.append("stale depth was not rejected or reprojected under a validated policy")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if validated_reprojection:
            reasons.append("stale depth explicitly reprojected under a validated policy")
        else:
            reasons.append("depth result matches the current timestamp and crop")
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
