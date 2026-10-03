"""TC-P021-01 late callback generation.

A successful callback from a previous camera or recording generation is stale
once the owner has changed. Stale state is ignored. Only resources owned by
the stale operation are released. A delayed callback that resurrects recording
or attaches an obsolete surface is rejected.

Baseline focus inventory stays in preservedResults. This host module does not
touch a device.
"""

from __future__ import annotations

CASE_ID = "TC-P021-01"
INTERVENTION = (
    "Deliver a successful callback from a previous camera or recording "
    "generation after the current owner has changed."
)
EXPECTED = (
    "Ignore stale state mutation and release only resources owned by the stale operation."
)
NEGATIVE = (
    "A delayed callback that resurrects recording or attaches an obsolete surface must fail."
)
REPEATS = (
    "before_first_sample",
    "during_stopping",
    "after_activity_recreation",
    "after_camera_reopen",
)
FOCUS_INVENTORY = (
    "physical.namespace:physical.lens",
    "physical.unit:metres",
    "physical.subject:nearby_foreground",
    "physical.distance:unknown",
    "virtual.namespace:virtual.development",
    "virtual.unit:relative_depth",
    "virtual.subject:face",
    "virtual.relativeDepth:0.62",
)
_PAYLOAD_KEYS = {
    "callbackGeneration",
    "currentOwner",
    "phase",
    "resurrectsRecording",
    "attachesObsoleteSurface",
    "staleResources",
    "currentResources",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Ignore a stale callback. Reject resurrection and obsolete surfaces."""
    (
        callback_generation,
        current_owner,
        phase,
        resurrects,
        obsolete,
        stale_resources,
        current_resources,
    ) = _payload(payload)
    stale = callback_generation != current_owner
    preserved = list(FOCUS_INVENTORY)
    preserved.extend("resource:" + item for item in current_resources)
    rejected: list[str] = []
    reasons = [EXPECTED, "repeat phase " + phase]

    if resurrects or obsolete:
        decision = "rejected"
        reasons.append(NEGATIVE)
        if resurrects:
            rejected.append("resurrect-recording")
            reasons.append("delayed callback does not resurrect recording")
        if obsolete:
            rejected.append("obsolete-surface")
            reasons.append("delayed callback does not attach an obsolete surface")
        if stale:
            reasons.append(
                "released only resources owned by the stale operation: "
                + (", ".join(stale_resources) if stale_resources else "none")
            )
    elif stale:
        decision = "ignored_stale"
        rejected.append("stale-generation:" + str(callback_generation))
        reasons.append("stale state mutation ignored")
        reasons.append(
            "released only resources owned by the stale operation: "
            + (", ".join(stale_resources) if stale_resources else "none")
        )
    else:
        decision = "current_owner"
        reasons.append("callback generation matches the current owner")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P021-01 must not decide qualified or allowed")
    for resource in stale_resources:
        if "resource:" + resource in preserved:
            raise ValueError("stale resource must not stay in the live inventory")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    callback_generation = _count(payload["callbackGeneration"], "callbackGeneration")
    current_owner = _count(payload["currentOwner"], "currentOwner")
    if callback_generation > current_owner:
        raise ValueError("callbackGeneration must not be ahead of the current owner")
    phase = payload["phase"]
    if phase not in REPEATS:
        raise ValueError("phase is not a TC-P021-01 repeat")
    stale_resources = _tokens(payload["staleResources"], "staleResources")
    current_resources = _tokens(payload["currentResources"], "currentResources")
    if set(stale_resources) & set(current_resources):
        raise ValueError("stale and current resources must be disjoint")
    return (
        callback_generation,
        current_owner,
        phase,
        _bool(payload["resurrectsRecording"], "resurrectsRecording"),
        _bool(payload["attachesObsoleteSurface"], "attachesObsoleteSurface"),
        _tokens(payload["staleResources"], "staleResources"),
        _tokens(payload["currentResources"], "currentResources"),
    )


def _count(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(name + " must be a non-negative int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(name + " must be a bool")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(name + " must be a list")
    seen: set[str] = set()
    tokens: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(name + " entries must be non-empty strings")
        if item in seen:
            raise ValueError(name + " entries must be unique")
        seen.add(item)
        tokens.append(item)
    return tokens


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("decision must not be qualified or allowed")
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
