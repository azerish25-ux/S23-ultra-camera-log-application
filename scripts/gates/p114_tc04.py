"""TC-P114-04 Interpolation occlusion artifact.

Host fixture. Synthesized samples are estimated frames, never captured ones.
Low confidence without fallback is rejected. Hidden estimated frames are a
hallucination under the disclosure rule.
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

CASE_ID = "TC-P114-04"
NAME = "Interpolation occlusion artifact"
INTERVENTION = "Use crossing objects and newly revealed surfaces during generated intermediate samples."
EXPECTED = "Bound artifacts or fall back under confidence policy while marking synthesized frames in provenance."
NEGATIVE = "Calling interpolated frames native sensor samples must fail."
REPEAT = "Repeat reflective objects, repetitive patterns, and thin fast structures."
NEGATIVE_TOKEN = "interpolated-frames-called-native-sensor-samples"
CONFIDENCE_TOKEN = "low-confidence-without-fallback"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "confidence_floor",
    "fell_back",
)


def _confidence(value: object, name: str) -> float:
    number = _GATE.finite_number(value, name)
    _GATE.require(0.0 <= number <= 1.0, name + " must be between 0 and 1")
    return number


def evaluate(payload: dict) -> dict:
    document = _GATE.exact_keys(payload, set(PAYLOAD_KEYS), "payload")
    evidence = _GATE.evidence_id(document["evidenceId"])
    repeat = _GATE.repeat_text(document["repeat"])
    frames = _GATE.check_extra(
        _GATE.parse_frames(document["frames"], ("synthesized", "confidence")),
        {"synthesized": lambda value, name: _GATE.flag(value, name), "confidence": _confidence},
    )
    angle = _GATE.optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = _GATE.optional_positive(document["fps"], "fps")
    contains_estimated = _GATE.flag(document["contains_estimated"], "contains_estimated")
    disclosed = _GATE.flag(document["disclosed"], "disclosed")
    labelled = _GATE.flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    floor = _confidence(document["confidence_floor"], "confidence_floor")
    fell_back = _GATE.flag(document["fell_back"], "fell_back")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons]
    native_lie = False
    low_confidence = False
    for frame in frames:
        if frame["synthesized"] and frame["origin"] != "estimated":
            native_lie = True
        if frame["origin"] == "estimated" and not frame["synthesized"]:
            raise ValueError("estimated frame must be marked synthesized")
        if frame["synthesized"] and frame["confidence"] < floor and not fell_back:
            low_confidence = True
    if native_lie:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        reasons.append("synthesized frames are marked estimated in provenance")
    if low_confidence:
        rejected.append(CONFIDENCE_TOKEN)
        reasons.append("low-confidence interpolation did not fall back")
    elif fell_back:
        reasons.append("low-confidence interval fell back under confidence policy")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("provenance marks retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
