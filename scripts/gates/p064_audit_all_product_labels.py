#!/usr/bin/env python3
"""P064 source-aware product labels on a host fixture.

Centralize wording for RAW-derived, HLG-derived, SDR-derived, provisional
calibration, virtual format, and processed look. UI labels are checked
against machine-readable evidence. Marketing must not imply sensor
enlargement, guaranteed ARRI equivalence, or recovered clipped detail.

The fixture is a rendered SDR import exported with a large-format recipe and
a ten-bit codec. The honest interface calls that a simulated look. The mutant
builds the export label from the film preset name alone and is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P064-01 through TC-P064-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P064"
CASE_ID = "P064"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-product-label-fixture"
METHOD = (
    "Centralize wording for RAW-derived, HLG-derived, SDR-derived, provisional "
    "calibration, virtual format, and processed look. Test UI labels against "
    "machine-readable evidence. Marketing text must not imply sensor enlargement, "
    "guaranteed ARRI equivalence, or recovered clipped detail."
)
FIXTURE = "A rendered SDR import exported with a large-format recipe and a ten-bit codec."
ORACLE = (
    "The interface identifies a simulated look from an SDR source rather than "
    "native large-format or sensor-derived Log capture."
)
MUTANT = "Build export labels only from the selected film preset name."
HONEST = "source-aware"
MUTANT_MODE = "preset-only"
INTERPRETATIONS = {HONEST, MUTANT_MODE}
HOST_LIMIT = "host fixture does not qualify a physical S23 or product-label capture"
SDR_ORIGIN = "rendered-sdr-import"
LARGE_RECIPE = "large-format"
PRESET_NAME = "Large Format Log"
CODEC = "Main10"
CALIBRATION = "provisional-calibration"
VIRTUAL = "virtual-format"
PROCESSED = "processed-look"
SURFACES = ("select", "export", "share")
ACQUISITIONS = {"RAW-derived", "HLG-derived", "SDR-derived"}
TRANSFERS = {"Rec.709", "HLG", "LogC3"}
CALIBRATIONS = {CALIBRATION, "measured-profile"}
FORMATS = {VIRTUAL, "native-sensor"}
LOOKS = {PROCESSED, "camera-original"}
PHRASES = {
    "RAW-derived": (
        "RAW-derived source; provisional calibration does not make it cinema-camera equivalent"
    ),
    "HLG-derived": "HLG-derived source; not sensor-derived Log and not RAW-derived",
    "SDR-derived": "SDR-derived simulated look; not native large-format or sensor-derived Log",
}
MARKETING_FLAGS = (
    ("sensorEnlargement", "sensor-enlargement", "marketing must not imply sensor enlargement"),
    (
        "guaranteedArriEquivalence",
        "guaranteed-arri-equivalence",
        "marketing must not imply guaranteed ARRI equivalence",
    ),
    (
        "recoveredClippedDetail",
        "recovered-clipped-detail",
        "marketing must not imply recovered clipped detail",
    ),
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
CODEC_TOKEN = re.compile(r"^[A-Za-z0-9]+$")
PRESET_TEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]*$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "source",
    "export",
    "wording",
    "marketing",
    "evidence",
}
SOURCE_KEYS = {"acquisition", "origin", "transfer"}
EXPORT_KEYS = {"recipe", "presetName", "codec", "containerBitDepth", "visuallyFlat"}
WORDING_KEYS = {"surfaces", "category", "calibration", "formatKind", "look", "text"}
MARKETING_KEYS = {"sensorEnlargement", "guaranteedArriEquivalence", "recoveredClippedDetail"}
EVIDENCE_KEYS = {"machineReadable", "uiMatchesEvidence"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "simulated_look"}


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


def _choice(value: object, allowed: set[str], label: str) -> str:
    require(value in allowed, label + " is unsupported")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _flag(value: bool) -> str:
    return "true" if value else "false"


def central_phrase(category: str) -> str:
    """Return the centralized wording for one acquisition category."""
    require(category in PHRASES, "category is unsupported")
    return PHRASES[category]


def preset_only_claims(preset_name: str) -> list[str]:
    """Claims the mutant would publish from the film preset name alone.

    ``assess`` must reject these. It must not turn them into ``simulated_look``,
    ``qualified``, or ``allowed``, and it must not replace the acquisition.
    """
    claims = ["preset-only-label"]
    folded = preset_name.casefold()
    if "large" in folded and "format" in folded:
        claims.append("native-large-format")
    if "log" in folded:
        claims.append("sensor-derived-log")
    if len(claims) == 1:
        claims.append("preset-name-as-lineage")
    return claims


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P064 product-label fixture."""
    exact_keys(document, DOCUMENT_KEYS, "product label")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P064")
    require(document["mapId"] == MAP_ID, "mapId must be s23-product-label-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "product label needs the P064 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    source = exact_keys(document["source"], SOURCE_KEYS, "source")
    _choice(source["acquisition"], ACQUISITIONS, "acquisition")
    _token(source["origin"], "origin")
    _choice(source["transfer"], TRANSFERS, "transfer")

    export = exact_keys(document["export"], EXPORT_KEYS, "export")
    _token(export["recipe"], "recipe")
    preset = export["presetName"]
    require(
        isinstance(preset, str) and PRESET_TEXT.fullmatch(preset) is not None and preset == preset.strip(),
        "presetName must be a non-empty preset title",
    )
    codec = export["codec"]
    require(isinstance(codec, str) and CODEC_TOKEN.fullmatch(codec) is not None, "codec must be a token")
    depth = export["containerBitDepth"]
    require(type(depth) is int and depth in {8, 10}, "containerBitDepth must be 8 or 10")
    _bool(export["visuallyFlat"], "visuallyFlat")

    wording = exact_keys(document["wording"], WORDING_KEYS, "wording")
    surfaces = wording["surfaces"]
    require(type(surfaces) is list and surfaces, "surfaces must be a non-empty list")
    require(all(item in SURFACES for item in surfaces), "surfaces must be select, export, or share")
    require(len(surfaces) == len(set(surfaces)), "surfaces must be unique")
    _choice(wording["category"], ACQUISITIONS, "wording category")
    _choice(wording["calibration"], CALIBRATIONS, "calibration")
    _choice(wording["formatKind"], FORMATS, "formatKind")
    _choice(wording["look"], LOOKS, "look")
    text = wording["text"]
    require(isinstance(text, str) and text.strip() and text == text.strip(), "wording text must be non-empty")

    marketing = exact_keys(document["marketing"], MARKETING_KEYS, "marketing")
    for key, _claim, _reason in MARKETING_FLAGS:
        _bool(marketing[key], key)
    evidence = exact_keys(document["evidence"], EVIDENCE_KEYS, "evidence")
    _bool(evidence["machineReadable"], "machineReadable")
    _bool(evidence["uiMatchesEvidence"], "uiMatchesEvidence")


def mutant_export_label(document: dict) -> str:
    """Return the preset name the mutant would use as the whole export label."""
    validate_document(document)
    return document["export"]["presetName"]


def honest_export_label(document: dict) -> str:
    """Return the source-aware wording, which is not the film preset name."""
    validate_document(document)
    return document["wording"]["text"]


def _preserved(document: dict) -> list[str]:
    source = document["source"]
    export = document["export"]
    wording = document["wording"]
    marketing = document["marketing"]
    evidence = document["evidence"]
    return [
        f"acquisition:{source['acquisition']}",
        f"origin:{source['origin']}",
        f"transfer:{source['transfer']}",
        f"recipe:{export['recipe']}",
        f"preset:{export['presetName']}",
        f"codec:{export['codec']}",
        f"container-bits:{export['containerBitDepth']}",
        f"visually-flat:{_flag(export['visuallyFlat'])}",
        f"category:{wording['category']}",
        f"calibration:{wording['calibration']}",
        f"format:{wording['formatKind']}",
        f"look:{wording['look']}",
        "surfaces:" + ",".join(wording["surfaces"]),
        f"wording:{wording['text']}",
        f"marketing:sensor-enlargement:{_flag(marketing['sensorEnlargement'])}",
        f"marketing:arri-equivalence:{_flag(marketing['guaranteedArriEquivalence'])}",
        f"marketing:recovered-clipped-detail:{_flag(marketing['recoveredClippedDetail'])}",
        f"evidence:machine-readable:{_flag(evidence['machineReadable'])}",
        f"evidence:ui-matches:{_flag(evidence['uiMatchesEvidence'])}",
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P064 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for key, items in (
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        require(all(isinstance(item, str) and item for item in items), key + " must be strings")
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


def assess(document: dict, interpretation: str = HONEST) -> dict:
    """Identify an SDR simulated look, or reject preset-only labels.

    ``interpretation`` ``preset-only`` is the mutant. It is rejected even when
    the preset name sounds like large-format Log. The SDR acquisition, the
    recipe, the codec, and the preset name stay in ``preservedResults``. The
    decision is never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(interpretation in INTERPRETATIONS, "interpretation must be source-aware or preset-only")
    source = document["source"]
    export = document["export"]
    wording = document["wording"]
    marketing = document["marketing"]
    evidence = document["evidence"]
    preserved = _preserved(document)
    reasons = [
        ORACLE,
        "ten-bit codec does not upgrade the source acquisition category",
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        "provisional calibration is not a measured camera profile",
        "virtual format is not sensor enlargement",
    ]
    if export["visuallyFlat"] and export["containerBitDepth"] == 10:
        questions.append("flat ten-bit export does not establish sensor-derived Log")
    rejected: list[str] = []

    if not evidence["machineReadable"] or not evidence["uiMatchesEvidence"]:
        rejected.append("label-evidence-mismatch")
        reasons.append("UI labels must match machine-readable evidence")
    missing = [item for item in SURFACES if item not in wording["surfaces"]]
    if missing:
        rejected.append("missing-surface")
        reasons.append("wording missing from " + ",".join(missing))
    if wording["category"] != source["acquisition"]:
        rejected.append("category-mismatch")
        reasons.append(
            f"wording category {wording['category']} does not match acquisition {source['acquisition']}"
        )
    if wording["text"] != central_phrase(wording["category"]):
        rejected.append("wording-not-centralized")
        reasons.append("label text is not the centralized phrase for its category")
    for key, claim, reason in MARKETING_FLAGS:
        if marketing[key]:
            rejected.append(claim)
            reasons.append(reason)
    if wording["calibration"] != CALIBRATION:
        rejected.append("calibration-not-provisional")
        reasons.append("calibration wording is not provisional")
    if wording["formatKind"] != VIRTUAL:
        rejected.append("format-not-virtual")
        reasons.append("format wording claims a native sensor rather than a virtual format")
    if wording["look"] != PROCESSED:
        rejected.append("look-not-processed")
        reasons.append("look wording is not a processed look")

    if interpretation == MUTANT_MODE:
        rejected = preset_only_claims(export["presetName"]) + rejected
        reasons.append(MUTANT)
        reasons.append("export label was built only from preset " + export["presetName"])
        reasons.append("preset name is not source provenance")
        questions.append("mutant interpretation rejected")
        decision = "rejected"
    elif rejected:
        decision = "rejected"
    elif (
        source["acquisition"] == "SDR-derived"
        and source["origin"] == SDR_ORIGIN
        and source["transfer"] == "Rec.709"
        and export["recipe"] == LARGE_RECIPE
        and export["codec"] == CODEC
        and export["containerBitDepth"] == 10
        and wording["category"] == "SDR-derived"
        and wording["text"] == central_phrase("SDR-derived")
        and wording["calibration"] == CALIBRATION
        and wording["formatKind"] == VIRTUAL
        and wording["look"] == PROCESSED
        and not missing
    ):
        decision = "simulated_look"
        reasons.append("interface identifies a simulated look from an SDR source")
        reasons.append(central_phrase("SDR-derived"))
    else:
        decision = "withheld"
        reasons.append("source-aware wording recorded; not a qualification")
        questions.append("source-aware wording is not physical S23 qualification")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
