"""TC-P011-06 geometry mismatch.

Source and output sizes stay distinct when a crop, downsample, or upscale is
applied. Container dimensions must not certify source resolution. Orientation
metadata is recorded and does not turn a transformed frame into source geometry.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-06"
INTERVENTION = (
    "Provide output dimensions that differ from the source stream because of crop, reduction, or enlargement."
)
EXPECTED = (
    "Preserve source and output geometry separately and label transformations "
    "rather than claiming native acquisition."
)
NEGATIVE = "Container dimensions alone must not certify source resolution."
_PAYLOAD_KEYS = (
    "sourceWidth",
    "sourceHeight",
    "outputWidth",
    "outputHeight",
    "transform",
    "orientationDegrees",
    "containerWidth",
    "containerHeight",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TRANSFORMS = ("none", "center_crop", "downsample", "upscale")
_ORIENTATIONS = (0, 90, 180, 270)
_CONTAINER_CLAIM = "container-as-source"
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Label geometry changes and refuse container-as-source certification."""
    source, output, container, transform, orientation, ae_min, ae_max, requested, timestamps = _payload(
        payload
    )
    source_text = _size_text(*source)
    output_text = _size_text(*output)
    reasons = [f"transform {transform}", f"orientation {orientation}"]
    rejected: list[str] = []
    if container != source:
        rejected.append(_CONTAINER_CLAIM)
        reasons.append("container dimensions must not certify source resolution")
    inventory = [f"ae:{_text(ae_min)}-{_text(ae_max)}", f"requested:{_text(requested)}"]
    if source != output:
        decision = "transformed"
        preserved = [f"source:{source_text}", f"output:{output_text}", *inventory]
        reasons.append("source and output geometry are preserved separately")
        if "native" in decision or any("native" in item for item in reasons):
            raise ValueError("transformed geometry must not be labelled native")
    elif source == output == container and transform == "none":
        decision = "source_matches"
        preserved = [source_text, *inventory]
        reasons.append(f"source output and container match at {source_text}")
        reasons.append("matching container dimensions are not a cadence certificate")
    else:
        decision = "withheld"
        preserved = [source_text, *inventory]
        reasons.append("container dimensions do not certify the matching source size")
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify fixed cadence")
    if source != output and decision == "source_matches":
        raise ValueError("source and output mismatch must not match as source")
    if source_text not in "".join(preserved):
        raise ValueError("source size must be preserved")
    open_questions = []
    if orientation != 0:
        open_questions.append("orientation metadata is not a source-size change")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object):
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
        raise ValueError("transform must be none, center_crop, downsample, or upscale")
    orientation = payload["orientationDegrees"]
    if type(orientation) is not int or orientation not in _ORIENTATIONS:
        raise ValueError("orientationDegrees must be 0, 90, 180, or 270")
    timestamps = payload["containerTimestampsAssigned"]
    if type(timestamps) is not bool:
        raise ValueError("containerTimestampsAssigned must be a bool")
    _consistent(source, output, transform)
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return source, output, container, transform, orientation, ae_min, ae_max, requested, timestamps


def _consistent(source: tuple[int, int], output: tuple[int, int], transform: str) -> None:
    same = source == output
    if transform == "none":
        if not same:
            raise ValueError("transform none requires matching source and output dimensions")
        return
    if same:
        raise ValueError("a named transform requires source and output dimensions to differ")
    sw, sh = source
    ow, oh = output
    if transform in {"center_crop", "downsample"}:
        if ow > sw or oh > sh:
            raise ValueError(f"{transform} cannot enlarge a dimension")
        return
    if ow < sw or oh < sh:
        raise ValueError("upscale cannot shrink a dimension")


def _positive_int(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _size_text(width: int, height: int) -> str:
    return f"{width}x{height}"


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-06 must not yield qualified, allowed, or native_fixed_24")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
