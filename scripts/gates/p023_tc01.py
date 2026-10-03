"""TC-P023-01 late callback generation.

A successful callback from a previous camera or recording generation must not
mutate the current owner. Only resources owned by the stale operation may be
released. Resurrecting recording or attaching an obsolete surface fails.
"""

from __future__ import annotations

CASE_ID = "TC-P023-01"
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
MOMENTS = (
    "before_first_sample",
    "during_stopping",
    "after_activity_recreation",
    "after_camera_reopen",
)
_PAYLOAD_KEYS = (
    "moment",
    "ownerGeneration",
    "callbackGeneration",
    "resurrectsRecording",
    "attachesObsoleteSurface",
    "releasesOnlyStaleResources",
    "currentTakeId",
    "staleResourceId",
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
    """Ignore a previous-generation callback. Negative controls are rejected."""
    fields = _payload(payload)
    reasons = [
        f"moment {fields['moment']} owner {fields['ownerGeneration']} "
        f"callback {fields['callbackGeneration']}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    if fields["resurrectsRecording"]:
        rejected.append("resurrected-recording")
    if fields["attachesObsoleteSurface"]:
        rejected.append("obsolete-surface")
    if not fields["releasesOnlyStaleResources"]:
        rejected.append("released-current-owner-resources")

    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("stale callback must not mutate the current owner")
    else:
        decision = "ignored"
        reasons.append(EXPECTED)
        reasons.append("stale state mutation ignored; only the stale resource may be released")

    preserved = [fields["currentTakeId"], fields["staleResourceId"]]
    open_questions: list[str] = []
    if fields["moment"] in {"after_activity_recreation", "after_camera_reopen"}:
        open_questions.append("recreation does not transfer ownership to a stale callback")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    moment = payload["moment"]
    if moment not in MOMENTS:
        raise ValueError("moment is not a TC-P023-01 repeat")
    owner = _generation(payload["ownerGeneration"], "ownerGeneration")
    callback = _generation(payload["callbackGeneration"], "callbackGeneration")
    if owner < 1 or callback >= owner:
        raise ValueError("callbackGeneration must be a previous generation")
    return {
        "moment": moment,
        "ownerGeneration": owner,
        "callbackGeneration": callback,
        "resurrectsRecording": _bool(payload["resurrectsRecording"], "resurrectsRecording"),
        "attachesObsoleteSurface": _bool(payload["attachesObsoleteSurface"], "attachesObsoleteSurface"),
        "releasesOnlyStaleResources": _bool(
            payload["releasesOnlyStaleResources"], "releasesOnlyStaleResources"
        ),
        "currentTakeId": _token(payload["currentTakeId"], "currentTakeId"),
        "staleResourceId": _token(payload["staleResourceId"], "staleResourceId"),
    }


def _generation(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or " " in value:
        raise ValueError(f"{name} must be a non-empty token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P023-01 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
