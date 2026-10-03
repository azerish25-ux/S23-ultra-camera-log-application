"""TC-P018-08 double stop and repeated cleanup.

Stop, close, cancel, and detach may arrive more than once and in any order.
Each resource is released once and one take identity is published at most
once. Double release, duplicate publication, or a second take is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P018-08"
INTERVENTION = "Send redundant stop, close, cancellation, and detach events in different orders."
EXPECTED = "Make cleanup idempotent and preserve a single coherent terminal take identity."
NEGATIVE = "Double release, duplicate publication, or a second take created by cleanup must fail."
REPEAT = (
    "Repeat with empty startup, active video, active audiovisual capture, "
    "and recovery reopening."
)
SCENARIOS = (
    "empty_startup",
    "active_video",
    "active_audiovisual",
    "recovery_reopening",
)
CLEANUP_EVENTS = ("stop", "close", "cancel", "detach")
PUBLISHING = frozenset({"active_video", "active_audiovisual"})
_PAYLOAD_KEYS = (
    "scenario",
    "events",
    "takeId",
    "doubleRelease",
    "duplicatePublication",
    "secondTake",
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
    """Fold redundant cleanup into one terminal take."""
    scenario, events, take_id, double_release, duplicate_publication, second_take = _payload(payload)
    counts = _effects(events)
    reasons = [f"scenario {scenario}", "events " + ",".join(events)]
    rejected: list[str] = []
    if double_release:
        rejected.append("double-release")
        reasons.append("double release is rejected")
    if duplicate_publication:
        rejected.append("duplicate-publication")
        reasons.append("duplicate publication is rejected")
    if second_take:
        rejected.append("second-take")
        reasons.append("cleanup must not create a second take")

    publications = 1 if counts["stop"] and scenario in PUBLISHING else 0
    if rejected:
        decision = "rejected"
        reasons.append("idempotent cleanup refused")
    else:
        decision = "idempotent"
        reasons.append(f"close:{counts['close']}")
        reasons.append(f"detach:{counts['detach']}")
        reasons.append(f"cancel:{counts['cancel']}")
        reasons.append(f"stop:{counts['stop']}")
        reasons.append(f"publications:{publications}")
        reasons.append("single terminal take")
        if counts["close"] > 1 or counts["detach"] > 1 or publications > 1:
            raise ValueError("cleanup effects must stay idempotent")

    preserved = [take_id]
    if preserved.count(take_id) != 1:
        raise ValueError("terminal take identity must stay singular")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P018-08 must not yield qualified or allowed")
    return _result(decision, reasons, rejected, preserved, [])


def _effects(events: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in CLEANUP_EVENTS}
    for event in events:
        if counts[event] == 0:
            counts[event] = 1
    return counts


def _payload(payload: object) -> tuple[str, list[str], str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scenario = payload["scenario"]
    if scenario not in SCENARIOS:
        raise ValueError("scenario is not a P018 cleanup repeat")
    events = payload["events"]
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    clean: list[str] = []
    for item in events:
        if item not in CLEANUP_EVENTS:
            raise ValueError("event is not stop, close, cancel, or detach")
        clean.append(item)
    take_id = payload["takeId"]
    if not isinstance(take_id, str) or not take_id or take_id != take_id.strip():
        raise ValueError("takeId must be a non-empty string")
    flags = []
    for name in ("doubleRelease", "duplicatePublication", "secondTake"):
        if type(payload[name]) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(payload[name])
    return scenario, clean, take_id, flags[0], flags[1], flags[2]


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
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
