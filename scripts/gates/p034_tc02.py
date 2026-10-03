"""TC-P034-02 metadata callback reordering.

Pair only equal sensor timestamps inside a bounded pending map. Delayed
metadata may still match. Missing metadata, duplicates, and metadata after
stop stay unresolved. Nearest-time and latest-metadata association fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P034-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain "
    "unresolved status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."

_CANONICAL = re.compile(r"0|[1-9][0-9]*")
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}")
_KINDS = ("image", "metadata", "stop")
_ASSOCIATIONS = ("exact", "nearest", "latest")
_EVENT_KEYS = ("kind", "id", "ts")
_PAYLOAD_KEYS = ("association", "pendingLimit", "events")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "gapped", "exact_paired"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Pair callback-ordered events by exact sensor timestamp only."""
    association, limit, events = _payload(payload)
    preserved = [f"{event['kind']}:{event['id']}@{event['ts']}" for event in events]
    if association == "latest":
        return _result(
            "rejected",
            [INTERVENTION, EXPECTED, NEGATIVE, "latest metadata was not attached"],
            ["latest-metadata"],
            preserved,
            ["unresolved association"],
        )
    if association == "nearest":
        return _result(
            "rejected",
            [INTERVENTION, EXPECTED, NEGATIVE, "nearest timestamp was not used"],
            ["nearest-time"],
            preserved,
            ["unresolved association"],
        )
    return _exact(events, limit, preserved)


def _exact(events: list[dict], limit: int, preserved: list[str]) -> dict:
    pending_images: dict[str, dict] = {}
    pending_meta: dict[str, dict] = {}
    seen_images: set[str] = set()
    seen_meta: set[str] = set()
    outcomes: list[str] = []
    rejected: list[str] = []
    questions: list[str] = []
    stopped = False

    for event in events:
        kind = event["kind"]
        ident = event["id"]
        stamp = event["ts"]
        if stopped:
            outcomes.append(f"after-stop:{kind}:{ident}@{stamp}")
            questions.append(f"metadata-after-stop:{ident}" if kind == "metadata"
                             else f"after-stop:{ident}")
            continue
        if kind == "stop":
            for image in pending_images.values():
                token = f"gap:{image['id']}@{image['ts']}"
                outcomes.append(token)
                questions.append(f"missing-metadata:{image['id']}")
            for meta in pending_meta.values():
                outcomes.append(f"unused-metadata:{meta['id']}@{meta['ts']}")
            pending_images.clear()
            pending_meta.clear()
            stopped = True
            continue
        if kind == "image":
            if stamp in seen_images:
                rejected.append(f"duplicate-timestamp:{stamp}")
                outcomes.append(f"duplicate:image:{ident}@{stamp}")
                continue
            if stamp in pending_meta:
                pending_meta.pop(stamp)
                seen_images.add(stamp)
                outcomes.append(f"exact:{ident}@{stamp}")
                continue
            if len(pending_images) >= limit:
                rejected.append(f"pending-overflow:{ident}")
                outcomes.append(f"overflow:{ident}@{stamp}")
                continue
            pending_images[stamp] = event
            seen_images.add(stamp)
            continue
        if stamp in seen_meta:
            rejected.append(f"duplicate-timestamp:{stamp}")
            outcomes.append(f"duplicate:metadata:{ident}@{stamp}")
            continue
        if stamp in pending_images:
            pending_images.pop(stamp)
            seen_meta.add(stamp)
            outcomes.append(f"exact:{ident}@{stamp}")
            continue
        if len(pending_meta) >= limit:
            rejected.append(f"pending-overflow:{ident}")
            outcomes.append(f"overflow-metadata:{ident}@{stamp}")
            continue
        pending_meta[stamp] = event
        seen_meta.add(stamp)

    preserved = list(preserved) + outcomes
    exact = [item for item in outcomes if item.startswith("exact:")]
    unresolved = [
        item for item in outcomes
        if item.startswith("gap:") or item.startswith("after-stop:") or item.startswith("unused-")
    ]
    if rejected:
        decision = "rejected"
        reasons = [
            INTERVENTION,
            EXPECTED,
            "duplicate or overflow kept the earlier partial results",
        ]
    elif unresolved or not exact:
        decision = "gapped"
        reasons = [INTERVENTION, EXPECTED, "unresolved frames stayed unresolved"]
    else:
        decision = "exact_paired"
        reasons = [INTERVENTION, EXPECTED, "only equal sensor timestamps were paired"]
    reasons.append("nearest-time and latest-metadata association were not used")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, list[dict]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    association = payload["association"]
    if association not in _ASSOCIATIONS:
        raise ValueError("association is not exact, nearest, or latest")
    limit = payload["pendingLimit"]
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("pendingLimit must be an int from 1 to 64")
    events = payload["events"]
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    seen: set[tuple[str, str]] = set()
    parsed: list[dict] = []
    stops = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != set(_EVENT_KEYS):
            raise ValueError(f"event {index} keys are invalid")
        if event["kind"] not in _KINDS:
            raise ValueError(f"event {index} kind is unknown")
        ident = event["id"]
        stamp = event["ts"]
        if not isinstance(ident, str) or _ID.fullmatch(ident) is None:
            raise ValueError(f"event {index} id is invalid")
        key = (event["kind"], ident)
        if key in seen:
            raise ValueError("event ids must be unique within a kind")
        seen.add(key)
        if not isinstance(stamp, str) or _CANONICAL.fullmatch(stamp) is None:
            raise ValueError(f"event {index} ts is invalid")
        if event["kind"] == "stop":
            stops += 1
        parsed.append({"kind": event["kind"], "id": ident, "ts": stamp})
    if stops != 1:
        raise ValueError("events must contain exactly one stop")
    return association, limit, parsed


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("reorder decision cannot be qualified or allowed")
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
