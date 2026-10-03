"""TC-P042-08 profile replacement and rollback.

A revised profile may render forward only as a new explicit result. The
archived recipe and its digest stay put. Overwriting bytes under the same
identifier is rejected.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-08"
INTERVENTION = "Install a revised profile after an existing result has been rendered and archived."
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering "
    "without rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_OPERATIONS = (
    "revise",
    "overwrite_same_id",
    "firmware_change",
    "user_rename",
    "rollback",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_DIGEST = re.compile(r"[0-9a-f]{8,64}")
_PAYLOAD_KEYS = (
    "profileId",
    "priorDigest",
    "newDigest",
    "archivedRecipeId",
    "operation",
    "renameTo",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "explicit_rerender", "provenance_kept", "rolled_back")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Refuse a same-id overwrite."""
    profile, prior, proposed, recipe, operation, rename = _payload(payload)
    preserved = [
        f"recipe:{recipe}",
        f"profile:{profile}",
        f"prior:{prior}",
        f"proposed:{proposed}",
    ]
    if rename is not None:
        preserved.append(f"rename:{rename}")
    if operation == "overwrite_same_id":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "historical provenance was not rewritten"],
            ["same-identifier-overwrite"],
            preserved,
            ["the archived recipe still names the prior digest"],
        )
    if operation in {"revise", "firmware_change"}:
        return _result(
            "explicit_rerender",
            [EXPECTED, INTERVENTION, f"explicit new rendering {proposed}", f"operation {operation}"],
            [],
            preserved,
            ["the archived recipe still names the prior digest"],
        )
    if operation == "user_rename":
        return _result(
            "provenance_kept",
            [EXPECTED, f"rename to {rename} does not retarget the archived recipe"],
            [],
            preserved,
            ["the archived recipe id was not replaced"],
        )
    return _result(
        "rolled_back",
        [EXPECTED, "rollback restores the prior digest without rewriting history"],
        [],
        preserved,
        ["the proposed digest was not written over the archive"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str, str | None]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile = _token(payload["profileId"], "profileId")
    prior = _digest(payload["priorDigest"], "priorDigest")
    proposed = _digest(payload["newDigest"], "newDigest")
    recipe = _token(payload["archivedRecipeId"], "archivedRecipeId")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is not allowed")
    rename = payload["renameTo"]
    if operation == "user_rename":
        if not isinstance(rename, str) or _TOKEN.fullmatch(rename) is None:
            raise ValueError("renameTo must be a token when renaming")
    elif rename is not None:
        raise ValueError("renameTo is only valid for user_rename")
    return profile, prior, proposed, recipe, operation, rename


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{label} must be lowercase hex")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-08 must not yield qualified or allowed")
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
