#!/usr/bin/env python3
"""P043 flat-field acquisition protocol and shading-map validator.

Diffuse uniform illumination is required before a lens-shading map may be
treated as spatial gain. A directional lighting ramp is not absorbed into
that map. Crop, CFA, and orientation must match the capture; a map applied
in display coordinates after rotation is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P043-01 through TC-P043-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P043"
CASE_ID = "P043"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-flat-field-shading-fixture"
METHOD = (
    "Capture diffuse uniform fields, reject gradients caused by the light source, "
    "align calibration to the actual crop and CFA, and bound correction gains. "
    "Record lens, focus, aperture metadata where applicable, exposure, and firmware. "
    "Validate on a separate flat capture."
)
FIXTURE = (
    "A flat field with a deliberate illumination gradient and a mismatched crop origin."
)
ORACLE = (
    "The pipeline does not absorb the lighting gradient into a supposedly universal "
    "lens-shading correction and detects coordinate mismatch."
)
MUTANT = "Apply a shading map in display coordinates after rotation."
SENSOR_APPLICATION = "sensor-crop"
MUTANT_APPLICATION = "display-after-rotation"
APPLICATIONS = (SENSOR_APPLICATION, MUTANT_APPLICATION)
HOST_LIMIT = "a host estimate does not qualify a physical S23"
CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
FRAMES = ("sensor-crop", "display")
ORIENTATIONS = ("native", "rotated")
FIELD_KINDS = ("uniform", "illumination-gradient", "lens-symmetric", "unstructured")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
UINT = re.compile(r"0|[1-9][0-9]*")
POSITIVE = re.compile(r"[1-9][0-9]*")
CROP = re.compile(r"([1-9][0-9]*)x([1-9][0-9]*)\+(0|[1-9][0-9]*)\+(0|[1-9][0-9]*)")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "protocol",
    "gainBounds",
    "session",
    "capture",
    "field",
    "shadingMap",
    "validation",
}
PROTOCOL_KEYS = {"illumination", "coordinateFrame", "validation"}
PROTOCOL = {
    "illumination": "diffuse-uniform",
    "coordinateFrame": "sensor-crop",
    "validation": "separate-flat",
}
GAIN_KEYS = {"min", "max"}
SESSION_KEYS = {"lens", "focus", "aperture", "exposureNs", "firmware"}
CAPTURE_KEYS = {"cfa", "sourceWidth", "sourceHeight", "crop"}
FIELD_KEYS = {"kind", "samples"}
MAP_KEYS = {"frame", "orientation", "crop", "cfa", "gains", "appliedAfterRotation"}
VALIDATION_KEYS = {"id", "separate", "samples"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "shading_rejected", "host_consistent"}
_FORBIDDEN = {"qualified", "allowed"}
_MIN_SAMPLES = 4
_MAX_SAMPLES = 8


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


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    return value


def _positive(value: object, label: str) -> str:
    require(
        isinstance(value, str) and POSITIVE.fullmatch(value) is not None,
        label + " must be a canonical positive integer string",
    )
    return value


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


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN, "P043 must not decide qualified or allowed")
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


def _samples(value: object, label: str) -> list[str]:
    require(type(value) is list, label + " must be a list")
    require(_MIN_SAMPLES <= len(value) <= _MAX_SAMPLES, label + " length must be 4..8")
    return [_decimal(item, label + " sample") for item in value]


def _crop(value: object, label: str) -> tuple[str, tuple[int, int, int, int]]:
    text = _text(value, label)
    match = CROP.fullmatch(text)
    require(match is not None, label + " must be widthxheight+left+top")
    width, height, left, top = (int(part) for part in match.groups())
    return text, (width, height, left, top)


def _class(values: list[Decimal]) -> str:
    if all(item == values[0] for item in values):
        return "uniform"
    symmetric = all(values[index] == values[-1 - index] for index in range(len(values)))
    increasing = all(values[index] < values[index + 1] for index in range(len(values) - 1))
    decreasing = all(values[index] > values[index + 1] for index in range(len(values) - 1))
    if symmetric and not increasing and not decreasing:
        return "lens-symmetric"
    if increasing or decreasing:
        return "illumination-gradient"
    return "unstructured"


def field_class(samples: list[str]) -> str:
    """Classify a sample row without consulting a shading map."""
    require(type(samples) is list, "samples must be a list")
    parsed = [Decimal(_decimal(item, "sample")) for item in samples]
    require(len(parsed) >= 2, "samples must contain at least two values")
    return _class(parsed)


def _protocol(value: object) -> dict:
    item = exact_keys(value, PROTOCOL_KEYS, "protocol")
    require(item["illumination"] == PROTOCOL["illumination"], "protocol illumination drifted")
    require(item["coordinateFrame"] == PROTOCOL["coordinateFrame"], "protocol coordinate frame drifted")
    require(item["validation"] == PROTOCOL["validation"], "protocol validation drifted")
    return item


def _bounds(value: object) -> dict:
    item = exact_keys(value, GAIN_KEYS, "gainBounds")
    low = Decimal(_decimal(item["min"], "gainBounds min"))
    high = Decimal(_decimal(item["max"], "gainBounds max"))
    require(low > 0 and high > low, "gain bounds must be positive and ordered")
    return item


def _session(value: object) -> dict:
    item = exact_keys(value, SESSION_KEYS, "session")
    _text(item["lens"], "session lens")
    _text(item["focus"], "session focus")
    _text(item["aperture"], "session aperture")
    _positive(item["exposureNs"], "session exposureNs")
    _text(item["firmware"], "session firmware")
    return item


def _capture(value: object) -> dict:
    item = exact_keys(value, CAPTURE_KEYS, "capture")
    cfa = _text(item["cfa"], "capture cfa")
    require(cfa in CFA, "capture cfa must be a supported Bayer phase")
    _positive(item["sourceWidth"], "capture sourceWidth")
    _positive(item["sourceHeight"], "capture sourceHeight")
    _crop(item["crop"], "capture crop")
    return item


def _field(value: object) -> dict:
    item = exact_keys(value, FIELD_KEYS, "field")
    kind = _text(item["kind"], "field kind")
    require(kind in FIELD_KINDS, "field kind is not a known class")
    _samples(item["samples"], "field")
    return item


def _map(value: object) -> dict:
    item = exact_keys(value, MAP_KEYS, "shadingMap")
    frame = _text(item["frame"], "shadingMap frame")
    require(frame in FRAMES, "shadingMap frame must be sensor-crop or display")
    orientation = _text(item["orientation"], "shadingMap orientation")
    require(orientation in ORIENTATIONS, "shadingMap orientation must be native or rotated")
    _crop(item["crop"], "shadingMap crop")
    cfa = _text(item["cfa"], "shadingMap cfa")
    require(cfa in CFA, "shadingMap cfa must be a supported Bayer phase")
    _samples(item["gains"], "shadingMap gains")
    _bool(item["appliedAfterRotation"], "shadingMap appliedAfterRotation")
    return item


def _validation(value: object) -> dict:
    item = exact_keys(value, VALIDATION_KEYS, "validation")
    _text(item["id"], "validation id")
    _bool(item["separate"], "validation separate")
    _samples(item["samples"], "validation")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P043 flat-field schema."""
    exact_keys(document, DOCUMENT_KEYS, "flat-field document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P043")
    require(document["mapId"] == MAP_ID, "mapId must be s23-flat-field-shading-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "flat-field document needs the P043 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _protocol(document["protocol"])
    _bounds(document["gainBounds"])
    _session(document["session"])
    _capture(document["capture"])
    field = _field(document["field"])
    shading = _map(document["shadingMap"])
    validation = _validation(document["validation"])
    require(len(field["samples"]) == len(shading["gains"]), "shading gains must match the field length")
    require(
        len(validation["samples"]) == len(field["samples"]),
        "validation samples must match the field length",
    )


def authored_gains(document: dict) -> list[str]:
    """Return the stored lens-shading gains, never a gain row derived from the field."""
    validate_document(document)
    return list(document["shadingMap"]["gains"])


def preserved_inventory(document: dict) -> list[str]:
    """Stable evidence inventory. Failures must not drop these tokens."""
    validate_document(document)
    session = document["session"]
    capture = document["capture"]
    shading = document["shadingMap"]
    validation = document["validation"]
    bounds = document["gainBounds"]
    return [
        f"lens:{session['lens']}",
        f"focus:{session['focus']}",
        f"aperture:{session['aperture']}",
        f"exposureNs:{session['exposureNs']}",
        f"firmware:{session['firmware']}",
        f"cfa:{capture['cfa']}",
        f"source:{capture['sourceWidth']}x{capture['sourceHeight']}",
        f"captureCrop:{capture['crop']}",
        f"mapCrop:{shading['crop']}",
        f"mapCfa:{shading['cfa']}",
        f"mapFrame:{shading['frame']}",
        f"mapOrientation:{shading['orientation']}",
        "field:" + ",".join(document["field"]["samples"]),
        "gains:" + ",".join(shading["gains"]),
        f"gainBounds:{bounds['min']}..{bounds['max']}",
        f"validation:{validation['id']}:" + ",".join(validation["samples"]),
    ]


def _fit(crop: tuple[int, int, int, int], width: int, height: int) -> bool:
    crop_w, crop_h, left, top = crop
    return left + crop_w <= width and top + crop_h <= height


def _claims(document: dict, application: str) -> list[str]:
    field_values = [Decimal(item) for item in document["field"]["samples"]]
    gain_values = [Decimal(item) for item in document["shadingMap"]["gains"]]
    computed = _class(field_values)
    gain_increasing = all(gain_values[index] < gain_values[index + 1] for index in range(len(gain_values) - 1))
    gain_decreasing = all(gain_values[index] > gain_values[index + 1] for index in range(len(gain_values) - 1))
    capture_text, capture_crop = _crop(document["capture"]["crop"], "capture crop")
    map_text, map_crop = _crop(document["shadingMap"]["crop"], "shadingMap crop")
    source_w = int(document["capture"]["sourceWidth"])
    source_h = int(document["capture"]["sourceHeight"])
    low = Decimal(document["gainBounds"]["min"])
    high = Decimal(document["gainBounds"]["max"])
    claims: list[str] = []
    if application == MUTANT_APPLICATION or document["shadingMap"]["appliedAfterRotation"] is True:
        claims.append("display-after-rotation")
    if document["shadingMap"]["frame"] == "display":
        claims.append("display-frame")
    if computed == "illumination-gradient":
        claims.append("illumination-gradient")
    if computed == "illumination-gradient" and (gain_increasing or gain_decreasing):
        claims.append("gradient-absorbed")
    if computed == "lens-symmetric":
        claims.append("non-uniform-illumination")
    if computed == "unstructured":
        claims.append("unclassified-field")
    if document["field"]["kind"] != computed:
        claims.append("field-kind-mismatch")
    if (capture_crop[2], capture_crop[3]) != (map_crop[2], map_crop[3]):
        claims.append("crop-origin-mismatch")
    if (capture_crop[0], capture_crop[1]) != (map_crop[0], map_crop[1]):
        claims.append("crop-size-mismatch")
    if document["capture"]["cfa"] != document["shadingMap"]["cfa"]:
        claims.append("cfa-mismatch")
    if document["shadingMap"]["orientation"] != "native":
        claims.append("rotated-application")
    if capture_crop[2] % 2 or capture_crop[3] % 2:
        if (capture_crop[2], capture_crop[3]) != (map_crop[2], map_crop[3]):
            claims.append("odd-crop-origin")
    if not _fit(capture_crop, source_w, source_h) or not _fit(map_crop, source_w, source_h):
        claims.append("dimension-mismatch")
    if any(item < low or item > high for item in gain_values):
        claims.append("gain-unbounded")
    if document["validation"]["separate"] is not True:
        claims.append("validation-not-separate")
    require(capture_text and map_text, "crops already validated")
    return claims


def _decision_for(claims: list[str], document: dict, application: str) -> str:
    display = application == MUTANT_APPLICATION or "display-after-rotation" in claims or "display-frame" in claims
    if display:
        return "rejected"
    hard = {
        "illumination-gradient",
        "gradient-absorbed",
        "non-uniform-illumination",
        "unclassified-field",
        "field-kind-mismatch",
        "crop-origin-mismatch",
        "crop-size-mismatch",
        "cfa-mismatch",
        "rotated-application",
        "odd-crop-origin",
        "dimension-mismatch",
        "gain-unbounded",
        "validation-not-separate",
    }
    if any(item in hard for item in claims):
        return "shading_rejected"
    validation_class = _class([Decimal(item) for item in document["validation"]["samples"]])
    if validation_class != "uniform":
        return "withheld"
    return "host_consistent"


def _reasons(decision: str, claims: list[str], document: dict, application: str) -> list[str]:
    capture = document["capture"]["crop"]
    mapped = document["shadingMap"]["crop"]
    reasons: list[str] = []
    if application == MUTANT_APPLICATION or "display-after-rotation" in claims or "display-frame" in claims:
        reasons.append(MUTANT)
        reasons.append("display coordinates after rotation were rejected")
        reasons.append("shading gains were not reprojected into display space")
    reasons.append(ORACLE)
    if "illumination-gradient" in claims and "gradient-absorbed" not in claims:
        reasons.append("lighting gradient was not absorbed into the lens-shading correction")
    if "gradient-absorbed" in claims:
        reasons.append("monotonic shading gains track the lighting gradient and were refused")
    if "crop-origin-mismatch" in claims:
        reasons.append(f"coordinate mismatch: capture crop {capture} versus map crop {mapped}")
    if "odd-crop-origin" in claims:
        _, crop = _crop(capture, "capture crop")
        reasons.append(f"odd crop origin {crop[2]}+{crop[3]} is not aligned to the shading map")
    if "non-uniform-illumination" in claims:
        reasons.append("symmetric non-uniform illumination is not a diffuse uniform field")
    if "gain-unbounded" in claims:
        bounds = document["gainBounds"]
        reasons.append(f"correction gains exceed {bounds['min']}..{bounds['max']}")
    if "validation-not-separate" in claims:
        reasons.append("validation reused the calibration capture")
    if decision == "withheld":
        reasons.append("separate flat capture is not uniform")
        reasons.append("correction is not certified")
    if decision == "host_consistent":
        bounds = document["gainBounds"]
        reasons.append("uniform illumination was not converted into a shading ramp")
        reasons.append("coordinates match the capture crop and CFA")
        reasons.append(f"correction gains stay inside {bounds['min']}..{bounds['max']}")
        reasons.append(f"separate flat capture {document['validation']['id']} was retained")
    reasons.append(HOST_LIMIT)
    return _dedupe(reasons)


def _questions(decision: str, document: dict) -> list[str]:
    questions = ["physical S23 flat-field unverified"]
    if decision != "rejected":
        questions.append("shading gains were kept separate from the illumination samples")
    if decision == "withheld":
        questions.append("holdout flat is not uniform")
    if decision == "rejected":
        questions.append("display-space shading was not applied")
    return questions


def assess(document: dict, application: str = SENSOR_APPLICATION) -> dict:
    """Validate a shading map against illumination, crop, CFA, and gain bounds.

    ``display-after-rotation`` is the deliberate mutant and is always rejected.
    The decision is never ``qualified`` or ``allowed``. Preserved results keep
    the session, both crops, the field samples, and the authored gains.
    """
    require(application in APPLICATIONS, "application must be sensor-crop or display-after-rotation")
    validate_document(document)
    claims = _claims(document, application)
    decision = _decision_for(claims, document, application)
    if application == MUTANT_APPLICATION:
        require(decision == "rejected", "display-after-rotation must not pass")
        require("display-after-rotation" in claims, "mutant claim missing")
    preserved = preserved_inventory(document)
    require(any(item.startswith("field:") for item in preserved), "field inventory missing")
    require(any(item.startswith("gains:") for item in preserved), "gain inventory missing")
    result = _result(
        decision,
        _reasons(decision, claims, document, application),
        claims,
        preserved,
        _questions(decision, document),
    )
    require(result["decision"] not in _FORBIDDEN, "P043 must not decide qualified or allowed")
    return result
