"""TC-P114-05 Stabilization-depth misalignment.

Host fixture. Depth and masks must take the same transform as RGB. Valid region
and field of view must be updated with the crop. Scope disclosure still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_define_synthetic_shutter_scope",
    Path(__file__).resolve().parent / "p114_define_synthetic_shutter_scope.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE_ID = "TC-P114-05"
NAME = "Stabilization-depth misalignment"
INTERVENTION = "Apply a changing stabilization transform to RGB while depth begins in source coordinates."
EXPECTED = "Transform all relevant geometry consistently and update valid region and field-of-view evidence."
NEGATIVE = "Stabilizing color alone while leaving masks unchanged must fail."
REPEAT = "Repeat crop changes, portrait rotation, and combined camera and subject motion."
NEGATIVE_TOKEN = "stabilizing-color-alone-leaving-masks-unchanged"
DEPTH_TOKEN = "depth-not-transformed-with-color"
REGION_TOKEN = "valid-region-or-fov-not-updated"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "rgb_transform",
    "depth_transform",
    "mask_transform",
    "valid_region_updated",
    "field_of_view_updated",
)


def _transform(value: object, name: str) -> list[float]:
    _GATE.require(isinstance(value, list) and len(value) >= 1, name + " must be a non-empty list")
    return [_GATE.finite_number(item, f"{name}[{index}]") for index, item in enumerate(value)]


def evaluate(payload: dict) -> dict:
    document = _GATE.exact_keys(payload, set(PAYLOAD_KEYS), "payload")
    evidence = _GATE.evidence_id(document["evidenceId"])
    repeat = _GATE.repeat_text(document["repeat"])
    frames = _GATE.parse_frames(document["frames"])
    angle = _GATE.optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = _GATE.optional_positive(document["fps"], "fps")
    contains_estimated = _GATE.flag(document["contains_estimated"], "contains_estimated")
    disclosed = _GATE.flag(document["disclosed"], "disclosed")
    labelled = _GATE.flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    rgb = _transform(document["rgb_transform"], "rgb_transform")
    depth = _transform(document["depth_transform"], "depth_transform")
    mask = _transform(document["mask_transform"], "mask_transform")
    valid_region = _GATE.flag(document["valid_region_updated"], "valid_region_updated")
    fov = _GATE.flag(document["field_of_view_updated"], "field_of_view_updated")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons]
    if mask != rgb:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if depth != rgb:
        rejected.append(DEPTH_TOKEN)
        reasons.append("depth remained in source coordinates while RGB was stabilized")
    if not valid_region or not fov:
        rejected.append(REGION_TOKEN)
        reasons.append("valid region and field of view were not both updated")
    if NEGATIVE_TOKEN not in rejected and DEPTH_TOKEN not in rejected and REGION_TOKEN not in rejected:
        reasons.append("rgb, depth, and mask share one transform and the crop evidence was updated")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("shared stabilization geometry retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
