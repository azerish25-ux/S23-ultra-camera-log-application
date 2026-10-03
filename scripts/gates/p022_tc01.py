"""TC-P022-01 late callback generation.

Deliver a successful callback from a previous camera or recording generation
after the current owner has changed. Ignore stale state mutation and release
only resources owned by the stale operation. A delayed callback that
resurrects recording or attaches an obsolete surface must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-01"
INTERVENTION = (
    "Deliver a successful callback from a previous camera or recording generation "
    "after the current owner has changed."
)
EXPECTED = "Ignore stale state mutation and release only resources owned by the stale operation."
NEGATIVE = "A delayed callback that resurrects recording or attaches an obsolete surface must fail."
STAGES = (
    "before_first_sample",
    "during_stopping",
    "after_activity_recreation",
    "after_camera_reopen",
)
_PAYLOAD_KEYS = (
    "currentOwner",
    "callbackGeneration",
    "stage",
    "resurrectsRecording",
    "attachesObsoleteSurface",
    "staleResources",
    "currentResources",
    "cleanMasterHash",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Ignore a stale generation. Reject resurrection and obsolete surfaces."""
    data = _payload(payload)
    reasons = [
        f"stage {data['stage']}",
        f"callback {data['callbackGeneration']} current {data['currentOwner']}",
    ]
    rejected: list[str] = []
    if data["resurrectsRecording"]:
        rejected.append("resurrected-recording")
        reasons.append("delayed callback must not resurrect recording")
    if data["attachesObsoleteSurface"]:
        rejected.append("obsolete-surface")
        reasons.append("delayed callback must not attach an obsolete surface")
    stale = data["callbackGeneration"] != data["currentOwner"]
    if rejected:
        decision = "rejected"
    elif stale:
        decision = "stale_ignored"
        released = ", ".join(data["staleResources"]) if data["staleResources"] else "none"
        reasons.append("released stale resources: " + released)
        reasons.append("current owner state was not mutated")
    else:
        decision = "owner_matched"
        reasons.append("callback generation matches the current owner")
    preserved = list(data["currentResources"]) + [data["cleanMasterHash"]]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    current = _token(payload["currentOwner"], "currentOwner")
    callback = _token(payload["callbackGeneration"], "callbackGeneration")
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage is not a declared repeat")
    resurrect = _bool(payload["resurrectsRecording"], "resurrectsRecording")
    obsolete = _bool(payload["attachesObsoleteSurface"], "attachesObsoleteSurface")
    stale = _tokens(payload["staleResources"], "staleResources")
    current_resources = _tokens(payload["currentResources"], "currentResources")
    if set(stale) & set(current_resources):
        raise ValueError("stale and current resources must be disjoint")
    clean = _token(payload["cleanMasterHash"], "cleanMasterHash")
    return {
        "currentOwner": current,
        "callbackGeneration": callback,
        "stage": stage,
        "resurrectsRecording": resurrect,
        "attachesObsoleteSurface": obsolete,
        "staleResources": stale,
        "currentResources": current_resources,
        "cleanMasterHash": clean,
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    items = []
    for item in value:
        items.append(_token(item, name))
    if len(items) != len(set(items)):
        raise ValueError(f"{name} must be unique")
    return items


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P022-01 must not yield qualified or allowed")
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
