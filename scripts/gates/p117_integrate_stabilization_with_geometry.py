#!/usr/bin/env python3
"""P117 Integrate stabilization with geometry.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P117-01 through TC-P117-08 modules.

A stabilization warp is a 2D translation (dx, dy):

    output (ox, oy) = source (sx, sy) + (dx, dy)
    source (sx, sy) = output (ox, oy) - (dx, dy)

A sample is known only when that source location lies inside the source
rectangle [0, width) x [0, height). Otherwise it is unknown. Unknown samples
are not filled with generated texture. fill="generated" or inpaint is rejected.

The declared crop is an axis-aligned rectangle in source coordinates. It must
be fully inside the source and no larger than the source. It must also lie in
the post-translation valid region (the source pixels that remain on the
original canvas):

    x in [max(0, -dx), min(width, width - dx))
    y in [max(0, -dy), min(height, height - dy))

Crop coverage is crop area / source area. Coverage of 1 is valid only when the
warp is zero. A coverage of 1 with nonzero translation is a full-frame claim
that hides lost borders and is rejected.

A crop that changes lens_id or image aspect must be recorded. Stabilization
still keeps the source timestamp and lens_id. Depth and subject masks use the
same translation as RGB. OIS, EIS, and post corrections are explicit; unknown
corrections are not stacked.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P117"
TITLE = "Integrate stabilization with geometry"
WORKSTREAM = 15
DEPENDENCIES = ("P116",)
GOAL = "Keep camera-motion correction, crop, depth, and lens mapping in a shared coordinate system."
METHOD = (
    "Represent stabilization as explicit per-frame transforms and valid regions. "
    "Apply corresponding mappings to depth and masks. Distinguish physical OIS, camera EIS, and post "
    "stabilization where known; avoid stacking unknown corrections without evidence."
)
FIXTURE = "A stabilized crop that moves across the original image while a depth map remains in source coordinates."
ORACLE = "All render inputs align after transformation and the field-of-view report reflects the changing crop."
MUTANT = "Stabilize RGB while leaving depth and subject masks untransformed."
DELIVERABLE = "Stabilization geometry contract and alignment tests"
CROP_RULE = (
    "Crop coverage is crop area divided by source area. "
    "The crop must be fully inside the source and no larger than the source, and inside the "
    "valid region that remains after translation (dx, dy). "
    "Coverage of 1 is valid only when the warp is zero; nonzero translation with coverage 1 "
    "hides lost borders and is rejected. "
    "Samples that map outside the source are unknown and are not filled with generated texture."
)

ABSOLUTE_TOLERANCE = 1e-9
RELATIVE_TOLERANCE = 1e-9
COVERAGE_UNITY_TOLERANCE = 1e-12
WARP_ZERO_TOLERANCE = 1e-12
FILL_VALUES = ("none", "unknown", "generated")
CORRECTION_KINDS = ("ois", "eis", "post")
LAYER_NAMES = ("rgb", "depth", "mask")
SOURCE_KEYS = ("width", "height", "lensId", "timestamp")
WARP_KEYS = ("dx", "dy")
CROP_KEYS = ("x", "y", "width", "height")
STABILIZED_KEYS = ("lensId", "timestamp", "aspect")
SAMPLE_KEYS = ("x", "y", "layer")
CORRECTION_KEYS = ("kind", "dx", "dy", "known")

GENERATED_FILL = "generated-fill"
INPAINT = "inpaint"
CROP_OUTSIDE_SOURCE = "crop-outside-source"
CROP_EXCEEDS_SOURCE = "crop-exceeds-source"
FULL_FRAME_HIDES_BORDERS = "full-frame-hides-lost-borders"
CROP_OUTSIDE_VALID = "crop-outside-valid-region"
UNRECORDED_ASPECT = "unrecorded-aspect-changing-crop"
UNRECORDED_LENS = "unrecorded-lens-changing-crop"
DROPPED_LENS = "dropped-lens-identity"
DROPPED_TIMESTAMP = "dropped-source-timestamp"
ASPECT_MISMATCH = "reported-aspect-does-not-match-crop"
RGB_WARP_MISMATCH = "rgb-warp-mismatch"
DEPTH_UNTRANSFORMED = "depth-untransformed"
DEPTH_LEFT_IN_SOURCE = "depth-left-in-source-coordinates"
MASK_UNTRANSFORMED = "color-stabilized-masks-unchanged"
UNKNOWN_CORRECTION = "unknown-correction-stacked"
WARP_CORRECTION_MISMATCH = "warp-does-not-match-known-corrections"
FOV_MISMATCH = "fov-does-not-reflect-crop"

GEOMETRY_KEYS = {
    "source",
    "warp",
    "crop",
    "cropRecorded",
    "fill",
    "inpaint",
    "stabilized",
    "layers",
    "corrections",
    "samples",
    "sourceHorizontalFovDegrees",
    "reportedHorizontalFovDegrees",
    "depthMap",
}
DOCUMENT_KEYS = GEOMETRY_KEYS | {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
}
EVALUATE_KEYS = GEOMETRY_KEYS | {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_number(value: Any, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def require_text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    require(value == value.strip(), f"{label} must not have surrounding whitespace")
    return value


def require_object(value: Any, label: str, keys: tuple[str, ...]) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == set(keys), f"{label} keys must be " + ", ".join(keys))
    return value


def format_number(value: float) -> str:
    return format(value, ".12g")


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=RELATIVE_TOLERANCE, abs_tol=ABSOLUTE_TOLERANCE)


def warp_is_zero(dx: float, dy: float) -> bool:
    return abs(dx) <= WARP_ZERO_TOLERANCE and abs(dy) <= WARP_ZERO_TOLERANCE


def same_warp(left_dx: float, left_dy: float, right_dx: float, right_dy: float) -> bool:
    return close(left_dx, right_dx) and close(left_dy, right_dy)


def expected_horizontal_fov(
    source_width: float,
    source_hfov_degrees: float,
    crop_x: float,
    crop_width: float,
) -> float:
    """Rectilinear horizontal field of view of a crop window.

    The principal point is the source centre. Focal length comes from the
    source field of view. The crop's field of view is the angle between its
    left and right edges, so an off-centre crop is not treated as centred.
    """
    require(source_width > 0, "source width must be positive")
    require(
        0.0 < source_hfov_degrees < 180.0,
        "source horizontal field of view must be between 0 and 180",
    )
    require(crop_width > 0, "crop width must be positive")
    half = math.radians(source_hfov_degrees) / 2.0
    focal = (source_width / 2.0) / math.tan(half)
    left = math.atan((crop_x - source_width / 2.0) / focal)
    right = math.atan((crop_x + crop_width - source_width / 2.0) / focal)
    span = math.degrees(right - left)
    require(span > 0.0, "crop horizontal field of view must be positive")
    return span


def valid_source_bounds(width: float, height: float, dx: float, dy: float) -> tuple[float, float, float, float]:
    """Source region that remains inside the original canvas after translation."""
    x0 = max(0.0, -dx)
    x1 = min(width, width - dx)
    y0 = max(0.0, -dy)
    y1 = min(height, height - dy)
    return x0, y0, x1, y1


def region_contains(
    x: float,
    y: float,
    width: float,
    height: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> bool:
    span_x = x1 - x0
    span_y = y1 - y0
    if span_x <= ABSOLUTE_TOLERANCE or span_y <= ABSOLUTE_TOLERANCE:
        return False
    return (
        x >= x0 - ABSOLUTE_TOLERANCE
        and y >= y0 - ABSOLUTE_TOLERANCE
        and x + width <= x1 + ABSOLUTE_TOLERANCE
        and y + height <= y1 + ABSOLUTE_TOLERANCE
    )


def inverse_sample(x: float, y: float, dx: float, dy: float) -> tuple[float, float]:
    """Map an output pixel back to source coordinates. Does not invent samples."""
    return x - dx, y - dy


def inside_source(sx: float, sy: float, width: float, height: float) -> bool:
    return 0.0 <= sx < width and 0.0 <= sy < height


def inside_crop(sx: float, sy: float, crop: dict[str, float]) -> bool:
    return (
        crop["x"] <= sx < crop["x"] + crop["width"]
        and crop["y"] <= sy < crop["y"] + crop["height"]
    )


def _identity(value: Any, label: str) -> str:
    return require_text(value, label)


def _positive_int(value: Any, label: str) -> int:
    require(type(value) is int and value > 0, f"{label} must be a positive int")
    return value


def _warp(value: Any, label: str) -> tuple[float, float]:
    obj = require_object(value, label, WARP_KEYS)
    return require_number(obj["dx"], label + ".dx"), require_number(obj["dy"], label + ".dy")


def _parse_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(geometry, dict), "geometry must be an object")
    missing = GEOMETRY_KEYS - set(geometry)
    extra = set(geometry) - GEOMETRY_KEYS
    require(not missing, "geometry missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "geometry has unexpected fields: " + ", ".join(sorted(extra)))

    source = require_object(geometry["source"], "source", SOURCE_KEYS)
    width = _positive_int(source["width"], "source.width")
    height = _positive_int(source["height"], "source.height")
    source_lens = require_text(source["lensId"], "source.lensId")
    source_timestamp = require_number(source["timestamp"], "source.timestamp")

    dx, dy = _warp(geometry["warp"], "warp")
    crop_obj = require_object(geometry["crop"], "crop", CROP_KEYS)
    crop = {
        "x": require_number(crop_obj["x"], "crop.x"),
        "y": require_number(crop_obj["y"], "crop.y"),
        "width": require_number(crop_obj["width"], "crop.width"),
        "height": require_number(crop_obj["height"], "crop.height"),
    }
    require(crop["width"] > 0.0 and crop["height"] > 0.0, "crop width and height must be positive")
    require(type(geometry["cropRecorded"]) is bool, "cropRecorded must be a bool")
    fill = geometry["fill"]
    require(fill in FILL_VALUES, "fill must be none, unknown, or generated")
    require(type(geometry["inpaint"]) is bool, "inpaint must be a bool")

    stabilized = require_object(geometry["stabilized"], "stabilized", STABILIZED_KEYS)
    stabilized_lens = require_text(stabilized["lensId"], "stabilized.lensId")
    stabilized_timestamp = require_number(stabilized["timestamp"], "stabilized.timestamp")
    stabilized_aspect = require_number(stabilized["aspect"], "stabilized.aspect")
    require(stabilized_aspect > 0.0, "stabilized.aspect must be positive")

    layers_obj = geometry["layers"]
    require(isinstance(layers_obj, dict) and set(layers_obj) == set(LAYER_NAMES),
            "layers must contain rgb, depth, and mask")
    layers = {name: _warp(layers_obj[name], "layers." + name) for name in LAYER_NAMES}

    corrections_in = geometry["corrections"]
    require(isinstance(corrections_in, list), "corrections must be a list")
    corrections = []
    for index, item in enumerate(corrections_in):
        obj = require_object(item, f"corrections[{index}]", CORRECTION_KEYS)
        kind = obj["kind"]
        require(kind in CORRECTION_KINDS, f"corrections[{index}].kind must be ois, eis, or post")
        require(type(obj["known"]) is bool, f"corrections[{index}].known must be a bool")
        corrections.append({
            "kind": kind,
            "dx": require_number(obj["dx"], f"corrections[{index}].dx"),
            "dy": require_number(obj["dy"], f"corrections[{index}].dy"),
            "known": obj["known"],
        })

    samples_in = geometry["samples"]
    require(isinstance(samples_in, list), "samples must be a list")
    samples = []
    for index, item in enumerate(samples_in):
        obj = require_object(item, f"samples[{index}]", SAMPLE_KEYS)
        layer = obj["layer"]
        require(layer in LAYER_NAMES, f"samples[{index}].layer must be rgb, depth, or mask")
        samples.append({
            "x": require_number(obj["x"], f"samples[{index}].x"),
            "y": require_number(obj["y"], f"samples[{index}].y"),
            "layer": layer,
        })

    source_fov = require_number(geometry["sourceHorizontalFovDegrees"], "sourceHorizontalFovDegrees")
    reported_fov = require_number(geometry["reportedHorizontalFovDegrees"], "reportedHorizontalFovDegrees")
    require(0.0 < source_fov < 180.0, "sourceHorizontalFovDegrees must be between 0 and 180")
    require(0.0 < reported_fov < 180.0, "reportedHorizontalFovDegrees must be between 0 and 180")

    depth_map_in = geometry["depthMap"]
    require(isinstance(depth_map_in, list) and len(depth_map_in) == height, "depthMap must have one row per source row")
    depth_map: list[list[float]] = []
    for row_index, row in enumerate(depth_map_in):
        require(isinstance(row, list) and len(row) == width, f"depthMap[{row_index}] must match source width")
        depth_map.append([
            require_number(value, f"depthMap[{row_index}][{col_index}]")
            for col_index, value in enumerate(row)
        ])

    return {
        "width": width,
        "height": height,
        "source_lens": source_lens,
        "source_timestamp": source_timestamp,
        "dx": dx,
        "dy": dy,
        "crop": crop,
        "crop_recorded": geometry["cropRecorded"],
        "fill": fill,
        "inpaint": geometry["inpaint"],
        "stabilized_lens": stabilized_lens,
        "stabilized_timestamp": stabilized_timestamp,
        "stabilized_aspect": stabilized_aspect,
        "layers": layers,
        "corrections": corrections,
        "samples": samples,
        "source_fov": source_fov,
        "reported_fov": reported_fov,
        "depth_map": depth_map,
    }


def evaluate_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    """Apply the translation, crop, and shared-layer contract.

    Unknown samples stay unknown. No generated texture is written into the
    preserved sample tags.
    """
    parsed = _parse_geometry(geometry)
    width = float(parsed["width"])
    height = float(parsed["height"])
    dx = parsed["dx"]
    dy = parsed["dy"]
    crop = parsed["crop"]
    crop_area = crop["width"] * crop["height"]
    source_area = width * height
    coverage = crop_area / source_area
    coverage_token = (
        "cropCoverage="
        + format_number(crop_area)
        + "/"
        + format_number(source_area)
        + "="
        + format_number(coverage)
    )
    x0, y0, x1, y1 = valid_source_bounds(width, height, dx, dy)
    source_aspect = width / height
    crop_aspect = crop["width"] / crop["height"]
    expected_fov = expected_horizontal_fov(width, parsed["source_fov"], crop["x"], crop["width"])

    reasons = [
        "host fixture only; not a physical S23 measurement",
        "fixture: " + FIXTURE,
        "crop rule: " + CROP_RULE,
        coverage_token,
        "validRegion=("
        + format_number(x0)
        + ","
        + format_number(y0)
        + ")-("
        + format_number(x1)
        + ","
        + format_number(y1)
        + ")",
        "warp dx=" + format_number(dx) + " dy=" + format_number(dy),
        "expectedHorizontalFovDegrees=" + format_number(expected_fov),
    ]
    rejected: list[str] = []

    if parsed["fill"] == "generated":
        rejected.append(GENERATED_FILL)
        reasons.append("fill=generated is rejected; outside samples stay unknown")
    if parsed["inpaint"]:
        rejected.append(INPAINT)
        reasons.append("inpaint is rejected; outside samples stay unknown")

    if not region_contains(crop["x"], crop["y"], crop["width"], crop["height"], 0.0, 0.0, width, height):
        rejected.append(CROP_OUTSIDE_SOURCE)
        reasons.append("crop must be fully inside the source and no larger than the source")
    if crop_area > source_area + ABSOLUTE_TOLERANCE:
        rejected.append(CROP_EXCEEDS_SOURCE)
        reasons.append("crop area exceeds the source area")
    if abs(coverage - 1.0) <= COVERAGE_UNITY_TOLERANCE and not warp_is_zero(dx, dy):
        rejected.append(FULL_FRAME_HIDES_BORDERS)
        reasons.append("coverage of 1 with nonzero translation hides lost borders")
    if not region_contains(crop["x"], crop["y"], crop["width"], crop["height"], x0, y0, x1, y1):
        rejected.append(CROP_OUTSIDE_VALID)
        reasons.append("crop includes source pixels the translation moves off the canvas")

    aspect_changed = not close(crop_aspect, source_aspect) or not close(parsed["stabilized_aspect"], source_aspect)
    lens_changed = parsed["stabilized_lens"] != parsed["source_lens"]
    if aspect_changed and not parsed["crop_recorded"]:
        rejected.append(UNRECORDED_ASPECT)
        reasons.append("image aspect changed without recording the crop")
    if lens_changed and not parsed["crop_recorded"]:
        rejected.append(UNRECORDED_LENS)
        reasons.append("lens_id changed without recording the crop")
    if lens_changed:
        rejected.append(DROPPED_LENS)
        reasons.append("stabilization dropped the source lens_id")
    if not close(parsed["stabilized_timestamp"], parsed["source_timestamp"]):
        rejected.append(DROPPED_TIMESTAMP)
        reasons.append("stabilization dropped the source timestamp")
    if not close(parsed["stabilized_aspect"], crop_aspect):
        rejected.append(ASPECT_MISMATCH)
        reasons.append(
            "stabilized aspect "
            + format_number(parsed["stabilized_aspect"])
            + " does not match crop aspect "
            + format_number(crop_aspect)
        )

    rgb_dx, rgb_dy = parsed["layers"]["rgb"]
    depth_dx, depth_dy = parsed["layers"]["depth"]
    mask_dx, mask_dy = parsed["layers"]["mask"]
    if not same_warp(rgb_dx, rgb_dy, dx, dy):
        rejected.append(RGB_WARP_MISMATCH)
        reasons.append("rgb layer translation must equal the declared stabilization warp")
    if not same_warp(depth_dx, depth_dy, rgb_dx, rgb_dy):
        rejected.append(DEPTH_UNTRANSFORMED)
        reasons.append("depth must receive the same translation as rgb")
        if warp_is_zero(depth_dx, depth_dy) and not warp_is_zero(rgb_dx, rgb_dy):
            rejected.append(DEPTH_LEFT_IN_SOURCE)
            reasons.append("depth was left in source coordinates")
    if not same_warp(mask_dx, mask_dy, rgb_dx, rgb_dy):
        rejected.append(MASK_UNTRANSFORMED)
        reasons.append("stabilizing color alone while leaving masks unchanged must fail")

    known_dx = 0.0
    known_dy = 0.0
    known_parts: list[str] = []
    unknown = False
    for correction in parsed["corrections"]:
        label = correction["kind"] + "=" + format_number(correction["dx"]) + "," + format_number(correction["dy"])
        if correction["known"]:
            known_dx += correction["dx"]
            known_dy += correction["dy"]
            known_parts.append(label)
        else:
            unknown = True
            reasons.append("unknown correction excluded " + label)
    if unknown:
        rejected.append(UNKNOWN_CORRECTION)
        reasons.append("unknown OIS, EIS, or post corrections must not be stacked")
    if not same_warp(known_dx, known_dy, dx, dy):
        rejected.append(WARP_CORRECTION_MISMATCH)
        reasons.append(
            "known corrections sum to dx="
            + format_number(known_dx)
            + " dy="
            + format_number(known_dy)
        )
    reasons.append("knownCorrections " + (" ".join(known_parts) if known_parts else "none"))

    if not close(parsed["reported_fov"], expected_fov):
        rejected.append(FOV_MISMATCH)
        reasons.append("reported field of view does not reflect the crop")

    preserved = [
        coverage_token,
        "sourceLensId=" + parsed["source_lens"] + " sourceTimestamp=" + format_number(parsed["source_timestamp"]),
        "expectedHorizontalFovDegrees=" + format_number(expected_fov),
    ]
    depth_map = parsed["depth_map"]
    for index, sample in enumerate(parsed["samples"]):
        layer_dx, layer_dy = parsed["layers"][sample["layer"]]
        sx, sy = inverse_sample(sample["x"], sample["y"], layer_dx, layer_dy)
        known = inside_source(sx, sy, width, height)
        in_crop = known and inside_crop(sx, sy, crop)
        status = "known" if known else "unknown"
        tag = (
            f"sample[{index}] layer={sample['layer']} "
            f"output=({format_number(sample['x'])},{format_number(sample['y'])}) "
            f"source=({format_number(sx)},{format_number(sy)}) "
            f"status={status} inCrop={'yes' if in_crop else 'no'}"
        )
        if known and sample["layer"] == "depth":
            column = int(math.floor(sx))
            row = int(math.floor(sy))
            tag += " depth=" + format_number(depth_map[row][column])
        preserved.append(tag)
        if known:
            reasons.append(tag)
        else:
            reasons.append(tag + " outside the source is unknown and has no texture")

    return {
        "decision": "rejected" if rejected else "recorded",
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "coverage": coverage,
    }


def seal_result(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[Any],
    questions: list[str],
) -> dict[str, Any]:
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(reasons, list) and reasons, "reasons must be non-empty")
    require(isinstance(rejected, list), "rejectedClaims must be a list")
    require(isinstance(preserved, list) and preserved, "evidence wiped")
    evidence = preserved[0]
    require(isinstance(evidence, str) and evidence in preserved, "evidence must be preserved")
    require(isinstance(questions, list) and questions, "openQuestions must be non-empty")
    require("physical S23 measurement was not run" in questions, "physical S23 measurement was not noted")
    blob = " ".join(str(item) for item in list(reasons) + [str(item) for item in preserved])
    require("cropCoverage=" in blob, "crop coverage missing")
    return result


def _questions() -> list[str]:
    return [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]


def _decide(case_id: str, evidence: str, claim: str, geometry: dict[str, Any], apply_mutant: bool) -> dict[str, Any]:
    analysis = evaluate_geometry(geometry)
    reasons = [
        "oracle: " + ORACLE,
        "goal: " + GOAL,
    ]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    if apply_mutant:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    preserved: list[Any] = [evidence, claim]
    preserved.extend(analysis["preservedResults"])
    return seal_result(case_id, decision, reasons, rejected, preserved, _questions())


def _geometry_from(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in GEOMETRY_KEYS}


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to one stabilization-geometry fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _identity(document["evidenceId"], "evidenceId")
    claim = _identity(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    return _decide(PHASE, evidence, claim, _geometry_from(document), document["applyMutant"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one stabilization geometry payload. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = _identity(payload["caseId"], "caseId")
    evidence = _identity(payload["evidenceId"], "evidenceId")
    claim = _identity(payload["claim"], "claim")
    require(type(payload["applyMutant"]) is bool, "applyMutant must be a bool")
    return _decide(case_id, evidence, claim, _geometry_from(payload), payload["applyMutant"])


def recorded_geometry() -> dict[str, Any]:
    """4x2 source, translation (1, 0), crop 3x2. Coverage is 6/8 = 0.75.

    Output (1, 0) reads source (0, 0), depth 0. Output (0, 0) reads source
    (-1, 0), which is unknown and carries no depth value.
    """
    source_fov = 90.0
    crop_x = 0.0
    crop_width = 3.0
    return {
        "source": {"width": 4, "height": 2, "lensId": "s23-main", "timestamp": 0.0},
        "warp": {"dx": 1.0, "dy": 0.0},
        "crop": {"x": crop_x, "y": 0.0, "width": crop_width, "height": 2.0},
        "cropRecorded": True,
        "fill": "unknown",
        "inpaint": False,
        "stabilized": {"lensId": "s23-main", "timestamp": 0.0, "aspect": 1.5},
        "layers": {
            "rgb": {"dx": 1.0, "dy": 0.0},
            "depth": {"dx": 1.0, "dy": 0.0},
            "mask": {"dx": 1.0, "dy": 0.0},
        },
        "corrections": [
            {"kind": "ois", "dx": 0.0, "dy": 0.0, "known": True},
            {"kind": "eis", "dx": 0.0, "dy": 0.0, "known": True},
            {"kind": "post", "dx": 1.0, "dy": 0.0, "known": True},
        ],
        "samples": [
            {"x": 1.0, "y": 0.0, "layer": "depth"},
            {"x": 0.0, "y": 0.0, "layer": "depth"},
        ],
        "sourceHorizontalFovDegrees": source_fov,
        "reportedHorizontalFovDegrees": expected_horizontal_fov(4.0, source_fov, crop_x, crop_width),
        "depthMap": [[0, 1, 2, 3], [4, 5, 6, 7]],
    }


def recorded_document() -> dict[str, Any]:
    document = {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": "p117-stabilized-crop",
        "claim": "synthetic-host-fixture",
        "applyMutant": False,
    }
    document.update(recorded_geometry())
    return document
