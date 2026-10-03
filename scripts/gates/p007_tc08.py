"""TC-P007-08 independent reproduction.

Reproduce a stated software result, or keep it unverified when undocumented
files, manual intervention, or a missing prerequisite are required. Distinct
profile hashes are always preserved. Temporary paths and phone connection do
not invent success. Unknown-rights images are not this case.
"""

from __future__ import annotations

CASE_ID = "TC-P007-08"
_PHYSICAL_OPEN = "physical S23 qualification remains open"
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_REPRODUCTION_KEYS = (
    "undocumentedFiles",
    "manualIntervention",
    "missingPrerequisite",
    "phoneConnected",
)


def evaluate(payload: object) -> dict:
    """Return the TC-P007-08 decision for an independent reproduction payload."""
    data = _require_payload(payload, CASE_ID)
    reproduction = _require_mapping(
        data.get("reproduction"), "reproduction", _REPRODUCTION_KEYS
    )
    if "statedSoftwareResult" not in data:
        raise ValueError("invalid payload: missing statedSoftwareResult")
    stated = data["statedSoftwareResult"]
    if not isinstance(stated, str) or stated == "":
        raise ValueError("invalid payload: statedSoftwareResult")
    if "tempPath" not in data or not isinstance(data["tempPath"], str):
        raise ValueError("invalid payload: tempPath")
    profiles = _require_profiles(data.get("profiles"))
    undocumented = _require_bool(reproduction, "undocumentedFiles")
    manual = _require_bool(reproduction, "manualIntervention")
    # Accepted and ignored: a connected phone must not change the decision.
    _require_bool(reproduction, "phoneConnected")
    missing = reproduction["missingPrerequisite"]
    if missing is not None and not isinstance(missing, str):
        raise ValueError("invalid payload: missingPrerequisite")
    if isinstance(missing, str) and missing == "":
        raise ValueError("invalid payload: missingPrerequisite")
    hashes = [profile["sha256"] for profile in profiles]
    preserved = [stated, *hashes]

    reasons: list[str] = []
    rejected: list[str] = []
    if undocumented:
        reasons.append("undocumented files keep the result unverified")
        rejected.append("undocumented-files")
    if manual:
        reasons.append("unrecorded manual intervention keeps the result unverified")
        rejected.append("unrecorded-manual-intervention")
    if missing is not None:
        reasons.append("missing prerequisite keeps the result unverified")
        rejected.append("missing-prerequisite")
    if reasons:
        questions = [missing] if missing is not None else []
        return _result("unverified", reasons, rejected, preserved, questions)

    return _result(
        "reproduced",
        [
            "stated software result reproduced without undocumented files or manual intervention"
        ],
        [],
        preserved,
        [_PHYSICAL_OPEN],
    )


def _require_payload(payload: object, case_id: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("invalid payload")
    if payload.get("caseId") != case_id:
        raise ValueError("caseId wrong")
    return payload


def _require_mapping(value: object, label: str, keys: tuple[str, ...]) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"invalid payload: {label}")
    missing = [key for key in keys if key not in value]
    if missing:
        raise ValueError(f"invalid payload: {label} missing {', '.join(missing)}")
    return value


def _require_bool(mapping: dict, key: str) -> bool:
    value = mapping[key]
    if type(value) is not bool:
        raise ValueError(f"invalid payload: {key}")
    return value


def _require_profiles(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("invalid payload: profiles")
    profiles: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"invalid payload: profiles[{index}]")
        name = item.get("displayName")
        digest = item.get("sha256")
        if not isinstance(name, str) or name == "":
            raise ValueError(f"invalid payload: profiles[{index}].displayName")
        if not isinstance(digest, str) or digest == "":
            raise ValueError(f"invalid payload: profiles[{index}].sha256")
        profiles.append({"displayName": name, "sha256": digest})
    return profiles


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list,
    questions: list,
) -> dict:
    if decision in {"allowed", "passed"}:
        raise ValueError("invalid decision")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("result keys")
    return result
