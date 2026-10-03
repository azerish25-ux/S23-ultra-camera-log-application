"""TC-P016-06 geometry mismatch on the first slice.

Source and output sizes stay distinct for a crop, downsample, or upscale.
Container dimensions must not certify source resolution. Orientation metadata
does not turn a transformed frame into native acquisition. This host case
does not qualify a physical S23.
"""

from __future__ import annotations

CASE_ID = "TC-P016-06"
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
_CONTAINER_CLAIM = "container-as-source"
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Label geometry changes and refuse container-as-source certification."""
    source, output, container, transform, orientation = _payload(payload)
    source_text = _size_text(*source)
    output_text = _size_text(*output)
    reasons = [f"transform {transform}", f"orientation {orientation}"]
    rejected: list[str] = []
    if container != source:
        rejected.append(_CONTAINER_CLAIM)
        reasons.append("container dimensions must not certify source resolution")

    if source != output:
        decision = "transformed"
        preserved = [f"source:{source_text}", f"output:{output_text}"]
        reasons.append("source and output geometry are preserved separately")
        if decision == "native" or any("native" in item for item in reasons):
            raise ValueError("transformed geometry must not be native")
    elif source == output == container and transform == "none":
        decision = "native"
        preserved = [source_text]
        reasons.append(f"source output and container match at {source_text}")
    else:
        decision = "withheld"
        preserved = [source_text]
        reasons.append("container dimensions do not certify the matching source size")

    if source != output and decision == "native":
        raise ValueError("source and output mismatch must not be native")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P016-06 must not yield qualified or allowed")
    if source_text not in "".join(preserved):
        raise ValueError("source size must be preserved")
    return _finish(decision, reasons, rejected, preserved, [])


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError(f"{CASE_ID} must not decide qualified or allowed")
    kept = list(preserved)
    for token in _ORACLE_PRESERVED:
        if token not in kept:
            kept.append(token)
    questions = list(open_questions)
    if _NOT_ENDURANCE not in questions:
        questions.append(_NOT_ENDURANCE)
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": kept,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


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
        raise ValueError("transform must be none, center_crop, downsample, or upscale")
    orientation = payload["orientationDegrees"]
    if type(orientation) is not int:
        raise ValueError("orientationDegrees must be an int")
    _consistent(source, output, transform)
    return source, output, container, transform, orientation


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
