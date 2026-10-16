"""TC-P115-05 Stabilization-depth misalignment.

Host fixture. A stabilization transform applied to RGB must be applied to depth
and masks, and the valid region plus field of view must be updated. Stabilizing
color alone is rejected.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P115-05"
NAME = "Stabilization-depth misalignment"
INTERVENTION = "Apply a changing stabilization transform to RGB while depth begins in source coordinates."
EXPECTED = "Transform all relevant geometry consistently and update valid region and field-of-view evidence."
NEGATIVE = "Stabilizing color alone while leaving masks unchanged must fail."
REPEAT = "Repeat crop changes, portrait rotation, and combined camera and subject motion."
REPEATS = ("crop", "portrait-rotation", "combined-motion")
TOLERANCE = 1e-9
PAYLOAD_KEYS = (
    "evidenceId",
    "rgbTransform",
    "depthTransform",
    "maskTransform",
    "validRegionUpdated",
    "fovUpdated",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject color-only stabilization. Leave the original mask in the result."""
    evidence, rgb, depth, mask, valid_region, fov, repeat = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {repeat}"]
    if not _changed(rgb):
        if _changed(depth) or _changed(mask):
            rejected.append("geometry-inconsistent")
            reasons.append("depth or mask moved without an RGB stabilization")
    else:
        if not _changed(mask):
            rejected.append("color-stabilized-mask-unchanged")
            reasons.append(NEGATIVE)
        elif not _matches(rgb, mask):
            rejected.append("mask-transform-mismatch")
            reasons.append("mask transform does not match the RGB stabilization")
        if not _matches(rgb, depth):
            rejected.append("depth-not-transformed")
            reasons.append("depth was left in source coordinates")
        if not valid_region:
            rejected.append("valid-region-not-updated")
        if not fov:
            rejected.append("fov-not-updated")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("RGB, depth, and mask share the stabilization")
    preserved = [evidence, {"rgb": rgb, "depth": depth, "mask": mask, "validRegionUpdated": valid_region, "fovUpdated": fov}]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _transform(value: object, label: str) -> list[list[float]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    rows = []
    for index, pair in enumerate(value):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"{label} {index} must be a pair")
        rows.append([_finite(pair[0], f"{label} {index} x"), _finite(pair[1], f"{label} {index} y")])
    return rows


def _changed(rows: list[list[float]]) -> bool:
    return any(abs(item) > TOLERANCE for row in rows for item in row)


def _matches(left: list[list[float]], right: list[list[float]]) -> bool:
    return all(
        abs(left[index][0] - right[index][0]) <= TOLERANCE and abs(left[index][1] - right[index][1]) <= TOLERANCE
        for index in range(len(left))
    )


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    valid_region = payload["validRegionUpdated"]
    fov = payload["fovUpdated"]
    if type(valid_region) is not bool or type(fov) is not bool:
        raise ValueError("update flags must be bools")
    rgb = _transform(payload["rgbTransform"], "rgbTransform")
    depth = _transform(payload["depthTransform"], "depthTransform")
    mask = _transform(payload["maskTransform"], "maskTransform")
    if not (len(rgb) == len(depth) == len(mask)):
        raise ValueError("transforms must share one length")
    return evidence, rgb, depth, mask, valid_region, fov, repeat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or not reasons or preserved[0] not in preserved:
        raise ValueError("result contract drifted")
    return result
