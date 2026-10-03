#!/usr/bin/env python3
"""P038 capture-time calibration snapshots.

Snapshots bind available matrices, illuminants, neutral points, levels, crop,
and lens-shading data to firmware and route. Missing fields stay explicit.
The deliberate mutant — reading current camera metadata while developing an
older source and treating it as capture-time truth — is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P038-01 through TC-P038-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P038"
CASE_ID = "P038"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-capture-calibration-snapshot-fixture"
METHOD = (
    "Capture available calibration and forward matrices, reference illuminants, "
    "neutral points, black and white levels, crop descriptions, and lens shading "
    "data with explicit missing fields. Bind snapshots to firmware and route. "
    "Document the coordinate and matrix conventions."
)
FIXTURE = (
    "Two takes on different firmware versions with different forward matrices "
    "but the same physical handset."
)
ORACLE = (
    "The developer selects the matching snapshot and rejects a profile whose "
    "source identity does not match."
)
MUTANT = (
    "Look up current camera metadata while developing an older source and "
    "treat it as capture-time truth."
)
COORDINATES = (
    "Sensor active-array coordinates: origin at the top-left, x increases to the "
    "right, y increases downward, integer pixels. Crop is widthxheight+left+top. "
    "Bayer phase is relative to the crop origin and must be RGGB, GRBG, GBRG, or "
    "BGGR. Odd crop origins are not a declared layout."
)
MATRICES = (
    "Row-major 3x3 canonical decimal strings. The forward matrix maps "
    "white-balanced camera RGB to CIE XYZ D50. The calibration matrix maps device "
    "RGB to that reference camera RGB. A snapshot is not a measured profile. "
    "Missing fields stay listed and are not filled from current device metadata "
    "or an identity matrix."
)

CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
ILLUMINANTS = ("D65", "D50", "A", "D55", "D75")
OPTIONAL_FIELDS = ("forwardMatrix", "calibrationMatrix", "lensShading")
IDENTITY_FIELDS = ("firmware", "route", "cfa", "crop", "handsetId")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(
    r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]"
)
UINT = re.compile(r"0|[1-9][0-9]*")
CROP = re.compile(r"[1-9][0-9]*x[1-9][0-9]*\+(?:0|[1-9][0-9]*)\+(?:0|[1-9][0-9]*)")
MUTANT_POLICY = "current_metadata_as_capture_truth"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "conventions",
    "handset",
    "sources",
    "snapshots",
    "currentMetadata",
}
CONVENTION_KEYS = {"coordinates", "matrices"}
HANDSET_KEYS = {"id", "model"}
SOURCE_KEYS = {
    "id",
    "handsetId",
    "firmware",
    "route",
    "cfa",
    "crop",
    "boundSnapshotId",
}
SNAPSHOT_KEYS = {
    "id",
    "sourceId",
    "handsetId",
    "firmware",
    "route",
    "cfa",
    "crop",
    "forwardMatrix",
    "calibrationMatrix",
    "referenceIlluminants",
    "neutralPoint",
    "blackLevel",
    "whiteLevel",
    "lensShading",
    "missingFields",
}
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
    require(
        isinstance(value, str) and bool(value) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def _uint(value: object, label: str) -> str:
    require(
        isinstance(value, str) and UINT.fullmatch(value) is not None,
        label + " must be a canonical non-negative integer string",
    )
    return value


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    return value


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
    require(decision not in _FORBIDDEN, "P038 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
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


def _matrix(value: object, label: str) -> list[str]:
    require(type(value) is list and len(value) == 9, label + " must be nine coefficients")
    return [_decimal(item, label + " coefficient") for item in value]


def _optional_matrix(value: object, label: str, missing: bool) -> list[str] | None:
    if missing:
        require(value is None, label + " must be null when listed missing")
        return None
    return _matrix(value, label)


def _lens(value: object, missing: bool) -> list[str] | None:
    if missing:
        require(value is None, "lensShading must be null when listed missing")
        return None
    require(type(value) is list and 1 <= len(value) <= 256, "lensShading must be a bounded grid")
    return [_decimal(item, "lensShading sample") for item in value]


def _identity_block(item: dict, label: str) -> None:
    _text(item["firmware"], label + " firmware")
    _text(item["route"], label + " route")
    cfa = _text(item["cfa"], label + " cfa")
    require(cfa in CFA, label + " cfa must be a supported Bayer phase")
    crop = _text(item["crop"], label + " crop")
    require(CROP.fullmatch(crop) is not None, label + " crop must be widthxheight+left+top")
    _text(item["handsetId"], label + " handsetId")


def _missing_fields(value: object, label: str) -> list[str]:
    require(type(value) is list, label + " missingFields must be a list")
    require(len(value) == len(set(value)), label + " missingFields must be unique")
    for item in value:
        require(item in OPTIONAL_FIELDS, label + " unknown missing field")
    return list(value)


def _snapshot(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SNAPSHOT_KEYS, f"snapshot {index}")
    ident = _text(item["id"], f"snapshot {index} id")
    require(ident not in seen, "duplicate snapshot id: " + ident)
    seen.add(ident)
    _text(item["sourceId"], f"snapshot {index} sourceId")
    _identity_block(item, f"snapshot {index}")
    missing = _missing_fields(item["missingFields"], f"snapshot {index}")
    _optional_matrix(item["forwardMatrix"], f"snapshot {index} forwardMatrix", "forwardMatrix" in missing)
    _optional_matrix(
        item["calibrationMatrix"],
        f"snapshot {index} calibrationMatrix",
        "calibrationMatrix" in missing,
    )
    _lens(item["lensShading"], "lensShading" in missing)
    illuminants = item["referenceIlluminants"]
    require(type(illuminants) is list and illuminants, f"snapshot {index} needs reference illuminants")
    require(len(illuminants) == len(set(illuminants)), f"snapshot {index} illuminants must be unique")
    for name in illuminants:
        require(name in ILLUMINANTS, f"snapshot {index} unknown illuminant")
    neutral = item["neutralPoint"]
    require(type(neutral) is list and len(neutral) == 3, f"snapshot {index} neutralPoint must have three components")
    for component in neutral:
        _decimal(component, f"snapshot {index} neutralPoint")
    black = _uint(item["blackLevel"], f"snapshot {index} blackLevel")
    white = _uint(item["whiteLevel"], f"snapshot {index} whiteLevel")
    require(int(white) > int(black), f"snapshot {index} whiteLevel must exceed blackLevel")
    return item


def _source(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SOURCE_KEYS, f"source {index}")
    ident = _text(item["id"], f"source {index} id")
    require(ident not in seen, "duplicate source id: " + ident)
    seen.add(ident)
    _identity_block(item, f"source {index}")
    _text(item["boundSnapshotId"], f"source {index} boundSnapshotId")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P038 snapshot schema."""
    exact_keys(document, DOCUMENT_KEYS, "calibration document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P038")
    require(document["mapId"] == MAP_ID, "mapId must be s23-capture-calibration-snapshot-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "calibration document needs the P038 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    conventions = exact_keys(document["conventions"], CONVENTION_KEYS, "conventions")
    require(conventions["coordinates"] == COORDINATES, "coordinate convention drifted")
    require(conventions["matrices"] == MATRICES, "matrix convention drifted")
    handset = exact_keys(document["handset"], HANDSET_KEYS, "handset")
    _text(handset["id"], "handset id")
    _text(handset["model"], "handset model")
    sources = document["sources"]
    require(type(sources) is list and sources, "sources must be a non-empty list")
    seen_sources: set[str] = set()
    for index, item in enumerate(sources):
        _source(item, index, seen_sources)
    snapshots = document["snapshots"]
    require(type(snapshots) is list and snapshots, "snapshots must be a non-empty list")
    seen_snaps: set[str] = set()
    for index, item in enumerate(snapshots):
        _snapshot(item, index, seen_snaps)
    current = _snapshot(document["currentMetadata"], 0, set())
    require(current["id"] == "current-device", "currentMetadata id must be current-device")
    require(current["sourceId"] == "live", "currentMetadata sourceId must be live")
    require(current["id"] not in seen_snaps, "current metadata must not reuse a snapshot id")
    by_id = {item["id"]: item for item in snapshots}
    for source in sources:
        require(source["boundSnapshotId"] in by_id, "source bound snapshot is missing")
        require(source["handsetId"] == handset["id"], "source handset must match the fixture handset")


def source_token(source: dict) -> str:
    return (
        f"{source['id']}@{source['handsetId']}:{source['firmware']}:"
        f"{source['route']}:{source['cfa']}:{source['crop']}"
    )


def matrix_token(snapshot: dict) -> str:
    matrix = snapshot["forwardMatrix"]
    if matrix is None:
        body = "missing"
    else:
        body = ",".join(matrix)
    return f"{snapshot['id']}:forward:{body}"


def _find_source(document: dict, source_id: str) -> dict:
    matches = [item for item in document["sources"] if item["id"] == source_id]
    require(len(matches) == 1, "unknown source id")
    return matches[0]


def _bound_snapshot(document: dict, source: dict) -> dict:
    matches = [item for item in document["snapshots"] if item["id"] == source["boundSnapshotId"]]
    require(len(matches) == 1, "bound snapshot missing")
    return matches[0]


def _deltas(source: dict, profile: dict) -> list[str]:
    return [field for field in IDENTITY_FIELDS if source[field] != profile[field]]


def _questions_for(document: dict) -> list[str]:
    questions = [
        "snapshot is not a measured colour profile",
        "physical S23 calibration unverified",
    ]
    for snapshot in document["snapshots"]:
        for field in snapshot["missingFields"]:
            questions.append(f"missing {snapshot['id']} {field}")
    return questions


def _preserved(document: dict) -> list[str]:
    preserved = [source_token(item) for item in document["sources"]]
    for snapshot in document["snapshots"]:
        preserved.append(matrix_token(snapshot))
        for field in snapshot["missingFields"]:
            preserved.append(f"missing:{snapshot['id']}:{field}")
    preserved.append("live:" + matrix_token(document["currentMetadata"]) + ":not-capture-truth")
    return preserved


def selected_forward(document: dict, source_id: str) -> list[str]:
    """Return the capture-time forward matrix. Never the live device lookup."""
    validate_document(document)
    source = _find_source(document, source_id)
    snapshot = _bound_snapshot(document, source)
    require(not _deltas(source, snapshot), "bound snapshot identity does not match the source")
    require(snapshot["sourceId"] == source["id"], "snapshot is not bound to this source")
    matrix = snapshot["forwardMatrix"]
    require(matrix is not None, "capture-time forward matrix is missing")
    return list(matrix)


def apply_current_as_truth(document: dict, source_id: str) -> dict:
    """Reject the mutant that treats live metadata as the older capture snapshot.

    The capture-time matrix stays in preservedResults under the ``capture:``
    prefix. A live lookup may be inventoried, but it is not the selected matrix.
    """
    validate_document(document)
    source = _find_source(document, source_id)
    snapshot = _bound_snapshot(document, source)
    current = document["currentMetadata"]
    capture = "capture:" + matrix_token(snapshot)
    preserved = [
        source_token(source),
        capture,
        "live:" + matrix_token(current) + ":not-capture-truth",
        f"provenance:{source['id']}",
    ]
    return _result(
        "rejected",
        [
            MUTANT,
            ORACLE,
            "current camera metadata is not capture-time truth",
            "the capture-time forward matrix was not replaced",
        ],
        ["current-metadata-as-capture-truth"],
        preserved,
        ["physical S23 calibration unverified"],
    )


def assess(document: dict) -> dict:
    """Select each source's bound snapshot and refuse live metadata substitution.

    Decision is ``selected`` only when every source matches its capture-time
    snapshot. It is never ``qualified`` or ``allowed``. Missing fields and the
    live lookup stay in the inventory.
    """
    validate_document(document)
    preserved = _preserved(document)
    questions = _questions_for(document)
    rejected: list[str] = []
    handsets = {item["handsetId"] for item in document["sources"]}
    if len(handsets) != 1:
        rejected.append("handset-not-shared")
    firmwares = [item["firmware"] for item in document["sources"]]
    matrices: list[tuple[str, ...]] = []
    for source in document["sources"]:
        snapshot = _bound_snapshot(document, source)
        if snapshot["sourceId"] != source["id"]:
            rejected.append("binding-mismatch:" + source["id"])
        for field in _deltas(source, snapshot):
            rejected.append(f"{field}-mismatch:{source['id']}")
        matrix = snapshot["forwardMatrix"]
        if matrix is None:
            rejected.append("missing-forward:" + source["id"])
        else:
            matrices.append(tuple(matrix))
        if snapshot["id"] == document["currentMetadata"]["id"]:
            rejected.append("current-metadata-as-capture-truth")
    if len(firmwares) >= 2 and len(set(firmwares)) >= 2 and len(set(matrices)) < 2 and matrices:
        questions.append("forward matrices are not distinct across firmware")
    if rejected:
        decision = "rejected"
        reasons = [ORACLE, "source identity did not match the bound snapshot"]
    elif len(document["sources"]) >= 2 and len(set(firmwares)) >= 2 and len(set(matrices)) >= 2:
        decision = "selected"
        reasons = [
            ORACLE,
            "matching capture-time snapshot selected",
            "current device metadata was not treated as capture-time truth",
            "forward matrices differ across firmware versions on the same handset",
            "explicit missing fields were not backfilled",
        ]
    else:
        decision = "withheld"
        reasons = [ORACLE, "snapshot selection is incomplete for this host fixture"]
        questions.append("capture-time selection withheld")
    if any(item["forwardMatrix"] is None for item in document["snapshots"]):
        reasons.append("a missing forward matrix was not replaced from current metadata")
    return _result(decision, reasons, rejected, preserved, questions)
