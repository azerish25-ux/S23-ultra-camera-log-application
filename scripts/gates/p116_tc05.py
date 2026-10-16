"""TC-P116-05 Stabilization-depth misalignment.

Host fixture. RGB, depth, and mask transforms must match. Field of view and
valid area follow the shared scale. Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-05"
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
    "rgbTransform",
    "depthTransform",
    "maskTransform",
    "sourceFovDegrees",
    "reportedFovDegrees",
    "sourceValidArea",
    "reportedValidArea",
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=_CORE.RELATIVE_TOLERANCE, abs_tol=_CORE.ABSOLUTE_TOLERANCE)


def _transform(value, label: str) -> dict[str, float]:
    if not isinstance(value, dict) or set(value) != set(TRANSFORM_KEYS):
        raise ValueError(label + " must contain scale, rotationRadians, tx, ty")
    parsed = {key: _number(value[key], label + "." + key) for key in TRANSFORM_KEYS}
    if parsed["scale"] <= 0:
        raise ValueError(label + " scale must be positive")
    return parsed


def _same(left: dict[str, float], right: dict[str, float]) -> bool:
    return all(_close(left[key], right[key]) for key in TRANSFORM_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    rgb = _transform(payload["rgbTransform"], "rgbTransform")
    depth = _transform(payload["depthTransform"], "depthTransform")
    mask = _transform(payload["maskTransform"], "maskTransform")
    source_fov = _number(payload["sourceFovDegrees"], "sourceFovDegrees")
    reported_fov = _number(payload["reportedFovDegrees"], "reportedFovDegrees")
    source_area = _number(payload["sourceValidArea"], "sourceValidArea")
    reported_area = _number(payload["reportedValidArea"], "reportedValidArea")
    if min(source_fov, reported_fov, source_area, reported_area) <= 0:
        raise ValueError("field of view and valid area must be positive")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    aligned = True
    if not _same(rgb, mask):
        aligned = False
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not _same(rgb, depth):
        aligned = False
        rejected.append(DEPTH_TOKEN)
        reasons.append("depth must receive the same stabilization transform as RGB")
    if aligned:
        expected_fov = source_fov / rgb["scale"]
        expected_area = source_area / (rgb["scale"] * rgb["scale"])
        if not _close(reported_fov, expected_fov) or not _close(reported_area, expected_area):
            rejected.append(FOV_TOKEN)
            reasons.append(
                "expectedFov="
                + format(expected_fov, ".12g")
                + " expectedValidArea="
                + format(expected_area, ".12g")
            )
        else:
            reasons.append("shared stabilization transform updated fov and valid area")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
