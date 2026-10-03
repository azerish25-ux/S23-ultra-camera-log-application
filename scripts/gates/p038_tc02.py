"""TC-P038-02 metadata callback reordering.

Intervention: Deliver metadata in a different callback order from Images with
one exact match delayed.
Expected: Pair only matching sensor timestamps within the bounded policy and
retain unresolved status otherwise.
Negative: Nearest-time or latest-metadata association must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain "
    "unresolved status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."

_ASSOCIATION = ("exact", "nearest", "latest")
_FRAME_KEYS = {"id", "sensorTimestamp", "order"}
_META_KEYS = {"id", "sensorTimestamp", "order", "afterStop"}
_PAYLOAD_KEYS = ("frames", "metadata", "bound", "association")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "unresolved", "paired")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Pair exact sensor timestamps inside the bound. Do not guess nearest or latest."""
    frames, metadata, bound, association = _payload(payload)
    preserved = [f"frame:{item['id']}@{item['sensorTimestamp']}" for item in frames]
    preserved.extend(f"metadata:{item['id']}@{item['sensorTimestamp']}" for item in metadata)
    if association == "nearest":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "nearest-time association was not applied"],
            ["nearest-time"],
            preserved,
            ["unresolved association"],
        )
    if association == "latest":
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "latest-metadata association was not applied"],
            ["latest-metadata"],
            preserved,
            ["unresolved association"],
        )
    used: set[int] = set()
    pairs: list[str] = []
    unresolved: list[str] = []
    for frame in frames:
        candidates = []
        for index, item in enumerate(metadata):
            if index in used:
                continue
            if item["sensorTimestamp"] != frame["sensorTimestamp"]:
                continue
            if item["afterStop"]:
                continue
            if abs(item["order"] - frame["order"]) > bound:
                continue
            candidates.append(index)
        if len(candidates) == 1:
            used.add(candidates[0])
            pairs.append(f"pair:{frame['id']}>{metadata[candidates[0]]['id']}")
        else:
            unresolved.append(frame["id"])
    preserved.extend(pairs)
    if unresolved:
        return _result(
            "unresolved",
            [EXPECTED, "exact timestamp matches only; unresolved frames stay unresolved"],
            [],
            preserved,
            [f"unresolved:{item}" for item in unresolved],
        )
    return _result(
        "paired",
        [EXPECTED, "paired only exact sensor timestamps inside the bound"],
        [],
        preserved,
        ["pairing is not physical synchronization"],
    )


def _payload(payload: object) -> tuple[list[dict], list[dict], int, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    frames = _records(payload["frames"], _FRAME_KEYS, "frame", False)
    metadata = _records(payload["metadata"], _META_KEYS, "metadata", True)
    if not frames:
        raise ValueError("frames must be a non-empty list")
    bound = payload["bound"]
    if type(bound) is not int or bound < 0:
        raise ValueError("bound must be a non-negative int")
    association = payload["association"]
    if association not in _ASSOCIATION:
        raise ValueError("association must be exact, nearest, or latest")
    frame_ids = [item["id"] for item in frames]
    meta_ids = [item["id"] for item in metadata]
    if len(frame_ids) != len(set(frame_ids)) or len(meta_ids) != len(set(meta_ids)):
        raise ValueError("record ids must be unique")
    return frames, metadata, bound, association


def _records(value: object, keys: set[str], label: str, after_stop: bool) -> list[dict]:
    if type(value) is not list:
        raise ValueError(label + " must be a list")
    records = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != keys:
            raise ValueError(label + f" {index} keys are invalid")
        ident = item["id"]
        stamp = item["sensorTimestamp"]
        order = item["order"]
        if not isinstance(ident, str) or not ident or ident != ident.strip():
            raise ValueError(label + " id must be a non-empty string")
        if not isinstance(stamp, str) or not stamp or stamp[0] == "-" or not stamp.isdigit():
            raise ValueError(label + " sensorTimestamp must be a canonical integer string")
        if stamp != "0" and stamp[0] == "0":
            raise ValueError(label + " sensorTimestamp must be canonical")
        if type(order) is not int or order < 0:
            raise ValueError(label + " order must be a non-negative int")
        if after_stop and type(item["afterStop"]) is not bool:
            raise ValueError("afterStop must be a bool")
        records.append(item)
    return records


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("pairing decision cannot be qualified or allowed")
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
