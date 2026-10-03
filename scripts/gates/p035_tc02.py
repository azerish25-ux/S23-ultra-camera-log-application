"""TC-P035-02 metadata callback reordering.

Intervention: Deliver metadata in a different callback order from Images with
one exact match delayed.
Expected: Pair only matching sensor timestamps within the bounded policy and
retain unresolved status otherwise.
Negative: Nearest-time or latest-metadata association must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P035-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain unresolved "
    "status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."

ASSOCIATIONS = ("exact", "nearest", "latest")
CANONICAL = re.compile(r"0|[1-9][0-9]*")
_ITEM_KEYS = ("id", "sensorTimestamp")
_PAYLOAD_KEYS = ("images", "metadata", "order", "association")
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
    """Pair Images to metadata only by exact sensor timestamp."""
    images, metadata, order, association = _payload(payload)
    preserved = [f"image:{item['id']}@{item['sensorTimestamp']}" for item in images]
    preserved.extend(f"metadata:{item['id']}@{item['sensorTimestamp']}" for item in metadata)
    if association == "nearest":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "nearest-time association is rejected"],
            ["nearest-time"],
            preserved,
            ["unresolved metadata"],
        )
    if association == "latest":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "latest-metadata association is rejected"],
            ["latest-metadata"],
            preserved,
            ["unresolved metadata"],
        )
    if _duplicate_times(images) or _duplicate_times(metadata):
        return _result(
            "rejected",
            [EXPECTED, "duplicate sensor timestamps are not paired"],
            ["duplicate-timestamp"],
            preserved,
            ["duplicate timestamps"],
        )
    seen_images: set[str] = set()
    seen_meta: set[str] = set()
    used_images: set[str] = set()
    used_meta: set[str] = set()
    pairs: list[tuple[str, str]] = []
    closed = False
    delayed = False

    def try_pair() -> None:
        for image in images:
            if image["id"] in used_images or image["id"] not in seen_images:
                continue
            for meta in metadata:
                if meta["id"] in used_meta or meta["id"] not in seen_meta:
                    continue
                if image["sensorTimestamp"] == meta["sensorTimestamp"]:
                    used_images.add(image["id"])
                    used_meta.add(meta["id"])
                    pairs.append((image["id"], meta["id"]))
                    break

    for event in order:
        if event == "stop":
            closed = True
            continue
        kind, ident = event.split(":", 1)
        if closed:
            delayed = True
            continue
        if kind == "image":
            seen_images.add(ident)
        else:
            seen_meta.add(ident)
        try_pair()

    for image_id, meta_id in pairs:
        preserved.append(f"pair:{image_id}={meta_id}")
    unresolved = [item["id"] for item in images if item["id"] not in used_images]
    for ident in unresolved:
        preserved.append(f"unresolved:{ident}")
    if unresolved or delayed:
        questions = [f"unresolved {ident}" for ident in unresolved]
        if delayed:
            questions.append("delayed metadata after stop")
        return _result(
            "unresolved",
            [EXPECTED, "only exact sensor timestamps pair within the bound"],
            [],
            preserved,
            questions,
        )
    return _result(
        "paired",
        [EXPECTED, "exact sensor timestamps paired within the bound"],
        [],
        preserved,
        [],
    )


def _duplicate_times(items: list[dict]) -> bool:
    stamps = [item["sensorTimestamp"] for item in items]
    return len(stamps) != len(set(stamps))


def _item(value: object, label: str, seen: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != set(_ITEM_KEYS):
        raise ValueError(label + " item keys")
    ident = value["id"]
    stamp = value["sensorTimestamp"]
    if not isinstance(ident, str) or not ident or ident != ident.strip() or ident in seen:
        raise ValueError(label + " id")
    if not isinstance(stamp, str) or CANONICAL.fullmatch(stamp) is None:
        raise ValueError(label + " sensorTimestamp")
    seen.add(ident)
    return {"id": ident, "sensorTimestamp": stamp}


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    images_raw = payload["images"]
    meta_raw = payload["metadata"]
    order = payload["order"]
    association = payload["association"]
    if not isinstance(images_raw, list) or not images_raw:
        raise ValueError("images must be a non-empty list")
    if not isinstance(meta_raw, list):
        raise ValueError("metadata must be a list")
    if association not in ASSOCIATIONS:
        raise ValueError("association")
    seen: set[str] = set()
    images = [_item(item, "image", seen) for item in images_raw]
    seen_meta: set[str] = set()
    metadata = [_item(item, "metadata", seen_meta) for item in meta_raw]
    if not isinstance(order, list) or not order:
        raise ValueError("order")
    if order.count("stop") > 1:
        raise ValueError("stop may occur at most once")
    image_ids = {item["id"] for item in images}
    meta_ids = {item["id"] for item in metadata}
    for event in order:
        if event == "stop":
            continue
        if not isinstance(event, str) or ":" not in event:
            raise ValueError("order event")
        kind, ident = event.split(":", 1)
        if kind == "image" and ident in image_ids:
            continue
        if kind == "metadata" and ident in meta_ids:
            continue
        raise ValueError("order references an unknown callback")
    return images, metadata, list(order), association


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
