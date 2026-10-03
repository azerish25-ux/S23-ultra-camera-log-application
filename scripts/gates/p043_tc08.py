"""TC-P043-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new rendering
without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P043-08"
INTERVENTION = "Install a revised profile after an existing result has been rendered and archived."
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering "
    "without rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_ACTIONS = ("revise", "overwrite", "rename", "rollback", "firmware-change")
_PAYLOAD_KEYS = (
    "archiveId",
    "previousProfileId",
    "previousRecipe",
    "nextProfileId",
    "nextRecipe",
    "action",
    "rendered",
    "explicitNewRender",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "revision_recorded", "rolled_back", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Same-id overwrites fail."""
    parsed = _payload(payload)
    previous = f"previous:{parsed['previousProfileId']}:{parsed['previousRecipe']}"
    preserved = [f"archive:{parsed['archiveId']}", previous]
    same_id = parsed["previousProfileId"] == parsed["nextProfileId"]
    questions = ["historical recipe identity was not rewritten"]
    if parsed["action"] == "overwrite" or (same_id and parsed["action"] != "rollback"):
        decision = "rejected"
        rejected = ["overwrite-same-identifier"]
        preserved.append(f"refused:{parsed['nextProfileId']}:{parsed['nextRecipe']}")
        reasons = [NEGATIVE, EXPECTED, "earlier recipe preserved"]
        return _result(decision, reasons, rejected, preserved, questions)
    if not parsed["rendered"]:
        decision = "withheld"
        preserved.append(f"next:{parsed['nextProfileId']}:{parsed['nextRecipe']}")
        reasons = ["nothing archived yet", "earlier recipe preserved"]
        questions.append("revision waits for an archived render")
        return _result(decision, reasons, [], preserved, questions)
    if parsed["action"] == "rollback":
        if parsed["nextRecipe"] != parsed["previousRecipe"] or not same_id:
            decision = "rejected"
            rejected = ["rollback-changed-bytes"]
            preserved.append(f"refused:{parsed['nextProfileId']}:{parsed['nextRecipe']}")
            reasons = [EXPECTED, "rollback refused because the approved recipe changed"]
            return _result(decision, reasons, rejected, preserved, questions)
        decision = "rolled_back"
        reasons = [EXPECTED, "previous approved profile restored without a new archive identity"]
        questions.append("rollback does not erase the archive id")
        return _result(decision, reasons, [], preserved, questions)
    if not parsed["explicitNewRender"]:
        decision = "rejected"
        rejected = ["implicit-replacement"]
        preserved.append(f"refused:{parsed['nextProfileId']}:{parsed['nextRecipe']}")
        reasons = [EXPECTED, "new rendering was not explicit", "earlier recipe preserved"]
        return _result(decision, reasons, rejected, preserved, questions)
    decision = "revision_recorded"
    preserved.append(f"next:{parsed['nextProfileId']}:{parsed['nextRecipe']}")
    reasons = [EXPECTED, f"explicit {parsed['action']} kept the archived recipe"]
    questions.append(f"new-render:{parsed['action']}")
    return _result(decision, reasons, [], preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    action = payload["action"]
    if action not in _ACTIONS:
        raise ValueError("action is not a known profile action")
    for label in ("rendered", "explicitNewRender"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    return {
        "archiveId": _text(payload["archiveId"], "archiveId"),
        "previousProfileId": _text(payload["previousProfileId"], "previousProfileId"),
        "previousRecipe": _text(payload["previousRecipe"], "previousRecipe"),
        "nextProfileId": _text(payload["nextProfileId"], "nextProfileId"),
        "nextRecipe": _text(payload["nextRecipe"], "nextRecipe"),
        "action": action,
        "rendered": payload["rendered"],
        "explicitNewRender": payload["explicitNewRender"],
    }


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
