#!/usr/bin/env python3
"""P055 declared working-space conversion.

Apply a validated camera transform and exposure scale into a high-precision
working representation. Negative channels and highlights above diffuse white
stay intact until the documented storage boundary. An independent reference
vector must agree. Singular and nonfinite transforms are rejected.

The deliberate mutant — an eight-bit display bitmap between the camera
transform and the working image — is rejected. Display-gamut clipping is not
the working image. This module does not probe a device, does not qualify a
physical S23, and does not execute TC-P055-01 through TC-P055-08.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


PHASE = "P055"
CASE_ID = "P055"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-declared-working-space-fixture"
METHOD = (
    "Apply the validated camera transform and exposure scale into the chosen "
    "high-precision working representation. Keep negative and above-one channels "
    "until a documented boundary. Use independent reference vectors and reject "
    "singular or nonfinite transforms."
)
FIXTURE = (
    "A saturated source vector that produces a negative working-space channel "
    "and a highlight above diffuse white."
)
ORACLE = (
    "The conversion preserves both values for subsequent processing instead of "
    "forcing display-gamut clipping."
)
MUTANT = (
    "Insert an eight-bit display bitmap between the camera transform and working image."
)
DECLARED_PATH = "declared"
MUTANT_PATH = "eight-bit-display"
PATHS = (DECLARED_PATH, MUTANT_PATH)
SPACE_NAME = "scene-linear-float"
PRECISION = "float64"
WHITE_POINT = "D65"
UNITS = "scene-linear"
ORDER = ("camera-transform", "exposure-scale", "working-store")
BOUNDARY = "documented-storage"
CHANNELS = ("R", "G", "B")
EIGHT_BIT = Decimal(255)
HOST_LIMIT = (
    "host fixture does not qualify a physical S23 or a measured working-space conversion"
)
NONFINITE = {"NaN", "Infinity", "-Infinity", "+Infinity", "inf", "-inf", "+inf"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "workingSpace",
    "cameraTransform",
    "exposureScale",
    "source",
    "independentReference",
}
SPACE_KEYS = {
    "name",
    "precision",
    "whitePoint",
    "units",
    "order",
    "boundary",
    "diffuseWhite",
    "storageFloor",
    "storageCeiling",
}
SOURCE_KEYS = {"id", "cameraRgb"}
REFERENCE_KEYS = {"id", "workingRgb"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "working_retained", "bounded"}


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


def canonical(value: Decimal) -> str:
    """Render a Decimal without exponent notation or trailing zeros."""
    if not value.is_finite():
        raise ValueError("nonfinite decimal")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal(value: object, label: str, signed: bool = False) -> str:
    pattern = SIGNED if signed else DECIMAL
    require(
        isinstance(value, str) and pattern.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    require(value != "-0", label + " must not be negative zero")
    return value


def _number(value: object, label: str, signed: bool = True) -> str:
    if isinstance(value, str) and value in NONFINITE:
        return value
    return _decimal(value, label, signed=signed)


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _rgb(value: object, label: str, signed: bool) -> list[str]:
    require(type(value) is list and len(value) == 3, label + " must be three components")
    return [_number(item, label + " component", signed=signed) for item in value]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P055 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for key, items in (("rejectedClaims", rejected), ("preservedResults", preserved), ("openQuestions", questions)):
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


def determinant(matrix: list[str]) -> Decimal:
    """Determinant of a row-major 3x3 of finite canonical decimals."""
    m = [Decimal(item) for item in matrix]
    a, b, c, d, e, f, g, h, i = m
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def convert_working(matrix: list[str], camera_rgb: list[str], scale: str) -> tuple[Decimal, Decimal, Decimal]:
    """Apply camera transform then exposure scale. No display clamp."""
    m = [Decimal(item) for item in matrix]
    x, y, z = (Decimal(item) for item in camera_rgb)
    factor = Decimal(scale)
    return (
        factor * (m[0] * x + m[1] * y + m[2] * z),
        factor * (m[3] * x + m[4] * y + m[5] * z),
        factor * (m[6] * x + m[7] * y + m[8] * z),
    )


def display_bitmap(working: tuple[Decimal, Decimal, Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    """Eight-bit display encoding: clamp to [0, 1] then quantize to 1/255.

    This is the mutant intermediate. It is not a working-space store.
    """
    coded: list[Decimal] = []
    for channel in working:
        clamped = min(Decimal(1), max(Decimal(0), channel))
        code = (clamped * EIGHT_BIT).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        coded.append(code / EIGHT_BIT)
    return coded[0], coded[1], coded[2]


def _join(values: list[str] | tuple[str, ...]) -> str:
    return ",".join(values)


def _working_text(values: tuple[Decimal, Decimal, Decimal]) -> str:
    return ",".join(canonical(item) for item in values)


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P055 working-space fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "working space")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P055")
    require(document["mapId"] == MAP_ID, "mapId must be s23-declared-working-space-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "working space needs the P055 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    space = exact_keys(document["workingSpace"], SPACE_KEYS, "workingSpace")
    require(space["name"] == SPACE_NAME, "working space name drifted")
    require(space["precision"] == PRECISION, "precision must be float64")
    require(space["whitePoint"] == WHITE_POINT, "white point must be D65")
    require(space["units"] == UNITS, "units must be scene-linear")
    require(type(space["order"]) is list and tuple(space["order"]) == ORDER, "transform order drifted")
    require(space["boundary"] == BOUNDARY, "boundary must be documented-storage")
    diffuse = _decimal(space["diffuseWhite"], "diffuseWhite")
    floor = _decimal(space["storageFloor"], "storageFloor", signed=True)
    ceiling = _decimal(space["storageCeiling"], "storageCeiling", signed=True)
    require(Decimal(floor) < 0 < Decimal(diffuse) < Decimal(ceiling), "storage boundary must bracket diffuse white")
    matrix = document["cameraTransform"]
    require(type(matrix) is list and len(matrix) == 9, "cameraTransform must be nine coefficients")
    for index, item in enumerate(matrix):
        _number(item, f"cameraTransform[{index}]", signed=True)
    _number(document["exposureScale"], "exposureScale", signed=False)
    if document["exposureScale"] not in NONFINITE:
        require(Decimal(document["exposureScale"]) > 0, "exposureScale must be positive")
    source = exact_keys(document["source"], SOURCE_KEYS, "source")
    _token(source["id"], "source id")
    _rgb(source["cameraRgb"], "cameraRgb", signed=True)
    reference = exact_keys(document["independentReference"], REFERENCE_KEYS, "independentReference")
    _token(reference["id"], "reference id")
    require(reference["id"] != source["id"], "reference id must differ from the source id")
    _rgb(reference["workingRgb"], "workingRgb", signed=True)


def _nonfinite_sites(document: dict) -> list[str]:
    sites: list[str] = []
    for index, item in enumerate(document["cameraTransform"]):
        if item in NONFINITE:
            sites.append(f"matrix[{index}]")
    if document["exposureScale"] in NONFINITE:
        sites.append("exposure-scale")
    for index, item in enumerate(document["source"]["cameraRgb"]):
        if item in NONFINITE:
            sites.append(f"source[{index}]")
    for index, item in enumerate(document["independentReference"]["workingRgb"]):
        if item in NONFINITE:
            sites.append(f"reference[{index}]")
    return sites


def _questions(document: dict) -> list[str]:
    space = document["workingSpace"]
    return [
        "host fixture is not a physical S23 measurement",
        f"white point {space['whitePoint']} is a declared assumption, not a measurement",
        "units are " + space["units"],
        "order is " + " then ".join(space["order"]),
        f"boundary {space['boundary']} is {space['storageFloor']}..{space['storageCeiling']}",
    ]


def _preserved(
    document: dict,
    working: str,
    negative: str,
    highlight: str,
    display: str,
    stored: str,
) -> list[str]:
    space = document["workingSpace"]
    source = document["source"]
    reference = document["independentReference"]
    return [
        f"source:{source['id']}:{_join(source['cameraRgb'])}",
        f"working:{working}",
        f"stored:{stored}",
        f"negative:{negative}",
        f"highlight:{highlight}",
        f"white-point:{space['whitePoint']}",
        f"units:{space['units']}",
        f"precision:{space['precision']}",
        "order:" + ">".join(space["order"]),
        f"scale:{document['exposureScale']}",
        f"boundary:{space['storageFloor']}..{space['storageCeiling']}",
        f"diffuse-white:{space['diffuseWhite']}",
        f"reference:{reference['id']}:{_join(reference['workingRgb'])}",
        "matrix:" + _join(document["cameraTransform"]),
        f"display:{display}",
    ]


def _extremes(working: tuple[Decimal, Decimal, Decimal], diffuse: Decimal) -> tuple[str, str]:
    negatives = [f"{name}:{canonical(value)}" for name, value in zip(CHANNELS, working) if value < 0]
    highlights = [
        f"{name}:{canonical(value)}" for name, value in zip(CHANNELS, working) if value > diffuse
    ]
    negative = ",".join(negatives) if negatives else "none"
    highlight = ",".join(highlights) if highlights else "none"
    return negative, highlight


def _store(
    working: tuple[Decimal, Decimal, Decimal], floor: Decimal, ceiling: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    return tuple(min(ceiling, max(floor, channel)) for channel in working)


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Preserve signed and over-range working values, or reject the mutant.

    ``path`` ``eight-bit-display`` inserts the mutant bitmap. That decision is
    ``rejected`` even when the bitmap is visually closer to a display. The
    unclipped working vector stays in ``preservedResults``. The decision is
    never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be declared or eight-bit-display")
    questions = _questions(document)
    reasons = [ORACLE, "precision " + document["workingSpace"]["precision"]]
    sites = _nonfinite_sites(document)
    if sites:
        reasons.append("nonfinite transform rejected at " + ", ".join(sites))
        reasons.append(HOST_LIMIT)
        rejected = ["nonfinite-transform"]
        if path == MUTANT_PATH:
            rejected.append("eight-bit-display-bitmap")
            reasons.append(MUTANT)
        preserved = _preserved(document, "unavailable", "none", "none", "not-applied", "unavailable")
        return _result("rejected", reasons, rejected, preserved, questions)

    matrix = document["cameraTransform"]
    det = determinant(matrix)
    source = document["source"]["cameraRgb"]
    if det == 0:
        reasons.append("singular camera transform was rejected")
        reasons.append(HOST_LIMIT)
        rejected = ["singular-transform"]
        if path == MUTANT_PATH:
            rejected.append("eight-bit-display-bitmap")
            reasons.append(MUTANT)
        preserved = _preserved(document, "unavailable", "none", "none", "not-applied", "unavailable")
        return _result("rejected", reasons, rejected, preserved, questions)

    working = convert_working(matrix, source, document["exposureScale"])
    space = document["workingSpace"]
    diffuse = Decimal(space["diffuseWhite"])
    floor = Decimal(space["storageFloor"])
    ceiling = Decimal(space["storageCeiling"])
    negative, highlight = _extremes(working, diffuse)
    stored = _store(working, floor, ceiling)
    stated = document["independentReference"]["workingRgb"]
    computed = [canonical(item) for item in working]
    agrees = computed == stated
    outside = stored != working
    mutant = path == MUTANT_PATH
    display_text = "not-applied"
    rejected: list[str] = []
    reasons.append(f"working vector {_working_text(working)} before any boundary")
    if not agrees:
        rejected.append("reference-disagreement")
        reasons.append(
            "independent reference "
            + _join(stated)
            + " disagrees with computed "
            + _join(computed)
        )
    else:
        reasons.append("independent reference agrees with the computed working vector")
    if mutant:
        bitmap = display_bitmap(working)
        display_text = _working_text(bitmap)
        rejected.insert(0, "eight-bit-display-bitmap")
        reasons.append(MUTANT)
        reasons.append(f"eight-bit display bitmap produced {display_text}")
        if bitmap != working:
            rejected.append("display-gamut-clip")
            reasons.append("display-gamut clipping destroyed working-space channels")
        questions.append("eight-bit display bitmap was rejected and was not stored")
    if outside:
        reasons.append(
            f"documented storage boundary produced {_working_text(stored)} from {_working_text(working)}"
        )
    if negative == "none" or highlight == "none":
        reasons.append("saturated fixture pair (negative channel and highlight above white) is absent")
        questions.append("working vector did not contain both a negative and an above-white channel")
    else:
        reasons.append(f"negative channel {negative} kept")
        reasons.append(f"highlight {highlight} is above diffuse white {space['diffuseWhite']}")
    reasons.append(HOST_LIMIT)
    preserved = _preserved(
        document,
        _working_text(working),
        negative,
        highlight,
        display_text,
        _working_text(stored),
    )
    if mutant or (not agrees):
        decision = "rejected"
    elif negative == "none" or highlight == "none":
        decision = "withheld"
    elif outside:
        decision = "bounded"
        questions.append("storage boundary applied; display gamut was not the limit")
    else:
        decision = "working_retained"
        reasons.append("negative and above-white channels remain available for later processing")
    return _result(decision, reasons, rejected, preserved, questions)
