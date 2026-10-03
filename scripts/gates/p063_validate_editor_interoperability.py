#!/usr/bin/env python3
"""P063 editor interoperability on a host fixture.

A LogC3 export is imported once at video levels and once with an incorrect
full-range assumption. The protocol records that tonal mismatch and the
supported workflow: video levels, explicit primaries, transfer, and sidecar.
A generic player opening the file is not interoperability.

The deliberate mutant — approve interoperability because a generic player
opens the file — is rejected. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P063-01 through TC-P063-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P063"
CASE_ID = "P063"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-editor-interoperability-fixture"
METHOD = (
    "Create reference exports with explicit import instructions, range, primaries, "
    "transfer, and sidecar. Round-trip through independently selected editors or "
    "decoders where available. Record application versions and any manual assignments; "
    "do not claim automatic recognition without testing it."
)
FIXTURE = (
    "A LogC3 export imported once at video levels and once with an incorrect "
    "full-range assumption."
)
ORACLE = (
    "The protocol detects the tonal mismatch and documents the correct supported workflow."
)
MUTANT = "Approve interoperability because a generic player opens the file."
HOST_LIMIT = "this host record does not qualify a physical S23 or editor interoperability"
HONEST = "detect-mismatch"
MUTANT_MODE = "player-opens"
INTERPRETATIONS = {HONEST, MUTANT_MODE}

ENCODINGS = {"LogC3", "HLG", "Rec.709"}
PRIMARIES = {"AWG3", "Rec.709", "Rec.2020"}
TRANSFERS = {"LogC3", "HLG", "Rec.709"}
RANGES = {"video", "full"}
CONTAINERS = {"Main10", "Main"}

HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "export",
    "videoImport",
    "fullRangeImport",
    "sidecar",
    "consumer",
    "workflow",
}
EXPORT_KEYS = {"encoding", "primaries", "transfer", "range", "container", "instructions"}
IMPORT_KEYS = {
    "id",
    "rangeAssumption",
    "application",
    "version",
    "manualAssignment",
    "automaticRecognitionTested",
}
SIDECAR_KEYS = {"present", "range", "primaries", "transfer", "encoding"}
CONSUMER_KEYS = {
    "name",
    "version",
    "opened",
    "thumbnailOnly",
    "automaticRecognitionClaimed",
}
WORKFLOW_KEYS = {"supportedRange", "documented", "statement"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "mismatch_recorded"}
_FORBIDDEN = {"qualified", "allowed", "interoperable"}
_STRUCTURAL = {
    "export-transfer-mismatch",
    "sidecar-contradiction",
    "workflow-range-mismatch",
    "workflow-not-documented",
    "untested-automatic-recognition",
}


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
    require(
        isinstance(value, str) and bool(value) and value == value.strip() and len(value) <= 400,
        label + " must be a non-empty string",
    )
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _choice(value: object, allowed: set[str], label: str) -> str:
    require(value in allowed, label + " is unsupported")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _import_record(kind: str, item: dict) -> str:
    return (
        f"import:{kind}:{item['id']}:{item['rangeAssumption']}:"
        f"{item['application']}:{item['version']}:"
        f"manual={_flag(item['manualAssignment'])}:"
        f"auto-tested={_flag(item['automaticRecognitionTested'])}"
    )


def opening_would_approve_interoperability(document: dict) -> bool:
    """True when a generic player opened the file.

    The mutant treats that fact as interoperability. ``assess`` must not turn
    it into ``interoperable``, ``qualified``, or ``allowed``.
    """
    validate_document(document)
    return document["consumer"]["opened"] is True


def tonal_mismatch(document: dict) -> bool:
    """True when video-level export is also imported with a full-range assumption."""
    validate_document(document)
    export = document["export"]
    video = document["videoImport"]
    full = document["fullRangeImport"]
    return bool(
        export["range"] == "video"
        and video["rangeAssumption"] == "video"
        and full["rangeAssumption"] == "full"
    )


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P063 editor-interoperability fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "editor interoperability")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P063")
    require(document["mapId"] == MAP_ID, "mapId must be s23-editor-interoperability-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "editor interoperability needs the P063 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    export = exact_keys(document["export"], EXPORT_KEYS, "export")
    _choice(export["encoding"], ENCODINGS, "export encoding")
    _choice(export["primaries"], PRIMARIES, "export primaries")
    _choice(export["transfer"], TRANSFERS, "export transfer")
    _choice(export["range"], RANGES, "export range")
    _choice(export["container"], CONTAINERS, "export container")
    _text(export["instructions"], "instructions")

    video = exact_keys(document["videoImport"], IMPORT_KEYS, "videoImport")
    full = exact_keys(document["fullRangeImport"], IMPORT_KEYS, "fullRangeImport")
    for label, item in (("videoImport", video), ("fullRangeImport", full)):
        _token(item["id"], label + " id")
        _choice(item["rangeAssumption"], RANGES, label + " range")
        _token(item["application"], label + " application")
        _token(item["version"], label + " version")
        _bool(item["manualAssignment"], label + " manualAssignment")
        _bool(item["automaticRecognitionTested"], label + " automaticRecognitionTested")
    require(video["id"] != full["id"], "video and full-range imports must have distinct ids")

    sidecar = exact_keys(document["sidecar"], SIDECAR_KEYS, "sidecar")
    _bool(sidecar["present"], "sidecar present")
    _choice(sidecar["range"], RANGES, "sidecar range")
    _choice(sidecar["primaries"], PRIMARIES, "sidecar primaries")
    _choice(sidecar["transfer"], TRANSFERS, "sidecar transfer")
    _choice(sidecar["encoding"], ENCODINGS, "sidecar encoding")

    consumer = exact_keys(document["consumer"], CONSUMER_KEYS, "consumer")
    _token(consumer["name"], "consumer name")
    _token(consumer["version"], "consumer version")
    _bool(consumer["opened"], "consumer opened")
    _bool(consumer["thumbnailOnly"], "consumer thumbnailOnly")
    _bool(consumer["automaticRecognitionClaimed"], "automaticRecognitionClaimed")

    workflow = exact_keys(document["workflow"], WORKFLOW_KEYS, "workflow")
    _choice(workflow["supportedRange"], RANGES, "workflow range")
    _bool(workflow["documented"], "workflow documented")
    _text(workflow["statement"], "workflow statement")


def _sidecar_matches(document: dict) -> bool:
    export = document["export"]
    sidecar = document["sidecar"]
    return bool(
        sidecar["present"]
        and sidecar["range"] == export["range"]
        and sidecar["primaries"] == export["primaries"]
        and sidecar["transfer"] == export["transfer"]
        and sidecar["encoding"] == export["encoding"]
    )


def _preserved(document: dict) -> list[str]:
    export = document["export"]
    sidecar = document["sidecar"]
    consumer = document["consumer"]
    workflow = document["workflow"]
    return [
        (
            f"export:{export['encoding']}:{export['primaries']}:{export['transfer']}:"
            f"{export['range']}:{export['container']}"
        ),
        "instructions:" + export["instructions"],
        _import_record("video", document["videoImport"]),
        _import_record("full", document["fullRangeImport"]),
        (
            f"sidecar:{_flag(sidecar['present'])}:{sidecar['range']}:{sidecar['primaries']}:"
            f"{sidecar['transfer']}:{sidecar['encoding']}"
        ),
        (
            f"consumer:{consumer['name']}:{consumer['version']}:"
            f"opened={_flag(consumer['opened'])}:thumbnail={_flag(consumer['thumbnailOnly'])}:"
            f"auto-claim={_flag(consumer['automaticRecognitionClaimed'])}"
        ),
        (
            f"workflow:{workflow['supportedRange']}:documented={_flag(workflow['documented'])}:"
            f"{workflow['statement']}"
        ),
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "P063 decision must be rejected, withheld, or mismatch_recorded")
    require(decision not in _FORBIDDEN, "P063 must not decide qualified, allowed, or interoperable")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    require(all(isinstance(item, str) and item for item in rejected), "rejectedClaims must be strings")
    require(all(isinstance(item, str) and item for item in preserved), "preservedResults must be strings")
    require(all(isinstance(item, str) and item for item in questions), "openQuestions must be strings")
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
    """Record a video-versus-full tonal mismatch, or reject the player-open mutant.

    interpretation ``player-opens`` is the mutant. It is rejected even when a
    generic player opened the file. Both import attempts, the sidecar, and the
    consumer version stay in preservedResults. The decision is never
    ``qualified``, ``allowed``, or ``interoperable``.
    """
    validate_document(document)
    require(interpretation in INTERPRETATIONS, "interpretation must be detect-mismatch or player-opens")
    export = document["export"]
    video = document["videoImport"]
    full = document["fullRangeImport"]
    sidecar = document["sidecar"]
    consumer = document["consumer"]
    workflow = document["workflow"]
    preserved = _preserved(document)
    reasons = [
        ORACLE,
        "thumbnail appearance is not consumer interpretation",
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        "application versions and manual assignments stay in the report",
    ]
    rejected: list[str] = []

    if export["encoding"] == "LogC3" and export["transfer"] != "LogC3":
        rejected.append("export-transfer-mismatch")
        reasons.append("LogC3 export transfer does not match the encoding")
    mismatch = tonal_mismatch(document)
    if mismatch:
        rejected.append("incorrect-full-range")
        reasons.append(
            "full-range import "
            + full["id"]
            + " disagrees with video-level export "
            + export["range"]
        )
    else:
        reasons.append(
            "video import "
            + video["rangeAssumption"]
            + " and full-range import "
            + full["rangeAssumption"]
            + " do not show the fixture tonal mismatch"
        )

    sidecar_ok = _sidecar_matches(document)
    if sidecar["present"] and not sidecar_ok:
        rejected.append("sidecar-contradiction")
        reasons.append("sidecar range, primaries, transfer, or encoding disagrees with the export")
    elif not sidecar["present"]:
        reasons.append("explicit sidecar is absent")
    else:
        reasons.append("sidecar restates the export range, primaries, and transfer")

    if workflow["documented"] and workflow["supportedRange"] != export["range"]:
        rejected.append("workflow-range-mismatch")
        reasons.append(
            "documented workflow range "
            + workflow["supportedRange"]
            + " disagrees with export range "
            + export["range"]
        )
    workflow_ok = bool(
        workflow["documented"]
        and workflow["supportedRange"] == export["range"]
        and sidecar_ok
    )
    if not workflow_ok:
        rejected.append("workflow-not-documented")
        reasons.append("correct supported workflow is not documented")
        questions.append("import guidance must name range, primaries, transfer, and sidecar")
    else:
        reasons.append(workflow["statement"])

    tested = video["automaticRecognitionTested"] or full["automaticRecognitionTested"]
    if consumer["automaticRecognitionClaimed"] and not tested:
        rejected.append("untested-automatic-recognition")
        reasons.append("automatic recognition was claimed without a recorded test")
    elif consumer["automaticRecognitionClaimed"]:
        reasons.append("automatic recognition was tested and is still not qualification")
    else:
        reasons.append("automatic recognition was not claimed")
    if consumer["thumbnailOnly"]:
        reasons.append("consumer evidence is thumbnail-only and was not used as the oracle")
        questions.append("a generic player thumbnail does not certify color interpretation")

    if interpretation == MUTANT_MODE:
        rejected.insert(0, "generic-player-open")
        reasons.append(MUTANT)
        reasons.append("opening the file is not interoperability")
        questions.append("mutant interpretation rejected")
        decision = "rejected"
    elif any(item in rejected for item in _STRUCTURAL):
        decision = "rejected"
    elif mismatch and workflow_ok:
        decision = "mismatch_recorded"
        questions.append("tonal mismatch recorded; incorrect full-range import kept")
    else:
        decision = "withheld"
        reasons.append("interoperability is withheld without the tonal-mismatch protocol")
        questions.append("file opening is not interoperability")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
