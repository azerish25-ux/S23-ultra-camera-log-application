"""TC-P048-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new
rendering without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P048-08"
INTERVENTION = (
    "Install a revised profile after an existing result has been rendered and archived."
)
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering without rewriting "
    "historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_EVENTS = ("install", "firmware", "rename", "rollback")
_PAYLOAD_KEYS = (
    "profileId",
    "revisedId",
    "priorBytes",
    "nextBytes",
    "recipeId",
    "event",
    "overwriteSameId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "new_development", "versioned", "renamed", "rolled_back")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Same-identifier byte replacement fails."""
    profile_id, revised_id, prior, nxt, recipe, event, overwrite = _payload(payload)
    preserved = [
        f"recipe:{recipe}",
        f"prior-bytes:{prior}",
        f"next-bytes:{nxt}",
        f"profile:{profile_id}",
        f"event:{event}",
    ]
    reasons = [EXPECTED]
    if overwrite:
        decision = "rejected"
        rejected = ["same-identifier-overwrite"]
        reasons.append(NEGATIVE)
        questions = ["historical recipe identity was kept"]
    elif event == "rollback":
        decision = "rolled_back"
        rejected = []
        preserved.append(f"approved:{profile_id}")
        reasons.append("rollback restored the previous approved profile without rewriting provenance")
        questions = ["rollback did not overwrite the archived recipe"]
    elif event == "rename":
        decision = "renamed"
        rejected = []
        preserved.append(f"revised-id:{revised_id}")
        reasons.append("user rename did not change the archived recipe identity")
        questions = ["rename is not an in-place byte replacement"]
    elif event == "firmware":
        decision = "versioned"
        rejected = []
        preserved.append(f"revised-id:{revised_id}")
        reasons.append("firmware change created a new development version")
        questions = ["firmware change did not rewrite the archived recipe"]
    else:
        decision = "new_development"
        rejected = []
        preserved.append(f"revised-id:{revised_id}")
        reasons.append("explicit new rendering left historical provenance unchanged")
        questions = ["new development version is not a replacement of the archived recipe"]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _payload(payload: object) -> tuple[str, str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    profile_id = _text(payload["profileId"], "profileId")
    revised_id = _text(payload["revisedId"], "revisedId")
    prior = _text(payload["priorBytes"], "priorBytes")
    nxt = _text(payload["nextBytes"], "nextBytes")
    recipe = _text(payload["recipeId"], "recipeId")
    event = payload["event"]
    if event not in _EVENTS:
        raise ValueError("event is unknown")
    overwrite = payload["overwriteSameId"]
    if type(overwrite) is not bool:
        raise ValueError("overwriteSameId must be a bool")
    if overwrite:
        if revised_id != profile_id:
            raise ValueError("overwrite keeps the same identifier")
    elif event == "rollback":
        if revised_id != profile_id or nxt != prior:
            raise ValueError("rollback returns the previous bytes under the previous identifier")
    elif revised_id == profile_id:
        raise ValueError("a new development version needs a new identifier")
    return profile_id, revised_id, prior, nxt, recipe, event, overwrite


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("profile-lifecycle decision cannot be qualified or allowed")
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
