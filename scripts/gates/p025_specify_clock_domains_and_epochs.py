#!/usr/bin/env python3
"""P025 clock-domain types and timing evidence schema.

Every timestamp carries a domain and units. Correspondence is estimated only
with an identified method and retained samples. A shared take epoch may label
presentation; original sensor times stay in the result. Unsupported
synchronization paths stay unverified.

The deliberate mutant — subtracting timestamps from unrelated domains because
both are nanoseconds — is rejected. This module does not probe a device, does
not qualify a physical S23, and does not execute TC-P025-01 through TC-P025-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P025"
CASE_ID = "P025"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-clock-domain-fixture"
METHOD = (
    "Represent every timestamp with domain and units. Estimate clock correspondence "
    "only using an identified method and retained samples. Use a shared take epoch "
    "for presentation while preserving original sensor times. Mark unsupported "
    "synchronization paths as unverified."
)
FIXTURE = (
    "Audio and video streams whose timestamps look similar numerically but originate "
    "from different clock domains."
)
ORACLE = (
    "The synchronizer refuses to assume equivalence without a measured or documented mapping."
)
MUTANT = "Subtract timestamps from unrelated domains because both are expressed in nanoseconds."

DOMAINS = (
    "sensor",
    "monotonic_system",
    "codec",
    "audio_hardware",
    "encoded_presentation",
)
UNITS = ("ns", "us", "ms", "s")
VALID_METHODS = ("measured_offset", "documented_epoch")
MUTANT_METHOD = "subtract_unrelated_nanoseconds"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
CANONICAL_INT = re.compile(r"0|-?[1-9][0-9]*")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "takeEpoch",
    "timestamps",
    "mappings",
    "unsupportedPaths",
}
EPOCH_KEYS = {"id", "domain", "units", "origin"}
TIMESTAMP_KEYS = {"id", "streamId", "domain", "units", "value", "origin"}
MAPPING_KEYS = {
    "id",
    "fromDomain",
    "toDomain",
    "method",
    "units",
    "retainedSampleIds",
    "offset",
}
PATH_KEYS = {"fromDomain", "toDomain", "status"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


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


def _sint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_INT.fullmatch(value) is not None,
            label + " must be a canonical integer string")
    return value


def _domain(value: object, label: str) -> str:
    text = _text(value, label)
    require(text in DOMAINS, label + " must be a known clock domain")
    return text


def _units(value: object, label: str) -> str:
    text = _text(value, label)
    require(text in UNITS, label + " must be a known unit")
    return text


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def token(timestamp: dict) -> str:
    """Stable inventory token. The numeric value is not rewritten."""
    return (
        f"{timestamp['id']}@{timestamp['streamId']}:{timestamp['domain']}:"
        f"{timestamp['units']}:{timestamp['value']}:{timestamp['origin']}"
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P025 must not decide qualified or allowed")
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


def _timestamp(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, TIMESTAMP_KEYS, f"timestamp {index}")
    ident = _text(item["id"], f"timestamp {index} id")
    require(ident not in seen, "duplicate timestamp id: " + ident)
    seen.add(ident)
    _text(item["streamId"], f"timestamp {index} streamId")
    _domain(item["domain"], f"timestamp {index} domain")
    _units(item["units"], f"timestamp {index} units")
    _uint(item["value"], f"timestamp {index} value")
    _text(item["origin"], f"timestamp {index} origin")
    return item


def _mapping(value: object, index: int, seen: set[str], known_ids: set[str]) -> dict:
    item = exact_keys(value, MAPPING_KEYS, f"mapping {index}")
    ident = _text(item["id"], f"mapping {index} id")
    require(ident not in seen, "duplicate mapping id: " + ident)
    seen.add(ident)
    left = _domain(item["fromDomain"], f"mapping {index} fromDomain")
    right = _domain(item["toDomain"], f"mapping {index} toDomain")
    require(left != right, f"mapping {index} must join two domains")
    _text(item["method"], f"mapping {index} method")
    _units(item["units"], f"mapping {index} units")
    samples = item["retainedSampleIds"]
    require(isinstance(samples, list), f"mapping {index} retainedSampleIds must be a list")
    require(len(samples) == len(set(samples)), f"mapping {index} retained samples must be unique")
    for sample in samples:
        require(isinstance(sample, str) and sample in known_ids,
                f"mapping {index} names an unknown retained sample")
    _sint(item["offset"], f"mapping {index} offset")
    return item


def _path(value: object, index: int, seen: set[tuple[str, str]]) -> dict:
    item = exact_keys(value, PATH_KEYS, f"unsupported path {index}")
    left = _domain(item["fromDomain"], f"unsupported path {index} fromDomain")
    right = _domain(item["toDomain"], f"unsupported path {index} toDomain")
    require(left != right, f"unsupported path {index} must join two domains")
    require(item["status"] == "unverified", f"unsupported path {index} status must be unverified")
    key = (left, right)
    require(key not in seen, "duplicate unsupported path")
    seen.add(key)
    return item


def _epoch(value: object) -> dict:
    item = exact_keys(value, EPOCH_KEYS, "takeEpoch")
    _text(item["id"], "takeEpoch id")
    _domain(item["domain"], "takeEpoch domain")
    _units(item["units"], "takeEpoch units")
    _text(item["origin"], "takeEpoch origin")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P025 timing-evidence schema."""
    exact_keys(document, DOCUMENT_KEYS, "clock document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P025")
    require(document["mapId"] == MAP_ID, "mapId must be s23-clock-domain-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "clock document needs the P025 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _epoch(document["takeEpoch"])
    stamps = document["timestamps"]
    require(isinstance(stamps, list) and stamps, "timestamps must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(stamps):
        _timestamp(item, index, seen)
    mappings = document["mappings"]
    require(isinstance(mappings, list), "mappings must be a list")
    seen_maps: set[str] = set()
    for index, item in enumerate(mappings):
        _mapping(item, index, seen_maps, seen)
    paths = document["unsupportedPaths"]
    require(isinstance(paths, list), "unsupportedPaths must be a list")
    seen_paths: set[tuple[str, str]] = set()
    for index, item in enumerate(paths):
        _path(item, index, seen_paths)


def _samples_ok(mapping: dict) -> bool:
    return len(mapping["retainedSampleIds"]) >= 2


def _valid_mapping(mapping: dict) -> bool:
    return mapping["method"] in VALID_METHODS and _samples_ok(mapping)


def _covers(mapping: dict, left: str, right: str) -> bool:
    return {mapping["fromDomain"], mapping["toDomain"]} == {left, right}


def _lookalike_uncovered(timestamps: list[dict], valid: list[dict]) -> list[tuple[dict, dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for item in timestamps:
        groups.setdefault((item["units"], item["value"]), []).append(item)
    uncovered: list[tuple[dict, dict]] = []
    for group in groups.values():
        for index, left in enumerate(group):
            for right in group[index + 1:]:
                if left["domain"] == right["domain"]:
                    continue
                if any(_covers(mapping, left["domain"], right["domain"]) for mapping in valid):
                    continue
                uncovered.append((left, right))
    return uncovered


def assess(document: dict) -> dict:
    """Refuse cross-domain equivalence that is only numeric.

    Preserved results are the original timestamp tokens, including sensor
    times. A mapping whose method is the nanosecond-subtraction mutant does
    not become a correspondence. Decision is never qualified or allowed.
    """
    validate_document(document)
    timestamps = document["timestamps"]
    preserved = [token(item) for item in timestamps]
    questions = [
        f"{item['fromDomain']}->{item['toDomain']} unverified"
        for item in document["unsupportedPaths"]
    ]
    rejected: list[str] = []
    valid: list[dict] = []
    for mapping in document["mappings"]:
        if mapping["method"] == MUTANT_METHOD:
            rejected.append("subtract-unrelated-nanoseconds")
        elif mapping["method"] not in VALID_METHODS:
            rejected.append("unidentified-method:" + mapping["id"])
        elif not _samples_ok(mapping):
            rejected.append("mapping-without-retained-samples:" + mapping["id"])
        else:
            valid.append(mapping)
    uncovered = _lookalike_uncovered(timestamps, valid)
    if uncovered:
        rejected.append("numeric-unit-equivalence")

    bad_mapping = any(
        item == "subtract-unrelated-nanoseconds" or item.startswith("unidentified-method:")
        or item.startswith("mapping-without-retained-samples:")
        for item in rejected
    )
    if bad_mapping or uncovered:
        decision = "rejected"
        questions.append("timing unverified")
        if not valid:
            questions.append("shared take epoch not applied")
    elif document["unsupportedPaths"]:
        decision = "withheld"
        questions.append("physical synchronization unverified")
    elif valid:
        decision = "mapped"
        questions.append("physical synchronization unverified")
    else:
        decision = "withheld"
        questions.append("timing unverified")
        questions.append("shared take epoch not applied")

    reasons = [ORACLE]
    if not valid:
        reasons.append("no measured or documented mapping was supplied")
    if uncovered:
        reasons.append(
            "equal values in the same units across different clock domains are not a correspondence"
        )
        if any(left["units"] == "ns" and right["units"] == "ns" for left, right in uncovered):
            reasons.append("subtracting unrelated nanosecond timestamps is rejected")
        else:
            reasons.append("matching numeric units alone do not establish clock equivalence")
    if "subtract-unrelated-nanoseconds" in rejected:
        reasons.append(MUTANT)
    if any(item["domain"] == "sensor" for item in timestamps):
        reasons.append("original sensor times are preserved")
    if decision == "mapped":
        reasons.append("correspondence uses an identified method and retained samples")
        reasons.append("a mapped estimate is not physical synchronization or cinema-camera equivalence")
    if decision == "withheld":
        reasons.append("unsupported synchronization paths remain unverified")
    return _result(decision, reasons, rejected, preserved, questions)


def _clock(value: object, label: str) -> dict:
    item = exact_keys(value, TIMESTAMP_KEYS, label)
    _text(item["id"], label + " id")
    _text(item["streamId"], label + " streamId")
    _domain(item["domain"], label + " domain")
    _units(item["units"], label + " units")
    _uint(item["value"], label + " value")
    _text(item["origin"], label + " origin")
    return item


def _pair_mapping(value: object) -> dict | None:
    if value is None:
        return None
    item = exact_keys(value, MAPPING_KEYS, "mapping")
    _text(item["id"], "mapping id")
    _domain(item["fromDomain"], "mapping fromDomain")
    _domain(item["toDomain"], "mapping toDomain")
    require(item["fromDomain"] != item["toDomain"], "mapping must join two domains")
    _text(item["method"], "mapping method")
    _units(item["units"], "mapping units")
    samples = item["retainedSampleIds"]
    require(isinstance(samples, list), "retainedSampleIds must be a list")
    require(all(isinstance(sample, str) and sample for sample in samples),
            "retainedSampleIds must be non-empty strings")
    require(len(samples) == len(set(samples)), "retained samples must be unique")
    _sint(item["offset"], "mapping offset")
    return item


def subtract(left: dict, right: dict, mapping: dict | None) -> dict:
    """Compare two timestamps without assuming a shared clock.

    Same domain, units, and origin may report a difference in reasons only.
    Unrelated domains are not subtracted, even when both values are nanoseconds
    and a mutant mapping says to subtract them. Original tokens are preserved.
    """
    first = _clock(left, "left")
    second = _clock(right, "right")
    link = _pair_mapping(mapping)
    preserved = [token(first), token(second)]
    same_domain = first["domain"] == second["domain"]
    same_units = first["units"] == second["units"]
    same_origin = first["origin"] == second["origin"]

    if same_domain and same_units and same_origin:
        delta = int(first["value"]) - int(second["value"])
        return _result(
            "same_domain",
            [
                f"same-domain difference {delta}{first['units']} stays inside {first['domain']}",
                "a same-domain difference is not cross-domain equivalence",
            ],
            [],
            preserved,
            [],
        )
    if same_domain and not same_origin:
        return _result(
            "withheld",
            [
                "changed origin inside one domain is not a licence to subtract",
                ORACLE,
            ],
            ["origin-changed"],
            preserved,
            ["timing unverified"],
        )
    if same_domain and not same_units:
        return _result(
            "withheld",
            ["unit conversion inside one domain needs a documented scale", ORACLE],
            ["unit-mismatch"],
            preserved,
            ["timing unverified"],
        )

    usable = (
        link is not None
        and link["method"] in VALID_METHODS
        and _samples_ok(link)
        and _covers(link, first["domain"], second["domain"])
        and link["units"] == first["units"] == second["units"]
        and first["id"] in link["retainedSampleIds"]
        and second["id"] in link["retainedSampleIds"]
    )
    if usable:
        return _result(
            "mapped",
            [
                f"identified method {link['method']} retained {len(link['retainedSampleIds'])} samples",
                "the offset is a correspondence estimate, not clock equivalence",
                "original timestamps are preserved",
                ORACLE,
            ],
            [],
            preserved,
            ["physical synchronization unverified"],
        )
    rejected: list[str] = []
    if (link is not None and link["method"] == MUTANT_METHOD) or (same_units and first["units"] == "ns"):
        rejected.append("subtract-unrelated-nanoseconds")
    if same_units:
        rejected.append("numeric-unit-equivalence")
    else:
        rejected.append("missing-mapping")
    reasons = [ORACLE, "refusing to subtract unrelated clock domains"]
    if same_units and first["units"] == "ns":
        reasons.append("matching nanosecond units are not a shared epoch")
    elif same_units:
        reasons.append("matching numeric units alone do not establish clock equivalence")
    if "subtract-unrelated-nanoseconds" in rejected:
        reasons.append(MUTANT)
    return _result("rejected", reasons, rejected, preserved, ["timing unverified"])


def present(timestamp: dict, take_epoch: dict, mapping: dict | None) -> dict:
    """Label presentation on the take epoch without replacing sensor time.

    No presentation value is invented when the mapping is missing, mutant, or
    aimed at another domain. The original sensor token always remains.
    """
    stamp = _clock(timestamp, "timestamp")
    epoch = _epoch(take_epoch)
    link = _pair_mapping(mapping)
    original = token(stamp)
    if stamp["domain"] != "sensor":
        return _result(
            "withheld",
            [
                "presentation epoch is applied to sensor timestamps only",
                "original time is preserved",
            ],
            [],
            [original],
            ["presentation withheld"],
        )
    mutant = link is not None and link["method"] == MUTANT_METHOD
    usable = (
        link is not None
        and not mutant
        and link["method"] in VALID_METHODS
        and _samples_ok(link)
        and stamp["id"] in link["retainedSampleIds"]
        and _covers(link, "sensor", epoch["domain"])
        and link["units"] == stamp["units"] == epoch["units"]
    )
    if mutant:
        return _result(
            "rejected",
            [MUTANT, "original sensor time is preserved", ORACLE],
            ["subtract-unrelated-nanoseconds"],
            [original],
            ["presentation withheld"],
        )
    if not usable:
        return _result(
            "withheld",
            [
                "shared take epoch is not applied without a measured or documented mapping",
                "original sensor time is preserved",
                ORACLE,
            ],
            ["missing-mapping"] if link is None else ["mapping-not-applicable"],
            [original],
            ["presentation withheld"],
        )
    presentation = f"presentation:{epoch['id']}:{link['offset']}{epoch['units']}"
    return _result(
        "presented",
        [
            "shared take epoch used for presentation",
            "original sensor time is preserved",
            "presentation is not physical synchronization",
        ],
        [],
        [original, presentation],
        ["physical synchronization unverified"],
    )
