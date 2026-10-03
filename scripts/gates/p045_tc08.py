"""TC-P045-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new rendering
without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P045-08"
INTERVENTION = (
    "Install a revised profile after an existing result has been rendered and archived."
)
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering "
    "without rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_PAYLOAD_KEYS = (
    "archivedRecipeId",
    "newProfileId",
    "archivedBytes",
    "newBytes",
    "overwriteSameId",
    "firmwareChanged",
    "userRename",
    "rollback",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_BYTES = re.compile(r"[0-9a-f]{2,64}")


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Same-identifier overwrites are rejected."""
    archived, new_id, archived_bytes, new_bytes, overwrite, firmware, rename, rollback = _payload(
        payload
    )
    preserved = [
        f"archived:{archived}",
        f"archived-bytes:{archived_bytes}",
        f"new:{new_id}",
        f"new-bytes:{new_bytes}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions: list[str] = []
    same_id = overwrite or archived == new_id
    if same_id:
        decision = "rejected"
        rejected = ["same-identifier-overwrite"]
        reasons.append(NEGATIVE)
        reasons.append("archived recipe bytes were not replaced")
        questions.append("historical provenance was kept")
    elif rollback:
        decision = "rolled_back"
        rejected = []
        reasons.append("rollback keeps the earlier recipe identity")
        questions.append("rollback does not rewrite the archived render")
    else:
        decision = "explicit_render"
        rejected = []
        reasons.append("explicit new rendering leaves historical provenance in place")
        questions.append("new render is not a physical S23 qualification")
    if firmware and not same_id:
        reasons.append("firmware change uses a distinct profile id")
    if rename and not same_id:
        reasons.append("user rename does not rewrite the archived recipe identity")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    archived = payload["archivedRecipeId"]
    new_id = payload["newProfileId"]
    for name, value in (("archivedRecipeId", archived), ("newProfileId", new_id)):
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(f"{name} must be a token")
    archived_bytes = payload["archivedBytes"]
    new_bytes = payload["newBytes"]
    for name, value in (("archivedBytes", archived_bytes), ("newBytes", new_bytes)):
        if not isinstance(value, str) or _BYTES.fullmatch(value) is None:
            raise ValueError(f"{name} must be lowercase hex")
    overwrite = payload["overwriteSameId"]
    firmware = payload["firmwareChanged"]
    rename = payload["userRename"]
    rollback = payload["rollback"]
    for name, value in (
        ("overwriteSameId", overwrite),
        ("firmwareChanged", firmware),
        ("userRename", rename),
        ("rollback", rollback),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    return archived, new_id, archived_bytes, new_bytes, overwrite, firmware, rename, rollback


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-08 must not yield qualified or allowed")
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
