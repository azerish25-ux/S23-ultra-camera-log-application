"""TC-P017-01 late callback generation.

A successful callback from a previous camera or recording generation does not
mutate the current owner. Only the stale operation's resources are named for
release. Resurrecting recording or attaching an obsolete surface is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P017-01"
INTERVENTION = (
    "Deliver a successful callback from a previous camera or recording generation "
    "after the current owner has changed."
)
EXPECTED = (
    "Ignore stale state mutation and release only resources owned by the stale operation."
)
NEGATIVE = (
    "A delayed callback that resurrects recording or attaches an obsolete surface must fail."
)
STAGES = (
    "before_first_sample",
    "during_stopping",
    "after_activity_recreation",
    "after_camera_reopen",
)
_PAYLOAD_KEYS = (
    "stage",
    "callbackGeneration",
    "currentGeneration",
    "resurrectRecording",
    "attachObsoleteSurface",
    "staleResourceIds",
    "currentResourceIds",
    "activePreview",
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
    """Ignore a stale generation. Negative controls are rejected, never allowed."""
    data = _payload(payload)
    reasons = [
        f"stage {data['stage']}",
        INTERVENTION,
        EXPECTED,
    ]
    rejected: list[str] = []
    stale = data["callbackGeneration"] != data["currentGeneration"]
    if stale:
        reasons.append("ignore stale state mutation")
        listed = ",".join(data["staleResourceIds"])
        reasons.append("release only resources owned by the stale operation: " + listed)
    else:
        reasons.append("callback generation matches the current owner")
    if data["resurrectRecording"]:
        rejected.append("resurrect-recording")
    if data["attachObsoleteSurface"]:
        rejected.append("attach-obsolete-surface")
    if rejected:
        reasons.append(NEGATIVE)
        decision = "rejected"
    elif stale:
        decision = "stale_ignored"
    else:
        decision = "current_owner"
    preserved = list(data["currentResourceIds"])
    if data["activePreview"] not in preserved:
        raise ValueError("active preview missing from preserved results")
    if any(item in preserved for item in data["staleResourceIds"]):
        raise ValueError("stale resources must not be preserved as current")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage is not a TC-P017-01 repeat")
    callback_gen = _generation(payload["callbackGeneration"], "callbackGeneration")
    current_gen = _generation(payload["currentGeneration"], "currentGeneration")
    resurrect = _bool(payload["resurrectRecording"], "resurrectRecording")
    attach = _bool(payload["attachObsoleteSurface"], "attachObsoleteSurface")
    stale_ids = _ids(payload["staleResourceIds"], "staleResourceIds")
    current_ids = _ids(payload["currentResourceIds"], "currentResourceIds")
    if not current_ids:
        raise ValueError("currentResourceIds must be non-empty")
    overlap = set(stale_ids) & set(current_ids)
    if overlap:
        raise ValueError("stale and current resource ids overlap")
    preview = payload["activePreview"]
    if not isinstance(preview, str) or not preview or preview != preview.strip():
        raise ValueError("activePreview must be a non-empty string")
    if preview not in current_ids:
        raise ValueError("activePreview must be a current resource")
    return {
        "stage": stage,
        "callbackGeneration": callback_gen,
        "currentGeneration": current_gen,
        "resurrectRecording": resurrect,
        "attachObsoleteSurface": attach,
        "staleResourceIds": stale_ids,
        "currentResourceIds": current_ids,
        "activePreview": preview,
    }


def _generation(value: object, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _ids(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(f"{name} entries must be non-empty strings")
        if item in seen:
            raise ValueError(f"{name} entries must be unique")
        seen.add(item)
    return list(value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P017-01 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
