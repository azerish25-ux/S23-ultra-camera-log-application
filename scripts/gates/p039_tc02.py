"""TC-P039-02 metadata callback reordering.

Pair an image only with metadata that shares its sensor timestamp. A different
callback order is not a pairing key. Nearest-time and latest-metadata
association are rejected. Duplicates, missing metadata, and metadata delayed
past stop stay unresolved.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P039-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain unresolved status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."

_ASSOCIATIONS = ("exact", "nearest", "latest")
_REPEATS = ("reordered", "duplicate_timestamps", "missing_metadata", "delayed_after_stop")
_TS = re.compile(r"^(0|[1-9][0-9]*)$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_ITEM_KEYS = {"id", "timestampNs"}
_PAYLOAD_KEYS = (
    "images",
    "metadata",
    "boundNs",
    "association",
    "repeat",
    "delayedMetadataId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Pair exact sensor timestamps or keep the image unresolved."""
    images, metadata, bound_ns, association, repeat, delayed = _payload(payload)
    reasons = [EXPECTED, INTERVENTION, f"boundNs {bound_ns}", f"repeat {repeat}"]
    preserved = [f"image:{item['id']}@{item['timestampNs']}" for item in images]
    preserved.extend(f"metadata:{item['id']}@{item['timestampNs']}" for item in metadata)
    if association == "nearest":
        reasons.append(NEGATIVE)
        return _result("rejected", reasons, ["nearest-time-association"], preserved, ["nearest-time was not used"])
    if association == "latest":
        reasons.append(NEGATIVE)
        return _result(
            "rejected", reasons, ["latest-metadata-association"], preserved, ["latest-metadata was not used"]
        )

    buckets: dict[str, list[dict]] = {}
    for item in metadata:
        if item["id"] == delayed:
            continue
        buckets.setdefault(item["timestampNs"], []).append(item)
    paired: list[str] = []
    unresolved: list[str] = []
    used: set[str] = set()
    for image in images:
        matches = buckets.get(image["timestampNs"], [])
        if len(matches) == 1 and matches[0]["id"] not in used:
            used.add(matches[0]["id"])
            paired.append(f"{image['id']}={matches[0]['id']}")
        else:
            unresolved.append(image["id"])
    questions: list[str] = []
    if repeat == "duplicate_timestamps":
        questions.append("duplicate timestamps left unresolved")
    elif repeat == "missing_metadata":
        questions.append("missing metadata")
    elif repeat == "delayed_after_stop":
        questions.append("delayed metadata after stop stayed unresolved")
    else:
        questions.append("callback order was not used as a pairing key")
    if unresolved:
        reasons.append("unresolved images: " + ",".join(unresolved))
        return _result("unresolved", reasons, [], preserved, questions)
    reasons.append("paired " + ",".join(paired))
    return _result("paired", reasons, [], preserved, questions if repeat == "reordered" else [])


def _items(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or not value or len(value) > 8:
        raise ValueError(label + " must be a non-empty list of at most 8")
    parsed: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != _ITEM_KEYS:
            raise ValueError(f"{label}[{index}] keys are invalid")
        ident = item["id"]
        stamp = item["timestampNs"]
        if not isinstance(ident, str) or _TOKEN.fullmatch(ident) is None:
            raise ValueError(f"{label}[{index}] id must be a token")
        if ident in seen:
            raise ValueError(f"{label} duplicate id")
        seen.add(ident)
        if not isinstance(stamp, str) or _TS.fullmatch(stamp) is None:
            raise ValueError(f"{label}[{index}] timestampNs must be canonical")
        parsed.append({"id": ident, "timestampNs": stamp})
    return parsed


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    images = _items(payload["images"], "images")
    metadata = _items(payload["metadata"], "metadata")
    bound = payload["boundNs"]
    if type(bound) is not int or bound < 0 or bound > 1_000_000_000:
        raise ValueError("boundNs must be an int from 0 to 1000000000")
    association = payload["association"]
    if association not in _ASSOCIATIONS:
        raise ValueError("association must be exact, nearest, or latest")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is not a TC-P039-02 repeat")
    delayed = payload["delayedMetadataId"]
    if repeat == "delayed_after_stop":
        if not isinstance(delayed, str) or delayed not in {item["id"] for item in metadata}:
            raise ValueError("delayedMetadataId must name a metadata id")
    elif delayed is not None:
        raise ValueError("delayedMetadataId is only valid after stop")
    image_stamps = [item["timestampNs"] for item in images]
    meta_stamps = [item["timestampNs"] for item in metadata]
    if repeat == "reordered":
        if association != "exact":
            return images, metadata, bound, association, repeat, delayed
        if len(set(image_stamps)) != len(image_stamps) or sorted(image_stamps) != sorted(meta_stamps):
            raise ValueError("reordered repeat needs a timestamp bijection")
        if meta_stamps == image_stamps:
            raise ValueError("reordered repeat must differ in callback order")
    elif repeat == "duplicate_timestamps":
        if len(set(meta_stamps)) == len(meta_stamps) and len(set(image_stamps)) == len(image_stamps):
            raise ValueError("duplicate_timestamps needs a repeated timestamp")
    elif repeat == "missing_metadata":
        if set(image_stamps) <= set(meta_stamps):
            raise ValueError("missing_metadata needs an image timestamp with no metadata")
    return images, metadata, bound, association, repeat, delayed


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P039-02 must not yield qualified or allowed")
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
