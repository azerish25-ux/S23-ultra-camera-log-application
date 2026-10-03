#!/usr/bin/env python3
"""P049 signed RAW normalization on a host fixture.

Source codes become declared linear units using per-frame black and white
references. Values below black stay negative. Values above a conservative
white stay greater than one. A normalized value of one is that source white
reference, not a universal scene-white boundary. Sensor saturation is counted
separately from export-clip candidates. CFA phase uses sensor coordinates.

The deliberate mutant — clamp every normalized sample into zero-to-one
immediately — is rejected. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P049-01 through TC-P049-08.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any


PHASE = "P049"
CASE_ID = "P049"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-signed-raw-normalization-fixture"
METHOD = (
    "Use the correct per-frame black and white references with CFA-aware indexing. "
    "Validate white exceeds black and retain clipping counts before normalization. "
    "Apply crop and optical-black policies explicitly; a normalized value of one is a "
    "source reference, not a universal scene-white boundary."
)
FIXTURE = (
    "Codes below black, at black, near white, and beyond an intentionally conservative "
    "white estimate."
)
ORACLE = (
    "The reference retains signed values and reports saturation separately from any "
    "export clipping."
)
MUTANT = "Clamp every normalized sample into zero-to-one immediately."
HOST_LIMIT = "this host record does not qualify a physical S23"
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
POLICIES = ("exclude", "retain-diagnostic")
REGIONS = ("optical-black", "active", "outside-crop")
VECTOR_CLASSES = (
    "below-black",
    "at-black",
    "near-white",
    "source-white",
    "beyond-white",
    "sensor-saturated",
)
_REQUIRED_VECTORS = ("below-black", "at-black", "near-white", "beyond-white")
_PHASE = {
    "RGGB": {(0, 0): "R", (1, 0): "G", (0, 1): "G", (1, 1): "B"},
    "GRBG": {(0, 0): "G", (1, 0): "R", (0, 1): "B", (1, 1): "G"},
    "GBRG": {(0, 0): "G", (1, 0): "B", (0, 1): "R", (1, 1): "G"},
    "BGGR": {(0, 0): "B", (1, 0): "G", (0, 1): "G", (1, 1): "R"},
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
UINT = re.compile(r"0|[1-9][0-9]*")
CROP_TEXT = re.compile(
    r"^([1-9][0-9]*)x([1-9][0-9]*)\+(0|[1-9][0-9]*)\+(0|[1-9][0-9]*)$"
)
RATIONAL = re.compile(r"[1-9][0-9]*(?:/[1-9][0-9]*)?")
COUNT_KEYS = (
    "below-black",
    "at-black",
    "interior",
    "near-white",
    "at-white",
    "beyond-white",
    "sensor-saturated",
    "export-clip-candidates",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
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
    "blackLevel",
    "whiteLevel",
    "sensorSaturation",
    "exportClipMax",
    "nearWhiteMargin",
    "cfa",
    "crop",
    "width",
    "height",
    "opticalBlackColumns",
    "opticalBlackPolicy",
    "samples",
    "referenceVectors",
}
SAMPLE_KEYS = {"x", "y", "code", "region"}
VECTOR_KEYS = {"code", "normalized", "class"}
REFERENCE_VECTORS = (
    {"code": "40", "black": "64", "white": "800", "normalized": "-3/92", "class": "below-black"},
    {"code": "64", "black": "64", "white": "800", "normalized": "0", "class": "at-black"},
    {"code": "780", "black": "64", "white": "800", "normalized": "179/184", "class": "near-white"},
    {"code": "800", "black": "64", "white": "800", "normalized": "1", "class": "source-white"},
    {"code": "900", "black": "64", "white": "800", "normalized": "209/184", "class": "beyond-white"},
    {
        "code": "1023",
        "black": "64",
        "white": "800",
        "normalized": "959/736",
        "class": "sensor-saturated",
    },
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "signed_reference"}


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


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive_int(value: object, label: str) -> int:
    require(type(value) is int and value > 0, label + " must be a positive int")
    return value


def _nonneg_int(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, label + " must be a non-negative int")
    return value


def channel_at(cfa: str, x: int, y: int) -> str:
    """Bayer channel in sensor coordinates. Crop origin does not reset the phase."""
    require(cfa in CFAS, "cfa is unknown")
    require(type(x) is int and x >= 0 and type(y) is int and y >= 0, "coordinates must be ints")
    return _PHASE[cfa][(x % 2, y % 2)]


def linear_ratio(code: str, black: str, white: str) -> str:
    """Signed (code-black)/(white-black). Not clamped into zero-to-one."""
    sample = int(_uint(code, "code"))
    low = int(_uint(black, "black"))
    high = int(_uint(white, "white"))
    require(high > low, "white must exceed black")
    return str(Fraction(sample - low, high - low))


def clamp_unit(ratio: str) -> str:
    """Mutant helper. Honest normalization must not store this result."""
    require(isinstance(ratio, str) and ratio, "ratio must be a string")
    value = Fraction(ratio)
    if value < 0:
        return "0"
    if value > 1:
        return "1"
    return str(value)


def check_reference_vectors() -> None:
    """Recompute authored vectors. A clamp mutant cannot satisfy the signed rows."""
    for item in REFERENCE_VECTORS:
        got = linear_ratio(item["code"], item["black"], item["white"])
        require(got == item["normalized"], "reference vector drifted: " + item["class"])
        require(got == str(Fraction(
            int(item["code"]) - int(item["black"]),
            int(item["white"]) - int(item["black"]),
        )), "reference vector is not the signed ratio")
        if item["class"] in {"below-black", "beyond-white", "sensor-saturated"}:
            require(got != clamp_unit(got), "signed vector collapsed to the unit clamp")


def _positive_rational(value: object, label: str) -> Fraction:
    require(isinstance(value, str) and RATIONAL.fullmatch(value) is not None,
            label + " must be a canonical positive rational")
    frac = Fraction(value)
    require(frac > 0 and str(frac) == value, label + " must be reduced")
    return frac


def _crop(value: object) -> tuple[int, int, int, int]:
    require(isinstance(value, str), "crop must be a string")
    match = CROP_TEXT.fullmatch(value)
    require(match is not None, "crop must look like widthxheight+left+top")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _expected_region(x: int, y: int, geometry: dict[str, int]) -> str:
    if x < geometry["ob"]:
        return "optical-black"
    if (geometry["left"] <= x < geometry["left"] + geometry["crop_w"]
            and geometry["top"] <= y < geometry["top"] + geometry["crop_h"]):
        return "active"
    return "outside-crop"


def _sample(value: object, index: int, width: int, height: int, geometry: dict[str, int],
            seen: set[tuple[int, int]]) -> dict:
    item = exact_keys(value, SAMPLE_KEYS, f"sample {index}")
    x = _nonneg_int(item["x"], f"sample {index} x")
    y = _nonneg_int(item["y"], f"sample {index} y")
    require(x < width and y < height, f"sample {index} is outside the frame")
    require((x, y) not in seen, f"duplicate sample at {x},{y}")
    seen.add((x, y))
    _uint(item["code"], f"sample {index} code")
    region = item["region"]
    require(region in REGIONS, f"sample {index} region is unknown")
    require(region == _expected_region(x, y, geometry),
            f"sample {index} region does not match crop and optical-black policy")
    return item


def _vector_class(code: int, black: int, white: int, saturation: int, margin: int) -> str:
    if code < black:
        return "below-black"
    if code == black:
        return "at-black"
    if code == white:
        return "source-white"
    if code >= saturation:
        return "sensor-saturated"
    if code > white:
        return "beyond-white"
    if white - margin <= code < white:
        return "near-white"
    return "interior"


def _vector(value: object, index: int, black: int, white: int, saturation: int,
            margin: int, seen: set[str]) -> dict:
    item = exact_keys(value, VECTOR_KEYS, f"reference vector {index}")
    code_text = _uint(item["code"], f"reference vector {index} code")
    code = int(code_text)
    label = item["class"]
    require(label in VECTOR_CLASSES, f"reference vector {index} class is unknown")
    require(label not in seen, "duplicate reference class: " + label)
    seen.add(label)
    require(_vector_class(code, black, white, saturation, margin) == label,
            f"reference vector {index} class does not match the code")
    expected = linear_ratio(code_text, str(black), str(white))
    require(item["normalized"] == expected,
            f"reference vector {index} is not the signed ratio")
    if label in {"below-black", "beyond-white", "sensor-saturated"}:
        require(item["normalized"] != clamp_unit(expected),
                f"reference vector {index} was clamped")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P049 signed-normalization fixture."""
    exact_keys(document, DOCUMENT_KEYS, "normalization document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P049")
    require(document["mapId"] == MAP_ID, "mapId must be s23-signed-raw-normalization-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "normalization document needs the P049 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    black = int(_uint(document["blackLevel"], "blackLevel"))
    white = int(_uint(document["whiteLevel"], "whiteLevel"))
    require(white > black, "white must exceed black")
    saturation = int(_uint(document["sensorSaturation"], "sensorSaturation"))
    require(saturation >= white, "sensorSaturation must be at least the white level")
    _positive_rational(document["exportClipMax"], "exportClipMax")
    margin = _positive_int(document["nearWhiteMargin"], "nearWhiteMargin")
    require(margin < white - black, "nearWhiteMargin must be smaller than the white-black span")
    require(document["cfa"] in CFAS, "cfa is unknown")
    crop_w, crop_h, left, top = _crop(document["crop"])
    width = _positive_int(document["width"], "width")
    height = _positive_int(document["height"], "height")
    ob = _nonneg_int(document["opticalBlackColumns"], "opticalBlackColumns")
    require(ob <= width, "opticalBlackColumns exceed the width")
    require(left >= ob, "crop overlaps optical black")
    require(left + crop_w <= width and top + crop_h <= height, "crop does not fit the frame")
    require(document["opticalBlackPolicy"] in POLICIES, "opticalBlackPolicy is unknown")
    geometry = {"ob": ob, "left": left, "top": top, "crop_w": crop_w, "crop_h": crop_h}
    samples = document["samples"]
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    seen: set[tuple[int, int]] = set()
    for index, item in enumerate(samples):
        _sample(item, index, width, height, geometry, seen)
    require(len(seen) == width * height, "samples must cover every pixel exactly once")
    vectors = document["referenceVectors"]
    require(isinstance(vectors, list) and vectors, "referenceVectors must be a non-empty list")
    classes: set[str] = set()
    for index, item in enumerate(vectors):
        _vector(item, index, black, white, saturation, margin, classes)
    missing = [name for name in _REQUIRED_VECTORS if name not in classes]
    require(not missing, "missing reference classes: " + ", ".join(missing))


def _counts(document: dict) -> dict[str, int]:
    black = int(document["blackLevel"])
    white = int(document["whiteLevel"])
    saturation = int(document["sensorSaturation"])
    margin = document["nearWhiteMargin"]
    export_max = Fraction(document["exportClipMax"])
    policy = document["opticalBlackPolicy"]
    counts = {key: 0 for key in COUNT_KEYS}
    for sample in document["samples"]:
        if sample["region"] == "outside-crop":
            continue
        if sample["region"] == "optical-black" and policy != "retain-diagnostic":
            continue
        code = int(sample["code"])
        if code < black:
            counts["below-black"] += 1
        elif code == black:
            counts["at-black"] += 1
        elif code < white - margin:
            counts["interior"] += 1
        elif code < white:
            counts["near-white"] += 1
        elif code == white:
            counts["at-white"] += 1
        else:
            counts["beyond-white"] += 1
        if code >= saturation:
            counts["sensor-saturated"] += 1
        ratio = Fraction(linear_ratio(sample["code"], document["blackLevel"], document["whiteLevel"]))
        if ratio < 0 or ratio > export_max:
            counts["export-clip-candidates"] += 1
    return counts


def sample_token(sample: dict, cfa: str, black: str, white: str) -> str:
    """Inventory token. The norm is the signed ratio, never the unit clamp."""
    ratio = linear_ratio(sample["code"], black, white)
    channel = channel_at(cfa, sample["x"], sample["y"])
    return (
        f"s:{sample['x']},{sample['y']}:code={sample['code']}:region={sample['region']}"
        f":norm={ratio}:ch={channel}"
    )


def _preserved(document: dict) -> list[str]:
    counts = _counts(document)
    preserved = [
        f"cfa:{document['cfa']}",
        f"crop:{document['crop']}",
        f"black:{document['blackLevel']}",
        f"white:{document['whiteLevel']}",
        f"saturation:{document['sensorSaturation']}",
        f"export-clip-max:{document['exportClipMax']}",
        f"policy:{document['opticalBlackPolicy']}",
        f"optical-black-columns:{document['opticalBlackColumns']}",
    ]
    preserved.extend(f"{key}:{counts[key]}" for key in COUNT_KEYS)
    ordered = sorted(document["samples"], key=lambda item: (item["y"], item["x"]))
    preserved.extend(
        sample_token(item, document["cfa"], document["blackLevel"], document["whiteLevel"])
        for item in ordered
    )
    for vector in document["referenceVectors"]:
        preserved.append(f"vector:{vector['class']}:{vector['code']}->{vector['normalized']}")
    preserved.append("source-white-is-not-scene-white")
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P049 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _questions() -> list[str]:
    return [
        "host fixture is not a physical S23 measurement",
        "normalized one is not scene white",
        "physical sensor black and white levels unverified",
    ]


def assess(document: dict) -> dict:
    """Retain signed linear units and separate saturation from export clipping.

    Decision is signed_reference. It is never qualified or allowed. Clamping
    into zero-to-one is not applied.
    """
    validate_document(document)
    check_reference_vectors()
    counts = _counts(document)
    reasons = [
        ORACLE,
        "white exceeds black",
        "clipping counts retained before normalization",
        "normalized one is a source white reference, not a universal scene-white boundary",
        "sensor saturation is reported separately from export clipping",
        f"optical-black policy {document['opticalBlackPolicy']} applied explicitly",
        "CFA phase uses sensor coordinates, not the crop origin",
        HOST_LIMIT,
    ]
    if counts["below-black"]:
        reasons.append("signed values below black retained")
    if counts["beyond-white"] or counts["sensor-saturated"]:
        reasons.append("over-range above the conservative white estimate retained")
    return _result("signed_reference", reasons, [], _preserved(document), _questions())


def apply_immediate_clamp(document: dict) -> dict:
    """Reject the mutant. Preserved norms stay signed; the clamp is not stored."""
    validate_document(document)
    preserved = _preserved(document)
    require(any(item.startswith("s:") and ":norm=-" in item for item in preserved),
            "mutant rejection still needs a signed below-black sample")
    return _result(
        "rejected",
        [
            MUTANT,
            "immediate zero-to-one clamp rejected",
            "signed samples were not replaced by clamped copies",
            ORACLE,
            HOST_LIMIT,
        ],
        ["immediate-zero-to-one-clamp"],
        preserved,
        _questions() + ["clamped zero-to-one copies are not the retained reference"],
    )
