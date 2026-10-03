"""TC-P015-06 geometry mismatch.

Source and output sizes stay distinct when a crop, downsample, upscale, or
orientation change is applied. Container dimensions must not certify source
resolution. Transformations are labelled. Native acquisition is not claimed.
The decision is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P015-06"
INTERVENTION = (
    "Provide output dimensions that differ from the source stream because of crop, reduction, or enlargement."
)
EXPECTED = (
    "Preserve source and output geometry separately and label transformations "
    "rather than claiming native acquisition."
)
NEGATIVE = "Container dimensions alone must not certify source resolution."
REPEAT = "Repeat with a center crop, linear downsample, upscaled output, and orientation metadata."
_PAYLOAD_KEYS = (
    "sourceWidth",
    "sourceHeight",
    "outputWidth",
    "outputHeight",
    "transform",
    "orientationDegrees",
    "containerWidth",
    "containerHeight",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TRANSFORMS = ("none", "center_crop", "linear_downsample", "upscale")
_ORIENTATIONS = (0, 90, 180, 270)
_CONTAINER_CLAIM = "container-as-source"
_FORBIDDEN = {"qualified", "allowed", "native"}


def evaluate(payload: dict) -> dict:
    """Label geometry changes and refuse container-as-source certification."""
    source, output, container, transform, orientation = _payload(payload)
    source_text = _size_text(*source)
    output_text = _size_text(*output)
    container_text = _size_text(*container)
    reasons = [f"transform {transform}", f"orientation {orientation}"]
    rejected: list[str] = []
    preserved = [f"source:{source_text}", f"output:{output_text}"]
    if orientation != 0:
        preserved.append(f"orientation:{orientation}")
        reasons.append(f"orientation metadata {orientation}")
    labelled = transform != "none" or orientation != 0 or source != output
    if container != source:
        rejected.append(_CONTAINER_CLAIM)
        reasons.append("container dimensions must not certify source resolution")
        reasons.append(f"container {container_text} is not source {source_text}")
    if labelled:
        decision = "transformed"
        reasons.append("source and output geometry are preserved separately")
        reasons.append("transformation is labelled rather than claimed as native acquisition")
    elif container != source:
        decision = "withheld"
        reasons.append("matching source and output are not certified by container dimensions")
    else:
        decision = "untransformed"
        reasons.append(f"source output and container match at {source_text}")
        reasons.append("untransformed is not a native-acquisition claim")
    if "native acquisition" in " ".join(reasons) and decision == "native":
        raise ValueError("transformed geometry must not be claimed as native acquisition")
    if source != output and decision == "untransformed":
        raise ValueError("source and output mismatch must be labelled")
    if decision in _FORBIDDEN:
        raise ValueError("TC-P015-06 must not yield qualified, allowed, or native")
    if not any(item.startswith("source:") for item in preserved):
        raise ValueError("source size must be preserved")
    if not any(item.startswith("output:") for item in preserved):
        raise ValueError("output size must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], str, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source = (
        _positive_int(payload["sourceWidth"], "sourceWidth"),
        _positive_int(payload["sourceHeight"], "sourceHeight"),
    )
    output = (
        _positive_int(payload["outputWidth"], "outputWidth"),
        _positive_int(payload["outputHeight"], "outputHeight"),
    )
    container = (
        _positive_int(payload["containerWidth"], "containerWidth"),
        _positive_int(payload["containerHeight"], "containerHeight"),
    )
    transform = payload["transform"]
    if transform not in _TRANSFORMS:
        raise ValueError("transform is not a known geometry label")
    orientation = payload["orientationDegrees"]
    if type(orientation) is not int or orientation not in _ORIENTATIONS:
        raise ValueError("orientationDegrees must be 0, 90, 180, or 270")
    if transform == "none" and source != output and orientation == 0:
        raise ValueError("a size change requires a transformation label")
    if transform != "none" and source == output:
        raise ValueError("a named size transform requires source and output to differ")
    if transform == "upscale" and (output[0] < source[0] or output[1] < source[1]):
        raise ValueError("upscale output must not be smaller than the source")
    if transform in {"center_crop", "linear_downsample"} and (
        output[0] > source[0] or output[1] > source[1]
    ):
        raise ValueError("crop or downsample output must not exceed the source")
    return source, output, container, transform, orientation


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _size_text(width: int, height: int) -> str:
    return f"{width}x{height}"


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in _FORBIDDEN or not reasons:
        raise ValueError("invalid decision or reasons")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
