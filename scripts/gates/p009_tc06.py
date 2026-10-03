"""TC-P009-06 camera-route inventory: geometry mismatch.

Source and output sizes stay distinct. Crop, downsample, and upscale are
labeled, orientation is echoed without flipping a native-acquisition claim,
and container dimensions are never treated as the source resolution.
"""

from __future__ import annotations

CASE_ID = "TC-P009-06"
_FIELDS = (
    "sourceWidth",
    "sourceHeight",
    "outputWidth",
    "outputHeight",
    "transform",
    "orientationDegrees",
    "containerWidth",
    "containerHeight",
)
_TRANSFORMS = ("none", "center_crop", "downsample", "upscale")
_TRANSFORM_LABELS = {
    "none": "transform none",
    "center_crop": "center crop",
    "downsample": "linear downsample",
    "upscale": "upscaled output",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Separate source geometry from output and container sizes."""
    data = _payload(payload)
    source_w = data["sourceWidth"]
    source_h = data["sourceHeight"]
    output_w = data["outputWidth"]
    output_h = data["outputHeight"]
    transform = data["transform"]
    orientation = data["orientationDegrees"]
    container_w = data["containerWidth"]
    container_h = data["containerHeight"]

    source_differs = source_w != output_w or source_h != output_h
    container_differs = container_w != source_w or container_h != source_h
    # Orientation is metadata only. It must not swap width/height or native.
    reasons = [_TRANSFORM_LABELS[transform], f"orientation {orientation}"]
    rejected: list[str] = []
    if container_differs:
        rejected.append("container-as-source")
        reasons.append("container dimensions are not source resolution")

    if source_differs:
        decision = "transformed"
        reasons.append("source and output geometry differ")
    elif transform == "none" and not container_differs:
        decision = "native"
        reasons.append("native acquisition")
    elif transform != "none":
        decision = "transformed"
        reasons.append("labeled transform is not native acquisition")
    else:
        decision = "withheld"
        reasons.append("container match is required for native acquisition")

    if source_differs and decision == "native":
        raise ValueError("differing source and output must not be native")
    if decision == "allowed":
        raise ValueError("TC-P009-06 must not decide allowed")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [f"source:{source_w}x{source_h}", f"output:{output_w}x{output_h}"],
        "openQuestions": [],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_FIELDS):
        raise ValueError("invalid payload keys")
    for key in (
        "sourceWidth",
        "sourceHeight",
        "outputWidth",
        "outputHeight",
        "containerWidth",
        "containerHeight",
    ):
        _positive_int(payload[key], key)
    if payload["transform"] not in _TRANSFORMS:
        raise ValueError("transform must be none, center_crop, downsample, or upscale")
    _int(payload["orientationDegrees"], "orientationDegrees")
    return payload


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an int")
    return value
