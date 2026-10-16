"""TC-P113-04 Interpolation occlusion artifact.

Synthesized frames stay marked in provenance. Low confidence falls back.
Calling an interpolated frame a native sensor sample is rejected.
"""

from __future__ import annotations

import math
import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-04"
NAME = "Interpolation occlusion artifact"
INTERVENTION = (
    "Use crossing objects and newly revealed surfaces during generated intermediate samples."
)
EXPECTED = (
    "Bound artifacts or fall back under confidence policy while marking synthesized "
    "frames in provenance."
)
NEGATIVE = "Calling interpolated frames native sensor samples must fail."
REPEAT = "Repeat reflective objects, repetitive patterns, and thin fast structures."
REPEATS = ("reflective", "repetitive-pattern", "thin-fast")
NEGATIVE_TOKEN = "interpolated-frame-called-native"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc04",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "confidence",
    "confidenceThreshold",
    "synthesized",
    "claimedNativeSensorSample",
    "provenanceMarksSynthesized",
    "crossingObjects",
    "interpolationApplied",
    "disocclusionBounded",
    "shutterAngleDegrees",
    "fps",
    "sensorConfirmed",
    "measurementId",
    "syntheticIntegration",
)


def _unit(value: object, name: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return number


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 interpolation repeat")
    confidence = _unit(payload["confidence"], "confidence")
    threshold = _unit(payload["confidenceThreshold"], "confidenceThreshold")
    synthesized = _bool(payload["synthesized"], "synthesized")
    native = _bool(payload["claimedNativeSensorSample"], "claimedNativeSensorSample")
    marked = _bool(payload["provenanceMarksSynthesized"], "provenanceMarksSynthesized")
    crossing = _bool(payload["crossingObjects"], "crossingObjects")
    applied = _bool(payload["interpolationApplied"], "interpolationApplied")
    bounded = _bool(payload["disocclusionBounded"], "disocclusionBounded")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    result = _CORE.judge_shutter(
        {
            "evidenceId": payload["evidenceId"],
            "shutterAngleDegrees": payload["shutterAngleDegrees"],
            "fps": payload["fps"],
            "syntheticIntegration": payload["syntheticIntegration"],
            "sensorConfirmed": payload["sensorConfirmed"],
            "measurementId": payload["measurementId"],
            "reportsAngleAsApplied": True,
        },
        CASE_ID,
    )
    extra: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        INTERVENTION,
        EXPECTED,
        f"repeat {repeat}",
        REPEAT,
        f"confidence {confidence} threshold {threshold}",
    ]
    if native:
        extra.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if synthesized and not marked:
        extra.append("synthesized-frame-unmarked")
        reasons.append("synthesized frames must be marked in provenance")
    if confidence < threshold:
        if applied:
            extra.append("unbounded-interpolation")
            reasons.append("low confidence must fall back instead of emitting interpolation")
        else:
            reasons.append("fell back under confidence policy; no interpolated frame was emitted")
    elif crossing and applied and not bounded:
        extra.append("occlusion-unbounded")
        reasons.append("crossing objects require a bounded disocclusion policy")
    else:
        reasons.append("interpolation artifacts stayed inside the confidence policy")
    preserved = list(result["preservedResults"])
    if synthesized:
        preserved.append("provenance:synthesized")
    else:
        preserved.append("provenance:not-synthesized")
    rewritten = _CORE.finish_result(
        result["caseId"],
        result["decision"],
        result["reasons"],
        result["rejectedClaims"],
        preserved,
        result["openQuestions"],
    )
    return _CORE.reject_more(rewritten, extra, reasons)
