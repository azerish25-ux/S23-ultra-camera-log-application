"""TC-P022-05 source queue exhaustion.

Delay the source consumer until its explicitly bounded queue reaches capacity.
Trigger the documented stop or failure policy with gap evidence. Never
silently overwrite source frames. An unbounded queue or hidden frame
replacement must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P022-05"
INTERVENTION = "Delay the source consumer until its explicitly bounded queue reaches capacity."
EXPECTED = "Trigger the documented stop or failure policy with gap evidence; never silently overwrite source frames."
NEGATIVE = "An unbounded queue or hidden frame replacement must fail."
POLICIES = ("stop_with_gap", "unbounded", "replace_hidden")
_PAYLOAD_KEYS = (
    "capacity",
    "occupancy",
    "policy",
    "gapEvidence",
    "incomingFrame",
    "retainedFrames",
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
    """Stop with a gap at capacity. Do not grow without bound or replace frames."""
    data = _payload(payload)
    retained = data["retainedFrames"]
    incoming = data["incomingFrame"]
    reasons = [
        f"capacity {data['capacity']}",
        f"occupancy {data['occupancy']}",
        f"policy {data['policy']}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    preserved = list(retained) + [incoming, data["cleanMasterHash"]]
    if data["policy"] == "unbounded":
        decision = "rejected"
        rejected.append("unbounded-queue")
        reasons.append("an unbounded queue must fail")
    elif data["policy"] == "replace_hidden":
        decision = "rejected"
        rejected.append("hidden-frame-replacement")
        reasons.append("hidden frame replacement must fail")
        reasons.append("retained source frames were not overwritten")
    elif data["occupancy"] < data["capacity"] - 1:
        decision = "queued"
        reasons.append("incoming frame accepted below capacity")
    elif data["occupancy"] == data["capacity"] - 1:
        decision = "at_capacity"
        reasons.append("incoming frame fills the queue to exact capacity")
    elif data["gapEvidence"]:
        decision = "stopped"
        reasons.append("first item past capacity rejected")
        reasons.append("gap evidence: " + data["gapEvidence"])
        questions.append("source gap recorded; capture did not continue silently")
    else:
        decision = "rejected"
        rejected.append("missing-gap-evidence")
        reasons.append("stop or failure at capacity requires gap evidence")
    if decision in {"queued", "at_capacity"} and incoming not in preserved:
        raise ValueError("accepted frame must remain in the inventory")
    if decision == "rejected" and data["policy"] == "replace_hidden":
        for frame in retained:
            if frame not in preserved:
                raise ValueError("hidden replacement must not drop retained frames")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capacity = payload["capacity"]
    occupancy = payload["occupancy"]
    if type(capacity) is not int or isinstance(capacity, bool) or capacity < 1:
        raise ValueError("capacity must be a positive int")
    if type(occupancy) is not int or isinstance(occupancy, bool) or occupancy < 0:
        raise ValueError("occupancy must be a non-negative int")
    if occupancy > capacity:
        raise ValueError("occupancy must not exceed capacity")
    policy = payload["policy"]
    if policy not in POLICIES:
        raise ValueError("policy must be stop_with_gap, unbounded, or replace_hidden")
    gap = payload["gapEvidence"]
    if gap is not None:
        gap = _token(gap, "gapEvidence")
    incoming = _token(payload["incomingFrame"], "incomingFrame")
    retained = _tokens(payload["retainedFrames"], "retainedFrames")
    if len(retained) != occupancy:
        raise ValueError("retainedFrames length must equal occupancy")
    if incoming in retained:
        raise ValueError("incomingFrame must not already be retained")
    if policy == "stop_with_gap" and occupancy < capacity and gap is not None:
        raise ValueError("gap evidence is only for the rejected item")
    return {
        "capacity": capacity,
        "occupancy": occupancy,
        "policy": policy,
        "gapEvidence": gap,
        "incomingFrame": incoming,
        "retainedFrames": retained,
        "cleanMasterHash": _token(payload["cleanMasterHash"], "cleanMasterHash"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    items = [_token(item, name) for item in value]
    if len(items) != len(set(items)):
        raise ValueError(f"{name} must be unique")
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P022-05 must not yield qualified or allowed")
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
