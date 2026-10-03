"""TC-P044-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new rendering
without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P044-08"
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
    "archivedRecipeId",
    "revisedRecipeId",
    "sameIdentifier",
    "overwriteBytes",
    "action",
    "renderedId",
    "historicalProvenance",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = (
    "rejected",
    "explicit_new_render",
    "firmware_noted",
    "renamed_explicit",
    "rolled_back",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Same-identifier overwrite fails."""
    archived, revised, same, overwrite, action, rendered, provenance = _payload(payload)
    preserved = [
        f"archived:{archived}",
        f"revised:{revised}",
        f"rendered:{rendered}",
        f"provenance:{provenance}",
        f"action:{action}",
    ]
    reasons = [EXPECTED, "historical provenance was not rewritten"]
    if overwrite or (same and action != "rollback"):
        decision = "rejected"
        rejected = ["identifier-overwrite"]
        reasons.append(NEGATIVE)
        questions = ["archived recipe identity remains intact"]
    elif action == "rollback":
        decision = "rolled_back"
        rejected = []
        reasons.append("rollback kept the earlier recipe identity")
        questions = ["explicit rollback kept the earlier recipe identity"]
    elif action == "rename":
        decision = "renamed_explicit"
        rejected = []
        reasons.append("rename left historical provenance unchanged")
        questions = ["rename did not rewrite historical provenance"]
    elif action == "firmware":
        decision = "firmware_noted"
        rejected = []
        reasons.append("firmware change left the archived recipe identity intact")
        questions = ["firmware change left the archived recipe identity intact"]
    else:
        decision = "explicit_new_render"
        rejected = []
        reasons.append("new rendering is explicit")
        questions = ["new rendering is explicit and historical provenance stands"]
    if f"provenance:{revised}" in preserved and revised != provenance:
        pass
    if preserved[3] != f"provenance:{provenance}":
        raise ValueError("historical provenance was rewritten")
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _payload(payload: object) -> tuple[str, str, bool, bool, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    archived = _text(payload["archivedRecipeId"], "archivedRecipeId")
    revised = _text(payload["revisedRecipeId"], "revisedRecipeId")
    same = payload["sameIdentifier"]
    overwrite = payload["overwriteBytes"]
    if type(same) is not bool or type(overwrite) is not bool:
        raise ValueError("sameIdentifier and overwriteBytes must be bools")
    if same and archived != revised:
        raise ValueError("sameIdentifier requires equal recipe ids")
    if not same and archived == revised:
        raise ValueError("distinct recipes must not share an identifier")
    action = payload["action"]
    if action not in _ACTIONS:
        raise ValueError("action is unknown")
    rendered = _text(payload["renderedId"], "renderedId")
    provenance = _text(payload["historicalProvenance"], "historicalProvenance")
    return archived, revised, same, overwrite, action, rendered, provenance


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
