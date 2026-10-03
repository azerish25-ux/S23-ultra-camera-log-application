"""TC-P024-08 double stop and repeated cleanup.

Redundant stop, close, cancel, and detach events are idempotent. Cleanup keeps
one terminal take identity. A double release, a duplicate publication, or a
second take created by cleanup fails.
"""

from __future__ import annotations

CASE_ID = "TC-P024-08"
INTERVENTION = "Send redundant stop, close, cancellation, and detach events in different orders."
EXPECTED = "Make cleanup idempotent and preserve a single coherent terminal take identity."
NEGATIVE = "Double release, duplicate publication, or a second take created by cleanup must fail."
CONTEXTS = (
    "empty_startup",
    "active_video",
    "active_audiovisual",
    "recovery_reopening",
)
EVENT_NAMES = ("stop", "close", "cancel", "detach")
_PAYLOAD_KEYS = (
    "context",
    "events",
    "releaseCount",
    "publicationCount",
    "takeIds",
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
    """Accept one release, one publication, and one terminal take. Reject duplicates."""
    fields = _payload(payload)
    order = ",".join(fields["events"])
    reasons = [f"context {fields['context']} order {order}", INTERVENTION]
    rejected: list[str] = []
    if fields["releaseCount"] > 1:
        rejected.append("double-release")
    if fields["publicationCount"] > 1:
        rejected.append("duplicate-publication")
    if len(fields["takeIds"]) > 1:
        rejected.append("second-take")
    if len(fields["takeIds"]) == 0:
        rejected.append("missing-terminal-identity")

    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        reasons.append("cleanup must not double-release, republish, or mint another take")
    else:
        decision = "idempotent"
        reasons.append(EXPECTED)
        reasons.append("redundant cleanup preserved one terminal take")

    preserved = list(fields["takeIds"]) if fields["takeIds"] else [fields["context"]]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    context = payload["context"]
    if context not in CONTEXTS:
        raise ValueError("context is not a TC-P024-08 repeat")
    events = payload["events"]
    if not isinstance(events, list) or len(events) < 2:
        raise ValueError("events must list at least two cleanup names")
    if any(item not in EVENT_NAMES for item in events):
        raise ValueError("events must be stop, close, cancel, or detach")
    release = _count(payload["releaseCount"], "releaseCount")
    publication = _count(payload["publicationCount"], "publicationCount")
    take_ids = _ids(payload["takeIds"])
    return {
        "context": context,
        "events": list(events),
        "releaseCount": release,
        "publicationCount": publication,
        "takeIds": take_ids,
    }


def _count(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("takeIds must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or " " in item:
            raise ValueError("takeIds must be non-empty tokens")
        if item in items:
            raise ValueError("takeIds must be unique")
        items.append(item)
    return items


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P024-08 must not yield qualified or allowed")
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
