"""TC-P007-07 concurrent collaborator change.

Preserve collaborator content and every profile hash. Identical display names
must not collapse distinct hashes. Resetting collaborator work for a clean
demonstration is blocked and is never allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P007-07"
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_COLLABORATOR_KEYS = (
    "present",
    "preserved",
    "overlapping",
    "remoteHeadChanged",
    "content",
)


def evaluate(payload: object) -> dict:
    """Return the TC-P007-07 decision for a collaborator handoff payload."""
    data = _require_payload(payload, CASE_ID)
    collaborator = _require_mapping(
        data.get("collaborator"), "collaborator", _COLLABORATOR_KEYS
    )
    if "integratedRevision" not in data:
        raise ValueError("invalid payload: missing integratedRevision")
    revision = data["integratedRevision"]
    if not isinstance(revision, str) or revision == "":
        raise ValueError("invalid payload: integratedRevision")
    profiles = _require_profiles(data.get("profiles"))
    present = _require_bool(collaborator, "present")
    preserved_flag = _require_bool(collaborator, "preserved")
    overlapping = _require_bool(collaborator, "overlapping")
    remote_head_changed = _require_bool(collaborator, "remoteHeadChanged")
    content = collaborator["content"]
    hashes = [profile["sha256"] for profile in profiles]

    if not present:
        return _result(
            "unchanged",
            ["no concurrent collaborator change is present"],
            [],
            list(hashes),
            [],
        )

    if not preserved_flag:
        return _result(
            "blocked",
            [
                "resetting or overwriting collaborator work to obtain a clean demonstration is rejected"
            ],
            ["clean-demonstration-reset"],
            [content, *hashes],
            [],
        )

    reasons = ["collaborator modification preserved; exact integrated state reported"]
    if overlapping:
        reasons.append("overlapping assumptions re-evaluated")
    if remote_head_changed:
        reasons.append(
            "remote head changed before push and was reconciled into the integrated state"
        )
    return _result(
        "integrated",
        reasons,
        [],
        [content, revision, *hashes],
        [],
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
