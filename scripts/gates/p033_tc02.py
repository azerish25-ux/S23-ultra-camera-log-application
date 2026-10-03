"""TC-P033-02 metadata callback reordering.

Images and metadata may arrive in different orders, including one exact
timestamp match that is delayed. Pair only equal sensor timestamps inside
the bounded wait. Nearest-time and latest-metadata association are rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P033-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain unresolved "
    "status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."
REPEATS = ("duplicate timestamps", "missing metadata", "delayed metadata after stop")
_ASSOCIATIONS = ("exact", "nearest", "latest")
_PAYLOAD_KEYS = (
    "imageIds",
    "imageTimestamps",
    "metadataIds",
    "metadataTimestamps",
    "metadataDelaysNs",
    "metadataAfterStop",
    "association",
    "boundNs",
    "stopped",
    "inventory",
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
    """Pair exact sensor timestamps, or keep the image unresolved."""
    data = _payload(payload)
    reasons = [
        "association " + data["association"],
        "boundNs " + str(data["boundNs"]),
    ]
    rejected: list[str] = []
    pairs: list[tuple[str, str]] = []
    unresolved: list[str] = []
    if data["association"] == "nearest":
        rejected.append("nearest-time")
        reasons.append(NEGATIVE)
    elif data["association"] == "latest":
        rejected.append("latest-metadata")
        reasons.append(NEGATIVE)
    else:
        pairs, unresolved, extra = _exact_pairs(data)
        rejected.extend(extra)
        if unresolved:
            reasons.append(EXPECTED)
        else:
            reasons.append(EXPECTED)
            reasons.append("every image paired on an equal sensor timestamp inside the bound")
    if rejected and data["association"] != "exact":
        decision = "rejected"
    elif unresolved or rejected:
        decision = "unresolved" if data["association"] == "exact" else "rejected"
    else:
        decision = "paired"
    if data["association"] != "exact":
        pairs = []
        unresolved = list(data["imageIds"])
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-02 must not yield qualified or allowed")
    questions = ["unresolved metadata remains unpaired"] if unresolved else []
    return _result(decision, reasons, rejected, _preserved(data, pairs, unresolved), questions)


def _exact_pairs(data: dict) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    stamps = data["imageTimestamps"]
    meta_stamps = data["metadataTimestamps"]
    if len(set(stamps)) != len(stamps) or len(set(meta_stamps)) != len(meta_stamps):
        return [], list(data["imageIds"]), ["ambiguous-timestamp"]
    pairs: list[tuple[str, str]] = []
    unresolved: list[str] = []
    extra: list[str] = []
    for image_id, stamp in zip(data["imageIds"], stamps):
        indexes = [index for index, meta in enumerate(meta_stamps) if meta == stamp]
        if not indexes:
            unresolved.append(image_id)
            if "missing-metadata" not in extra:
                extra.append("missing-metadata")
            continue
        index = indexes[0]
        if data["metadataAfterStop"][index] and data["stopped"]:
            unresolved.append(image_id)
            if "delayed-after-stop" not in extra:
                extra.append("delayed-after-stop")
            continue
        if data["metadataDelaysNs"][index] > data["boundNs"]:
            unresolved.append(image_id)
            if "outside-bound" not in extra:
                extra.append("outside-bound")
            continue
        pairs.append((image_id, data["metadataIds"][index]))
    return pairs, unresolved, extra


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    image_ids = _ids(payload["imageIds"], "imageIds")
    image_stamps = _stamps(payload["imageTimestamps"], "imageTimestamps", len(image_ids))
    meta_ids = _ids(payload["metadataIds"], "metadataIds")
    meta_stamps = _stamps(payload["metadataTimestamps"], "metadataTimestamps", len(meta_ids))
    delays = _delay_list(payload["metadataDelaysNs"], len(meta_ids))
    after = _bool_list(payload["metadataAfterStop"], len(meta_ids))
    association = payload["association"]
    if association not in _ASSOCIATIONS:
        raise ValueError("association must be exact, nearest, or latest")
    bound = payload["boundNs"]
    if type(bound) is not int or bound < 0:
        raise ValueError("boundNs must be a non-negative int")
    if set(image_ids) & set(meta_ids):
        raise ValueError("image and metadata ids must be disjoint")
    return {
        "imageIds": image_ids,
        "imageTimestamps": image_stamps,
        "metadataIds": meta_ids,
        "metadataTimestamps": meta_stamps,
        "metadataDelaysNs": delays,
        "metadataAfterStop": after,
        "association": association,
        "boundNs": bound,
        "stopped": _bool(payload["stopped"], "stopped"),
        "inventory": _tokens(payload["inventory"], "inventory"),
    }


def _preserved(data: dict, pairs: list[tuple[str, str]], unresolved: list[str]) -> list[str]:
    preserved = list(data["inventory"])
    preserved.extend("image:" + item for item in data["imageIds"])
    preserved.extend("metadata:" + item for item in data["metadataIds"])
    preserved.extend("timestamp:" + item for item in data["imageTimestamps"])
    preserved.extend("pair:" + image + "->" + meta for image, meta in pairs)
    preserved.extend("unresolved:" + item for item in unresolved)
    return preserved


def _ids(value: object, name: str) -> list[str]:
    items = _tokens(value, name)
    return items


def _stamps(value: object, name: str, count: int) -> list[str]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{name} length must match its ids")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.isdigit() or (len(item) > 1 and item[0] == "0"):
            raise ValueError(f"{name} must be canonical integer strings")
        items.append(item)
    return items


def _delay_list(value: object, count: int) -> list[int]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError("metadataDelaysNs length must match metadata ids")
    items = []
    for item in value:
        if type(item) is not int or item < 0:
            raise ValueError("metadataDelaysNs items must be non-negative ints")
        items.append(item)
    return items


def _bool_list(value: object, count: int) -> list[bool]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError("metadataAfterStop length must match metadata ids")
    items = []
    for item in value:
        if type(item) is not bool:
            raise ValueError("metadataAfterStop items must be bools")
        items.append(item)
    return items


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    items = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip() or item in seen:
            raise ValueError(f"{name} items must be unique non-empty strings")
        seen.add(item)
        items.append(item)
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-02 must not yield qualified or allowed")
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
