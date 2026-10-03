"""TC-P046-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new rendering
without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-08"
INTERVENTION = (
    "Install a revised profile after an existing result has been rendered and archived."
)
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering without "
    "rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_ACTIONS = ("install", "firmware", "rename", "rollback")
_PAYLOAD_KEYS = (
    "archivedId",
    "archivedDigest",
    "archivedRecipe",
    "installedId",
    "installedDigest",
    "overwriteSameId",
    "action",
    "previousApprovedId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provenance_kept", "rolled_back")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[a-z0-9-]+$")
_DIGEST = re.compile(r"^[0-9a-f]{8}$")


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Refuse same-identifier byte overwrites."""
    (
        archived_id,
        archived_digest,
        recipe,
        installed_id,
        installed_digest,
        overwrite,
        action,
        previous,
    ) = _payload(payload)
    preserved = [
        f"archived:{archived_id}:{archived_digest}",
        f"recipe:{recipe}",
        f"installed:{installed_id}:{installed_digest}",
        f"action:{action}",
        f"previous:{previous}",
    ]
    rewritten = installed_id == archived_id and installed_digest != archived_digest
    reasons = [EXPECTED]
    if overwrite or rewritten:
        decision = "rejected"
        rejected = ["same-identifier-overwrite"]
        reasons.append(NEGATIVE)
        questions = ["historical provenance was not rewritten"]
    elif action == "rollback":
        if installed_id == previous:
            decision = "rolled_back"
            rejected = []
            reasons.append(f"rollback to {previous} leaves archived recipe unchanged")
            questions = []
        else:
            decision = "rejected"
            rejected = ["rollback-target-mismatch"]
            reasons.append("rollback target does not match the previous approved profile")
            questions = ["historical provenance was not rewritten"]
    elif installed_id == archived_id:
        decision = "rejected"
        rejected = ["identifier-reused"]
        reasons.append("new rendering reused the archived identifier")
        questions = ["historical provenance was not rewritten"]
    else:
        decision = "provenance_kept"
        rejected = []
        reasons.append(
            f"explicit new rendering {installed_id} leaves archived {archived_id} unchanged"
        )
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    archived_id = _token(payload["archivedId"], "archivedId")
    installed_id = _token(payload["installedId"], "installedId")
    previous = _token(payload["previousApprovedId"], "previousApprovedId")
    recipe = _token(payload["archivedRecipe"], "archivedRecipe")
    archived_digest = _digest(payload["archivedDigest"], "archivedDigest")
    installed_digest = _digest(payload["installedDigest"], "installedDigest")
    overwrite = payload["overwriteSameId"]
    if type(overwrite) is not bool:
        raise ValueError("overwriteSameId must be a bool")
    action = payload["action"]
    if action not in _ACTIONS:
        raise ValueError("action is unknown")
    return (
        archived_id,
        archived_digest,
        recipe,
        installed_id,
        installed_digest,
        overwrite,
        action,
        previous,
    )


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(label + " must be a lowercase token")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(label + " must be 8 lowercase hex characters")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("profile decision cannot be qualified or allowed")
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
