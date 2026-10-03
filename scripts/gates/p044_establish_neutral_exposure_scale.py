#!/usr/bin/env python3
"""P044 neutral exposure scale on a host fixture.

A user-confirmed patch is inspected for clipping, texture, signal level, and
color neutrality. ROI coordinates and the source frame identity stay on the
result. Exposure scale is computed only from valid patches and stays separate
from chromatic fitting. Invalid patches are rejected. The whole-frame mean is
never treated as middle grey.

The deliberate mutant — assuming mean image luminance always corresponds to
middle grey — is rejected. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P044-01 through TC-P044-08.
"""

from __future__ import annotations

import math
import re
from typing import Any


PHASE = "P044"
CASE_ID = "P044"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-neutral-exposure-scale-fixture"
METHOD = (
    "Inspect a user-confirmed patch for clipping, texture, signal level, and color "
    "neutrality. Retain ROI coordinates and source frame identity. Apply exposure scale "
    "separately from chromatic fitting, and reject invalid patches rather than silently "
    "guessing from the whole frame."
)
FIXTURE = (
    "A bright white object misidentified as eighteen-percent grey and a grey patch "
    "partly clipped by a specular reflection."
)
ORACLE = (
    "The calibration workflow requests valid evidence and records uncertainty instead of "
    "producing a confidently measured scale."
)
MUTANT = "Assume the mean image luminance always corresponds to middle grey."
INSPECTION = "patch-inspection"
MUTANT_TEST = "mean-luminance-middle-grey"
SOLE_TESTS = (INSPECTION, MUTANT_TEST)
NEUTRAL_DELTA_LIMIT = 50
IDENTIFIED = ("eighteen-percent-grey", "bright-white", "unknown")
ACTUAL = ("eighteen-percent-grey", "bright-white", "partial-clip", "unknown")
TEXTURES = ("low", "high")
HOST_LIMIT = "a host estimate does not qualify a physical S23"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
CANONICAL_POS = re.compile(r"[1-9][0-9]*")
ROI_TEXT = re.compile(
    r"^(?:0|[1-9][0-9]*),(?:0|[1-9][0-9]*),([1-9][0-9]*),([1-9][0-9]*)$"
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
    "sourceFrameId",
    "wholeFrameMeanLuminance",
    "middleGreyCode",
    "clipCeiling",
    "patches",
}
PATCH_KEYS = {
    "id",
    "roi",
    "userConfirmed",
    "identifiedAs",
    "signalLevel",
    "texture",
    "clippedFraction",
    "specular",
    "neutralDelta",
    "actualClass",
}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "provisional"}


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


def _positive(value: object, label: str) -> str:
    text = _uint(value, label)
    require(CANONICAL_POS.fullmatch(text) is not None, label + " must be positive")
    return text


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def exposure_ratio(middle_grey: str, signal_level: str) -> str:
    """Reduced middle-grey / signal ratio. Not a whole-frame substitution."""
    middle = int(_positive(middle_grey, "middleGreyCode"))
    signal = int(_positive(signal_level, "signalLevel"))
    divisor = math.gcd(middle, signal)
    return f"{middle // divisor}/{signal // divisor}"


def patch_token(patch: dict) -> str:
    """Stable inventory token. Signal and class are not rewritten."""
    specular = "1" if patch["specular"] is True else "0"
    return (
        f"{patch['id']}:signal={patch['signalLevel']}:clip={patch['clippedFraction']}"
        f":specular={specular}:class={patch['actualClass']}:as={patch['identifiedAs']}"
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P044 must not decide qualified or allowed")
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


def _patch(value: object, index: int, seen: set[str], ceiling: int) -> dict:
    item = exact_keys(value, PATCH_KEYS, f"patch {index}")
    ident = _text(item["id"], f"patch {index} id")
    require(ident not in seen, "duplicate patch id: " + ident)
    seen.add(ident)
    roi = _text(item["roi"], f"patch {index} roi")
    require(ROI_TEXT.fullmatch(roi) is not None, f"patch {index} roi must look like x,y,w,h")
    _bool(item["userConfirmed"], f"patch {index} userConfirmed")
    require(item["identifiedAs"] in IDENTIFIED, f"patch {index} identifiedAs is unknown")
    signal = int(_positive(item["signalLevel"], f"patch {index} signalLevel"))
    require(signal <= ceiling, f"patch {index} signalLevel exceeds the clip ceiling")
    require(item["texture"] in TEXTURES, f"patch {index} texture must be low or high")
    clipped = int(_uint(item["clippedFraction"], f"patch {index} clippedFraction"))
    require(0 <= clipped <= 100, f"patch {index} clippedFraction must be 0..100")
    _bool(item["specular"], f"patch {index} specular")
    _uint(item["neutralDelta"], f"patch {index} neutralDelta")
    require(item["actualClass"] in ACTUAL, f"patch {index} actualClass is unknown")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P044 neutral-scale fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "neutral scale document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P044")
    require(document["mapId"] == MAP_ID, "mapId must be s23-neutral-exposure-scale-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "neutral scale document needs the P044 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _text(document["sourceFrameId"], "sourceFrameId")
    mean = int(_positive(document["wholeFrameMeanLuminance"], "wholeFrameMeanLuminance"))
    middle = int(_positive(document["middleGreyCode"], "middleGreyCode"))
    ceiling = int(_positive(document["clipCeiling"], "clipCeiling"))
    require(middle < ceiling, "middleGreyCode must be below the clip ceiling")
    require(mean <= ceiling, "wholeFrameMeanLuminance exceeds the clip ceiling")
    patches = document["patches"]
    require(isinstance(patches, list) and patches, "patches must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(patches):
        _patch(item, index, seen, ceiling)


def _claims_for_patch(patch: dict, ceiling: int) -> list[str]:
    ident = patch["id"]
    claims: list[str] = []
    signal = int(patch["signalLevel"])
    clip = int(patch["clippedFraction"])
    delta = int(patch["neutralDelta"])
    if (
        patch["identifiedAs"] == "eighteen-percent-grey"
        and patch["actualClass"] != "eighteen-percent-grey"
    ):
        claims.append(f"{ident}:misidentified-{patch['actualClass']}")
    elif patch["identifiedAs"] != "eighteen-percent-grey":
        claims.append(f"{ident}:not-grey-target")
    if patch["specular"] is True and (clip > 0 or signal >= ceiling):
        claims.append(f"{ident}:partial-specular-clip")
    elif patch["specular"] is True:
        claims.append(f"{ident}:specular")
    elif clip > 0 or signal >= ceiling:
        claims.append(f"{ident}:clipped")
    if patch["texture"] == "high":
        claims.append(f"{ident}:textured")
    if patch["userConfirmed"] is not True:
        claims.append(f"{ident}:unconfirmed")
    if delta > NEUTRAL_DELTA_LIMIT:
        claims.append(f"{ident}:not-neutral")
    return claims


def _valid(patch: dict, ceiling: int) -> bool:
    return not _claims_for_patch(patch, ceiling)


def assess(document: dict, sole_test: str = INSPECTION) -> dict:
    """Request valid neutral evidence. Never treat frame mean as middle grey.

    sole_test "mean-luminance-middle-grey" is the mutant. It is rejected even
    when the numbers are finite. Patch tokens, ROI coordinates, and the source
    frame stay in preservedResults. No confidently measured scale is emitted.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS,
            "sole_test must be patch-inspection or mean-luminance-middle-grey")
    ceiling = int(document["clipCeiling"])
    middle = document["middleGreyCode"]
    mean = document["wholeFrameMeanLuminance"]
    patches = document["patches"]
    rejected: list[str] = []
    for patch in patches:
        rejected.extend(_claims_for_patch(patch, ceiling))
    valid = [patch for patch in patches if _valid(patch, ceiling)]
    ratios = [exposure_ratio(middle, patch["signalLevel"]) for patch in valid]
    consistent = bool(valid) and len(set(ratios)) == 1
    if int(mean) != int(middle):
        rejected.append("whole-frame-mean-not-middle-grey")
    if valid and not consistent:
        rejected.append("scale-disagreement")

    preserved = [f"frame:{document['sourceFrameId']}"]
    preserved.extend(f"roi:{patch['id']}:{patch['roi']}" for patch in patches)
    preserved.extend(patch_token(patch) for patch in patches)
    preserved.append(f"whole-frame-mean:{mean}")
    preserved.append(f"middle-grey:{middle}")
    preserved.append("chromatic-fit:withheld")
    if consistent:
        preserved.append(f"exposure-scale:{ratios[0]}")
        widest = max(int(patch["neutralDelta"]) for patch in valid)
        preserved.append(f"uncertainty:neutral-delta-{widest}")
    elif valid:
        preserved.extend(
            f"candidate-scale:{patch['id']}:{ratio}" for patch, ratio in zip(valid, ratios)
        )

    reasons = [
        ORACLE,
        "exposure scale is separate from chromatic fitting",
    ]
    for patch in patches:
        if f"{patch['id']}:misidentified-bright-white" in rejected:
            reasons.append(
                f"{patch['id']} is a bright white object misidentified as eighteen-percent grey"
            )
        if f"{patch['id']}:partial-specular-clip" in rejected:
            reasons.append(f"{patch['id']} is partly clipped by a specular reflection")
    if int(mean) != int(middle):
        reasons.append(f"whole-frame mean {mean} is not middle grey {middle}")
    else:
        reasons.append("equal frame mean is not used as the neutral target")
    if consistent:
        reasons.append(
            f"provisional exposure scale {ratios[0]} is not a confidently measured profile"
        )
    else:
        reasons.append("uncertainty recorded; no confidently measured scale")
    if any(_claims_for_patch(patch, ceiling) for patch in patches):
        reasons.append("invalid patches are rejected instead of guessing from the whole frame")
    reasons.append(HOST_LIMIT)

    questions = ["host fixture is not a physical S23 measurement"]
    if not valid:
        questions.append("valid neutral-patch evidence requested")
        questions.append("uncertainty recorded; scale not measured")
    elif not consistent:
        questions.append("valid patches disagree; scale withheld")
    else:
        questions.append("provisional scale records uncertainty and is not a confident measurement")
    if int(mean) == int(middle):
        questions.append("frame-mean equality is not a neutral-target measurement")

    if consistent and sole_test != MUTANT_TEST:
        decision = "provisional"
    else:
        decision = "withheld"
    if sole_test == MUTANT_TEST:
        decision = "rejected"
        rejected.insert(0, "mean-luminance-middle-grey")
        reasons.append(MUTANT)
        questions.append("mean luminance was not treated as middle grey")

    return _result(decision, reasons, rejected, preserved, questions)
