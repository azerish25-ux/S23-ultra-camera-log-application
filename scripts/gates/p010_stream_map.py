#!/usr/bin/env python3
"""P010 ordinary stream-map export and timing-aware mode candidates.

Every advertised format and size stays in the export. Timing strings are
constraints, not a measured cadence. One failed property query must not drop
the other streams. fixedCadence is "supported" only when fixedCadenceEvidence
is true; an AE range that merely includes a nominal rate stays "withheld".
An illegal simultaneous combination is rejected and the export is kept.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P010-01 through TC-P010-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


BASE_REVISION = "fffd5c9a63cb732e103052acae29ae0c251585cc"
MAP_ID = "s23-stream-map-fixture"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
FPS_TEXT = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
MAP_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "failedProperties",
    "streams",
}
STREAM_KEYS = {
    "logicalId",
    "format",
    "width",
    "height",
    "advertised",
    "minFps",
    "maxFps",
    "fixedCadenceEvidence",
    "aeRangeIncludesNominal",
    "queryError",
}
RESULT_KEYS = ("decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
DECISIONS = {"rejected", "candidate"}


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


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _fps(value: object, context: str) -> Decimal:
    require(isinstance(value, str) and FPS_TEXT.fullmatch(value) is not None,
            context + " must be a decimal string such as 30 or 29.97")
    parsed = Decimal(value)
    require(parsed > 0, context + " must be positive")
    return parsed


def _stream_identity(stream: dict) -> str:
    return f"{stream['width']}x{stream['height']}:{stream['format']}@{stream['logicalId']}"


def _fixed_cadence(stream: dict) -> str:
    """Certify fixed cadence only from explicit evidence.

    aeRangeIncludesNominal is recorded on the stream and is not consulted.
    A variable range that happens to contain the nominal rate stays withheld.
    """
    if stream["fixedCadenceEvidence"] is True:
        return "supported"
    return "withheld"


def validate_map(document: dict) -> None:
    """Raise ValueError unless document is a P010 ordinary stream map."""
    exact_keys(document, MAP_KEYS, "stream map")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == "P010", "phase must be P010")
    require(document["mapId"] == MAP_ID, "mapId must be s23-stream-map-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "stream map needs the P010 implementation base revision")
    failed = document["failedProperties"]
    require(isinstance(failed, list) and all(_text(item) for item in failed),
            "failedProperties must be a list of non-empty strings")
    require(len(failed) == len(set(failed)), "failedProperties must be unique")
    streams = document["streams"]
    require(isinstance(streams, list) and streams, "streams must be a non-empty list")
    seen: set[str] = set()
    for index, stream in enumerate(streams):
        exact_keys(stream, STREAM_KEYS, f"stream {index}")
        require(_text(stream["logicalId"]), f"stream {index} logicalId must be a non-empty string")
        require(_text(stream["format"]), f"stream {index} format must be a non-empty string")
        for axis in ("width", "height"):
            require(type(stream[axis]) is int and stream[axis] > 0,
                    f"stream {index} {axis} must be a positive int")
        require(type(stream["advertised"]) is bool, f"stream {index} advertised must be a bool")
        low = _fps(stream["minFps"], f"stream {index} minFps")
        high = _fps(stream["maxFps"], f"stream {index} maxFps")
        require(low <= high, f"stream {index} minFps must not exceed maxFps")
        require(type(stream["fixedCadenceEvidence"]) is bool,
                f"stream {index} fixedCadenceEvidence must be a bool")
        require(type(stream["aeRangeIncludesNominal"]) is bool,
                f"stream {index} aeRangeIncludesNominal must be a bool")
        query = stream["queryError"]
        require(query is None or _text(query),
                f"stream {index} queryError must be a non-empty string or null")
        identity = _stream_identity(stream)
        require(identity not in seen, "duplicate stream identity: " + identity)
        seen.add(identity)


def export_streams(document: dict) -> list[dict]:
    """Export every stream, including those with a queryError.

    A failed property on the map or on one stream does not remove the others.
    Frame-rate strings are copied unchanged. fixedCadence stays withheld unless
    fixedCadenceEvidence is true.
    """
    validate_map(document)
    exported: list[dict] = []
    for stream in document["streams"]:
        exported.append({
            "identity": _stream_identity(stream),
            "advertised": stream["advertised"],
            "queryError": stream["queryError"],
            "timing": {
                "minFps": stream["minFps"],
                "maxFps": stream["maxFps"],
                "fixedCadence": _fixed_cadence(stream),
            },
        })
    return exported


def _open_questions(document: dict, exported: list[dict]) -> list[str]:
    questions: list[str] = []
    for prop in document["failedProperties"]:
        questions.append(prop + " query failed; unrelated streams were retained")
    if any(item["queryError"] for item in exported):
        questions.append("stream query errors were retained in the export")
    if any(item["timing"]["fixedCadence"] == "withheld" for item in exported):
        questions.append("fixed cadence withheld; AE range inclusion is not fixed-rate evidence")
    return questions


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must not be qualified")
    require(decision != "qualified", "decision must not be qualified")
    require(bool(reasons), "reasons required")
    result = {
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_combination(document: dict, selected_identities: list[str],
                       constraints_violated: bool) -> dict:
    """Judge a simultaneous selection without discarding the export.

    constraints_violated yields decision "rejected". rejectedClaims are the
    selected identities. preservedResults are every exported identity. The
    decision is never "qualified". When constraints are intact and every
    selected identity exists, the decision is "candidate".
    """
    require(isinstance(selected_identities, list), "selected_identities must be a list")
    require(all(isinstance(item, str) and item for item in selected_identities),
            "selected_identities must be non-empty strings")
    require(type(constraints_violated) is bool, "constraints_violated must be a bool")
    exported = export_streams(document)
    preserved = [item["identity"] for item in exported]
    questions = _open_questions(document, exported)
    if constraints_violated:
        return _result(
            "rejected",
            [
                "declared camera constraints reject this simultaneous combination",
                "individual support does not prove the streams can be selected together",
            ],
            list(selected_identities),
            preserved,
            questions,
        )
    missing = [item for item in selected_identities if item not in preserved]
    require(not missing, "unknown stream identity: " + ", ".join(missing))
    return _result(
        "candidate",
        [
            "selected streams are present in the ordinary export",
            "candidate status does not certify fixed cadence or coexistence",
        ],
        [],
        preserved,
        questions,
    )
