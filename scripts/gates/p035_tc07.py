"""TC-P035-07 source mutation during development.

Intervention: Alter the source or profile while a development job is reading it.
Expected: Detect identity inconsistency, stop accepted publication, and preserve
all available evidence without overwriting originals.
Negative: A successful result whose source changed unnoticed must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P035-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all available "
    "evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."

MUTATIONS = ("none", "renamed", "changed_bytes", "replaced_profile", "revoked_read")
_PAYLOAD_KEYS = (
    "mutation",
    "sourceBefore",
    "sourceDuring",
    "profileBefore",
    "profileDuring",
    "nameBefore",
    "nameDuring",
    "publish",
    "noticed",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "stopped", "consistent")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop publication when identity changes. Original hashes stay in the result."""
    mutation, source_before, source_during, profile_before, profile_during, name_before, name_during, publish, noticed = _payload(
        payload
    )
    preserved = [
        f"source-before:{source_before}",
        f"source-during:{source_during}",
        f"profile-before:{profile_before}",
        f"profile-during:{profile_during}",
        f"name-before:{name_before}",
        f"name-during:{name_during}",
    ]
    if mutation != "none" and not noticed:
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "an unnoticed source change is not a successful result"],
            ["unnoticed-mutation"],
            preserved,
            ["publication not accepted"],
        )
    if mutation != "none":
        claims = ["publication-blocked"] if publish else []
        return _result(
            "stopped",
            [EXPECTED, f"{mutation} stopped accepted publication"],
            claims,
            preserved,
            ["originals preserved"],
        )
    return _result(
        "consistent",
        [EXPECTED, "identity was unchanged; this is not physical S23 qualification"],
        [],
        preserved,
        ["consistent identity is not a measured profile"],
    )


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label)
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    mutation = payload["mutation"]
    if mutation not in MUTATIONS:
        raise ValueError("mutation")
    source_before = _text(payload["sourceBefore"], "sourceBefore")
    source_during = _text(payload["sourceDuring"], "sourceDuring")
    profile_before = _text(payload["profileBefore"], "profileBefore")
    profile_during = _text(payload["profileDuring"], "profileDuring")
    name_before = _text(payload["nameBefore"], "nameBefore")
    name_during = _text(payload["nameDuring"], "nameDuring")
    publish = payload["publish"]
    noticed = payload["noticed"]
    if type(publish) is not bool or type(noticed) is not bool:
        raise ValueError("flags")
    if mutation == "none":
        if not noticed:
            raise ValueError("an unchanged source is not an unnoticed mutation")
        if source_before != source_during or profile_before != profile_during or name_before != name_during:
            raise ValueError("none requires unchanged identity")
    if mutation == "renamed" and name_before == name_during:
        raise ValueError("renamed requires a different name")
    if mutation == "changed_bytes" and source_before == source_during:
        raise ValueError("changed_bytes requires a different source hash")
    if mutation == "replaced_profile" and profile_before == profile_during:
        raise ValueError("replaced_profile requires a different profile hash")
    return (
        mutation,
        source_before,
        source_during,
        profile_before,
        profile_during,
        name_before,
        name_during,
        publish,
        noticed,
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("mutation decision cannot be qualified or allowed")
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
