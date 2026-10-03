"""TC-P027-05 drain timeout.

One selected encoder does not complete EOS after the other track finishes.
Terminate within the declared bound and keep partial output with an incomplete
status. Waiting forever or labelling truncated audio complete must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-05"
INTERVENTION = "Prevent one selected encoder from completing EOS after the other track has finished."
EXPECTED = (
    "Terminate within the declared bound and retain inspectable partial output with the "
    "correct incomplete status."
)
NEGATIVE = "Waiting forever or silently labelling truncated audio complete must fail."
CAUSES = ("codec-failure", "stopped-microphone", "blocked-mux")
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_PAYLOAD_KEYS = {
    "cause",
    "waitedForever",
    "labelledComplete",
    "withinBound",
    "partialOutput",
    "incompleteStatus",
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
    """Bound the drain. Keep the partial output identity."""
    data = _payload(payload)
    reasons = [f"cause {data['cause']}", INTERVENTION]
    preserved = [data["partialOutput"], data["cause"]]
    rejected: list[str] = []
    if data["waitedForever"]:
        rejected.append("waited-forever")
        reasons.append("drain waited forever")
    if data["labelledComplete"]:
        rejected.append("truncated-audio-labelled-complete")
        reasons.append("truncated audio was labelled complete")
    if data["waitedForever"] or data["labelledComplete"]:
        reasons.append(NEGATIVE)
    if not data["withinBound"]:
        rejected.append("bound-missed")
        reasons.append("drain did not terminate within the declared bound")
    if not data["incompleteStatus"]:
        rejected.append("missing-incomplete-status")
        reasons.append("partial output lacked the incomplete status")
    if rejected:
        decision = "rejected"
    else:
        decision = "bounded_incomplete"
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    cause = payload["cause"]
    if cause not in CAUSES:
        raise ValueError("cause is not a declared drain failure")
    partial = payload["partialOutput"]
    if not isinstance(partial, str) or _TOKEN.fullmatch(partial) is None:
        raise ValueError("partialOutput must be a token")
    return {
        "cause": cause,
        "waitedForever": _bool(payload["waitedForever"], "waitedForever"),
        "labelledComplete": _bool(payload["labelledComplete"], "labelledComplete"),
        "withinBound": _bool(payload["withinBound"], "withinBound"),
        "partialOutput": partial,
        "incompleteStatus": _bool(payload["incompleteStatus"], "incompleteStatus"),
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-05 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
