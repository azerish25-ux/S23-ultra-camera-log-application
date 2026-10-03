#!/usr/bin/env python3
"""P034 exact image and capture-metadata pairing.

Join Images to capture metadata only by exact sensor timestamp, using bounded
pending maps. Timeout and missing-metadata policies are explicit. Duplicate
timestamps are rejected without dropping partial results. Every Image that is
copied is closed. The mutant — attaching the most recently received metadata
to each incoming Image — is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P034-01 through TC-P034-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P034"
CASE_ID = "P034"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-exact-pair-fixture"
METHOD = (
    "Join by exact sensor timestamp using bounded pending maps. Define timeout "
    "and missing-metadata policy. Detect duplicate timestamps and preserve "
    "partial results rather than nearest-neighbor guessing. Close every Image "
    "after copying or consuming its data."
)
FIXTURE = (
    "Frames arriving out of callback order with one metadata entry delayed and another absent."
)
ORACLE = (
    "Only exact matches enter qualified source records; unresolved frames receive "
    "an explicit failure or gap policy."
)
MUTANT = "Attach the most recently received metadata to each incoming Image."

HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
FRAME_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}")
NEUTRAL = re.compile(
    r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:,(?:0|[1-9][0-9]*)(?:\.[0-9]+)?){2}"
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "policy",
    "events",
}
POLICY_KEYS = {"pendingLimit", "timeoutNs", "missingMetadata", "duplicatePolicy"}
IMAGE_KEYS = {"kind", "frameId", "sensorTimestampNs", "atNs", "copied", "closed"}
METADATA_KEYS = {
    "kind",
    "frameId",
    "sensorTimestampNs",
    "atNs",
    "exposureNs",
    "blackLevel",
    "neutral",
}
STOP_KEYS = {"kind", "atNs"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
STRATEGIES = ("exact", "latest", "nearest")
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "gapped", "exact_paired", "withheld"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _frame(value: object, label: str) -> str:
    text = _text(value, label)
    require(FRAME_ID.fullmatch(text) is not None, label + " must be a frame id")
    return text


def _neutral(value: object, label: str) -> str:
    text = _text(value, label)
    require(NEUTRAL.fullmatch(text) is not None, label + " must be three neutral components")
    return text


def _positive_uint(value: object, label: str) -> str:
    text = _uint(value, label)
    require(text != "0", label + " must be positive")
    return text


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P034 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _policy(value: object) -> dict:
    item = exact_keys(value, POLICY_KEYS, "policy")
    limit = item["pendingLimit"]
    require(type(limit) is int and 1 <= limit <= 64, "pendingLimit must be an int from 1 to 64")
    _positive_uint(item["timeoutNs"], "timeoutNs")
    require(item["missingMetadata"] == "gap", "missingMetadata policy must be gap")
    require(item["duplicatePolicy"] == "reject_and_preserve",
            "duplicatePolicy must reject and preserve")
    return item


def _event(value: object, index: int) -> dict:
    require(isinstance(value, dict), f"event {index} must be an object")
    kind = value.get("kind")
    require(kind in {"image", "metadata", "stop"}, f"event {index} kind is unknown")
    if kind == "image":
        item = exact_keys(value, IMAGE_KEYS, f"event {index}")
        _frame(item["frameId"], f"event {index} frameId")
        _uint(item["sensorTimestampNs"], f"event {index} sensorTimestampNs")
        _uint(item["atNs"], f"event {index} atNs")
        require(type(item["copied"]) is bool, f"event {index} copied must be a bool")
        require(type(item["closed"]) is bool, f"event {index} closed must be a bool")
        return item
    if kind == "metadata":
        item = exact_keys(value, METADATA_KEYS, f"event {index}")
        _frame(item["frameId"], f"event {index} frameId")
        _uint(item["sensorTimestampNs"], f"event {index} sensorTimestampNs")
        _uint(item["atNs"], f"event {index} atNs")
        _positive_uint(item["exposureNs"], f"event {index} exposureNs")
        _uint(item["blackLevel"], f"event {index} blackLevel")
        _neutral(item["neutral"], f"event {index} neutral")
        return item
    item = exact_keys(value, STOP_KEYS, f"event {index}")
    _uint(item["atNs"], f"event {index} atNs")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P034 pairing fixture schema."""
    exact_keys(document, DOCUMENT_KEYS, "pairing document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P034")
    require(document["mapId"] == MAP_ID, "mapId must be s23-exact-pair-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "pairing document needs the P034 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _policy(document["policy"])
    events = document["events"]
    require(isinstance(events, list) and events, "events must be a non-empty list")
    parsed = [_event(item, index) for index, item in enumerate(events)]
    stops = [item for item in parsed if item["kind"] == "stop"]
    require(len(stops) == 1, "events must contain exactly one stop")
    previous = -1
    for index, item in enumerate(parsed):
        at_ns = int(item["atNs"])
        require(at_ns > previous, f"event {index} atNs must increase")
        previous = at_ns


def _image_token(event: dict) -> str:
    return f"image:{event['frameId']}@{event['sensorTimestampNs']}"


def _meta_token(event: dict) -> str:
    return (
        f"metadata:{event['frameId']}@{event['sensorTimestampNs']}"
        f":exposure:{event['exposureNs']}:black:{event['blackLevel']}:neutral:{event['neutral']}"
    )


def _exact_token(event: dict, meta: dict) -> str:
    return (
        f"exact:{event['frameId']}@{event['sensorTimestampNs']}"
        f":exposure:{meta['exposureNs']}:black:{meta['blackLevel']}:neutral:{meta['neutral']}"
    )


def refused_latest_attachments(events: list[dict]) -> list[str]:
    """Attachments the latest-metadata mutant would make across unequal timestamps.

    ``assess`` must not accept these. The list is a detector, not a pairing result.
    """
    latest: dict | None = None
    refused: list[str] = []
    for event in events:
        if event["kind"] == "metadata":
            latest = event
        elif event["kind"] == "image" and latest is not None:
            if latest["sensorTimestampNs"] != event["sensorTimestampNs"]:
                refused.append(
                    f"{event['frameId']}@{event['sensorTimestampNs']}"
                    f"<-{latest['frameId']}@{latest['sensorTimestampNs']}"
                )
    return refused


def _inventory(events: list[dict]) -> list[str]:
    rows: list[str] = []
    for event in events:
        if event["kind"] == "image":
            rows.append(_image_token(event))
        elif event["kind"] == "metadata":
            rows.append(_meta_token(event))
        else:
            rows.append(f"stop@{event['atNs']}")
    return rows


def _reject_strategy(document: dict, strategy: str) -> dict[str, Any]:
    events = document["events"]
    preserved = _inventory(events)
    if strategy == "latest":
        refused = refused_latest_attachments(events)
        reasons = [
            MUTANT,
            "latest-metadata association is not an exact sensor-timestamp join",
            ORACLE,
        ]
        reasons.extend(f"refused latest attachment {item}" for item in refused)
        return _result(
            "rejected",
            reasons,
            ["latest-metadata"],
            preserved,
            ["exact timestamp join not used"],
        )
    reasons = [
        "nearest-timestamp association is not an exact sensor-timestamp join",
        "nearest-neighbor guessing is rejected",
        ORACLE,
    ]
    return _result(
        "rejected",
        reasons,
        ["nearest-timestamp"],
        preserved,
        ["exact timestamp join not used"],
    )


def _assess_exact(document: dict) -> dict[str, Any]:
    policy = document["policy"]
    limit = policy["pendingLimit"]
    timeout = int(policy["timeoutNs"])
    pending_images: dict[str, dict] = {}
    pending_meta: dict[str, dict] = {}
    seen_images: set[str] = set()
    seen_meta: set[str] = set()
    preserved = _inventory(document["events"])
    closed: list[str] = []
    outcomes: list[str] = []
    rejected: list[str] = []
    questions: list[str] = []
    stopped = False
    saw_image = False

    def gap_pending(stop_at: int) -> None:
        for image in pending_images.values():
            age = stop_at - int(image["atNs"])
            reason = "timeout" if age >= timeout else "missing-metadata"
            token = f"gap:{image['frameId']}@{image['sensorTimestampNs']}:{reason}"
            outcomes.append(token)
            questions.append(token)
        for meta in pending_meta.values():
            token = f"unused-metadata:{meta['frameId']}@{meta['sensorTimestampNs']}"
            outcomes.append(token)
            questions.append(token)
        pending_images.clear()
        pending_meta.clear()

    for event in document["events"]:
        if stopped:
            if event["kind"] == "image":
                token = f"after-stop:image:{event['frameId']}@{event['sensorTimestampNs']}"
            elif event["kind"] == "metadata":
                token = f"after-stop:metadata:{event['frameId']}@{event['sensorTimestampNs']}"
            else:
                token = f"after-stop:stop@{event['atNs']}"
            outcomes.append(token)
            questions.append(token)
            continue
        if event["kind"] == "stop":
            gap_pending(int(event["atNs"]))
            stopped = True
            continue
        if event["kind"] == "image":
            saw_image = True
            frame_id = event["frameId"]
            stamp = event["sensorTimestampNs"]
            if event["copied"] and event["closed"]:
                closed.append(f"closed:{frame_id}")
            else:
                if not event["copied"]:
                    rejected.append(f"image-not-copied:{frame_id}")
                if not event["closed"]:
                    rejected.append(f"image-not-closed:{frame_id}")
                outcomes.append(f"unready:{frame_id}@{stamp}")
                continue
            if stamp in seen_images:
                rejected.append(f"duplicate-timestamp:{stamp}")
                outcomes.append(f"duplicate:image:{frame_id}@{stamp}")
                continue
            if stamp in pending_meta:
                meta = pending_meta[stamp]
                if meta["frameId"] != frame_id:
                    rejected.append(f"frame-id-mismatch:{stamp}")
                    outcomes.append(f"mismatch:{frame_id}/{meta['frameId']}@{stamp}")
                    continue
                pending_meta.pop(stamp)
                seen_images.add(stamp)
                outcomes.append(_exact_token(event, meta))
                continue
            if len(pending_images) >= limit:
                rejected.append(f"pending-overflow:{frame_id}")
                outcomes.append(f"overflow:{frame_id}@{stamp}")
                continue
            pending_images[stamp] = event
            seen_images.add(stamp)
            continue
        frame_id = event["frameId"]
        stamp = event["sensorTimestampNs"]
        if stamp in seen_meta:
            rejected.append(f"duplicate-timestamp:{stamp}")
            outcomes.append(f"duplicate:metadata:{frame_id}@{stamp}")
            continue
        if stamp in pending_images:
            image = pending_images[stamp]
            if image["frameId"] != frame_id:
                rejected.append(f"frame-id-mismatch:{stamp}")
                outcomes.append(f"mismatch:{image['frameId']}/{frame_id}@{stamp}")
                continue
            pending_images.pop(stamp)
            seen_meta.add(stamp)
            outcomes.append(_exact_token(image, event))
            continue
        if len(pending_meta) >= limit:
            rejected.append(f"pending-overflow:{frame_id}")
            outcomes.append(f"overflow-metadata:{frame_id}@{stamp}")
            continue
        pending_meta[stamp] = event
        seen_meta.add(stamp)

    preserved.extend(closed)
    preserved.extend(outcomes)
    exact = [item for item in outcomes if item.startswith("exact:")]
    gaps = [item for item in outcomes if item.startswith("gap:") or item.startswith("unused-")]
    structural = bool(rejected)
    if structural:
        decision = "rejected"
    elif gaps or any(item.startswith("after-stop:") for item in outcomes):
        decision = "gapped"
    elif exact and saw_image:
        decision = "exact_paired"
    else:
        decision = "withheld"

    reasons = [ORACLE]
    for item in exact:
        ident = item.split(":", 2)[1]
        reasons.append(f"exact match {ident}")
    for item in outcomes:
        if item.startswith("gap:"):
            reasons.append(f"unresolved frame received {item}")
    if structural:
        reasons.append("partial results are preserved; timestamps were not guessed")
    if decision == "gapped":
        reasons.append("latest metadata was not attached to a different sensor timestamp")
        reasons.append("a gapped host result is not physical S23 qualification")
    elif decision == "exact_paired":
        reasons.append("every resolved frame used an equal sensor timestamp")
        reasons.append("an exact host pair is not physical S23 qualification")
    elif decision == "withheld":
        reasons.append("no exact sensor-timestamp pair was formed")
    if closed and not any(item.startswith("image-not-closed:") or item.startswith("image-not-copied:")
                         for item in rejected):
        reasons.append("every copied image was closed")
    elif any(item.startswith("image-not-closed:") for item in rejected):
        reasons.append("an image that was not closed after copy is not a source record")
    questions.append("physical pairing unverified")
    return _result(decision, reasons, rejected, preserved, questions)


def assess(document: dict, strategy: str = "exact") -> dict[str, Any]:
    """Pair the document, or reject a latest/nearest mutant strategy.

    Exact matches keep the metadata that shares the sensor timestamp. Unresolved
    images become timeout or missing-metadata gaps. Decision is never
    ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(strategy in STRATEGIES, "strategy must be exact, latest, or nearest")
    if strategy != "exact":
        return _reject_strategy(document, strategy)
    return _assess_exact(document)
