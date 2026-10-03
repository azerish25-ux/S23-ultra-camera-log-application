"""TC-P026-08 physical sync disagreement.

Packet starts can line up while a measured visible-audible event is offset
or drifting. Container timing and physical synchronization stay distinct,
and the sync gate fails. A packet-only lip-sync certificate must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-08"
INTERVENTION = (
    "Provide aligned packet starts but a measured visible-audible event offset or drift in the actual recording."
)
EXPECTED = (
    "Keep container timing and physical synchronization as distinct results and fail the relevant sync gate."
)
NEGATIVE = "A packet-only lip-sync certificate must fail."
POSITIONS = ("beginning", "middle", "end")
_PAYLOAD_KEYS = (
    "position",
    "fixtureDistance",
    "packetStartAligned",
    "containerOffsetMs",
    "measuredOffsetMs",
    "drift",
    "packetOnlyCertificate",
    "takeId",
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
    """Fail physical sync without collapsing it into container timing."""
    fields = _payload(payload)
    reasons = [
        INTERVENTION,
        f"position {fields['position']}",
        f"fixture distance {fields['fixtureDistance']}",
    ]
    preserved = [
        f"container:{fields['takeId']}:{fields['containerOffsetMs']}",
        (
            f"physical:{fields['position']}:{fields['fixtureDistance']}:"
            f"{fields['measuredOffsetMs']}"
        ),
    ]
    rejected: list[str] = []
    disagreed = fields["measuredOffsetMs"] != 0 or fields["drift"]
    if fields["packetOnlyCertificate"]:
        rejected.append("packet-only-lipsync")
        reasons.append(NEGATIVE)
    if not fields["packetStartAligned"]:
        rejected.append("packet-starts-unaligned")
        reasons.append("packet starts were not aligned")
    if disagreed:
        rejected.append("physical-sync")
        reasons.append(EXPECTED)
    if rejected:
        decision = "rejected" if "packet-only-lipsync" in rejected or "packet-starts-unaligned" in rejected else "sync_failed"
    else:
        decision = "sync_unverified"
        reasons.append("container timing and physical synchronization remain distinct")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    position = payload["position"]
    if position not in POSITIONS:
        raise ValueError("position is not a declared repeat")
    distance = payload["fixtureDistance"]
    if not isinstance(distance, str) or not _distance(distance):
        raise ValueError("fixtureDistance must look like 2m or 1.5m")
    return {
        "position": position,
        "fixtureDistance": distance,
        "packetStartAligned": _bool(payload["packetStartAligned"], "packetStartAligned"),
        "containerOffsetMs": _int(payload["containerOffsetMs"], "containerOffsetMs"),
        "measuredOffsetMs": _int(payload["measuredOffsetMs"], "measuredOffsetMs"),
        "drift": _bool(payload["drift"], "drift"),
        "packetOnlyCertificate": _bool(payload["packetOnlyCertificate"], "packetOnlyCertificate"),
        "takeId": _token(payload["takeId"], "takeId"),
    }


def _distance(value: str) -> bool:
    if len(value) < 2 or not value.endswith("m"):
        return False
    number = value[:-1]
    whole, dot, frac = number.partition(".")
    if not whole.isdigit() or whole[0] == "0":
        return False
    if dot == "":
        return True
    return bool(frac) and frac.isdigit() and frac[-1] != "0"


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _int(value: object, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-08 must not yield qualified or allowed")
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
