"""TC-P120-05 Stabilization-depth misalignment.

Host fixture. RGB, depth, and mask transforms must match. Field of view,
valid area, and the combined stabilization crop follow the shared scale.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-05"
NAME = "Stabilization-depth misalignment"
INTERVENTION = "Apply a changing stabilization transform to RGB while depth begins in source coordinates."
EXPECTED = "Transform all relevant geometry consistently and update valid region and field-of-view evidence."
NEGATIVE = "Stabilizing color alone while leaving masks unchanged must fail."
REPEAT = "Repeat crop changes, portrait rotation, and combined camera and subject motion."
NEGATIVE_TOKEN = "color-stabilized-masks-unchanged"
DEPTH_TOKEN = "depth-left-in-source-coordinates"
FOV_TOKEN = "valid-region-or-fov-not-updated"
TRANSFORM_KEYS = ("scale", "rotationRadians", "tx", "ty")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "combinationPassed",
    "report",
    "rgbTransform",
    "depthTransform",
    "maskTransform",
    "sourceFovDegrees",
    "reportedFovDegrees",
    "sourceValidArea",
    "reportedValidArea",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _transform(value, label: str) -> dict[str, float]:
    _CORE.require(isinstance(value, dict) and set(value) == set(TRANSFORM_KEYS), label + " must contain scale, rotationRadians, tx, ty")
    parsed = {key: _CORE.require_number(value[key], label + "." + key) for key in TRANSFORM_KEYS}
    _CORE.require(parsed["scale"] >= 1.0, label + " scale must be at least 1")
    return parsed


def _same(left: dict[str, float], right: dict[str, float]) -> bool:
    return all(_CORE.exposures_match(left[key], right[key]) for key in TRANSFORM_KEYS)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    rgb = _transform(payload["rgbTransform"], "rgbTransform")
    depth = _transform(payload["depthTransform"], "depthTransform")
    mask = _transform(payload["maskTransform"], "maskTransform")
    source_fov = _CORE.require_number(payload["sourceFovDegrees"], "sourceFovDegrees")
    reported_fov = _CORE.require_number(payload["reportedFovDegrees"], "reportedFovDegrees")
    source_area = _CORE.require_number(payload["sourceValidArea"], "sourceValidArea")
    reported_area = _CORE.require_number(payload["reportedValidArea"], "reportedValidArea")
    _CORE.require(min(source_fov, reported_fov, source_area, reported_area) > 0, "field of view and valid area must be positive")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    aligned = True
    if not _same(rgb, mask):
        aligned = False
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("defectOrigin=stabilization")
    if not _same(rgb, depth):
        aligned = False
        rejected.append(DEPTH_TOKEN)
        reasons.append("depth must receive the same stabilization transform as RGB")
        reasons.append("defectOrigin=depth")
    if aligned:
        scale = rgb["scale"]
        expected_fov = source_fov / scale
        expected_area = source_area / (scale * scale)
        expected_crop = 1.0 - (1.0 / (scale * scale))
        report_ready = _CORE.MISSING_FIELDS not in rejected and _CORE.EXPOSURE_MISMATCH not in rejected
        crop_ok = True
        if report_ready:
            crop = _CORE.require_number(payload["report"]["stabilization_crop_fraction"], "stabilization_crop_fraction")
            crop_ok = _CORE.exposures_match(crop, expected_crop)
        geometry_ok = (
            _CORE.exposures_match(reported_fov, expected_fov)
            and _CORE.exposures_match(reported_area, expected_area)
            and crop_ok
        )
        if not geometry_ok:
            rejected.append(FOV_TOKEN)
            reasons.append(
                "expectedFov="
                + _CORE.format_number(expected_fov)
                + " expectedValidArea="
                + _CORE.format_number(expected_area)
                + " expectedCrop="
                + _CORE.format_number(expected_crop)
            )
            reasons.append("defectOrigin=stabilization")
        else:
            reasons.append("shared stabilization transform updated fov, valid area, and crop")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
