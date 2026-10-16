"""TC-P118-04 Interpolation occlusion artifact.

Host fixture. Low confidence or an unbounded occlusion must fall back.
Synthesized samples stay origin=estimated. Calling them captured sensor samples
is rejected. Unknown readout does not shift rows.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P118-04"
NAME = "Interpolation occlusion artifact"
INTERVENTION = "Use crossing objects and newly revealed surfaces during generated intermediate samples."
EXPECTED = (
    "Bound artifacts or fall back under confidence policy while marking synthesized frames in provenance."
)
NEGATIVE = "Calling interpolated frames native sensor samples must fail."
REPEAT = "Repeat reflective objects, repetitive patterns, and thin fast structures."
NEGATIVE_TOKEN = "interpolated-frames-called-native-sensor-samples"
LOW_CONFIDENCE = "low-confidence-without-fallback"
UNBOUNDED = "occlusion-artifact-unbounded"
SAMPLE_KEYS = {"time", "origin"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "confidence",
    "confidenceFloor",
    "occlusionPresent",
    "artifactScore",
    "artifactBound",
    "fallbackApplied",
    "samples",
    "readoutSecondsPerRow",
    "readoutSource",
    "cameraVelocityY",
    "warpLabel",
    "claimsGlobalShutterRestored",
    "rows",
)

_SPEC = importlib.util.spec_from_file_location(
    "p118_investigate_rolling_shutter_correction_conservatively",
    Path(__file__).resolve().parent / "p118_investigate_rolling_shutter_correction_conservatively.py",
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


def _samples(samples) -> list[dict]:
    if not isinstance(samples, list) or not samples:
        raise ValueError("samples must be a non-empty list")
    parsed = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or set(sample) != SAMPLE_KEYS:
            raise ValueError(f"samples[{index}] keys are invalid")
        origin = sample["origin"]
        if origin not in {"estimated", "captured"}:
            raise ValueError(f"samples[{index}].origin is unsupported")
        parsed.append({"time": _number(sample["time"], f"samples[{index}].time"), "origin": origin})
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    confidence = _number(payload["confidence"], "confidence")
    floor = _number(payload["confidenceFloor"], "confidenceFloor")
    artifact = _number(payload["artifactScore"], "artifactScore")
    bound = _number(payload["artifactBound"], "artifactBound")
    for flag in ("occlusionPresent", "fallbackApplied"):
        if type(payload[flag]) is not bool:
            raise ValueError(flag + " must be a bool")
    samples = _samples(payload["samples"])
    plan = _CORE.plan_correction(
        payload["readoutSecondsPerRow"],
        payload["readoutSource"],
        payload["cameraVelocityY"],
        payload["warpLabel"],
        payload["claimsGlobalShutterRestored"],
        payload["rows"],
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if any(sample["origin"] == "captured" for sample in samples):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    low_confidence = confidence < floor
    unbounded = payload["occlusionPresent"] and artifact > bound
    if (low_confidence or unbounded) and not payload["fallbackApplied"]:
        if low_confidence:
            rejected.append(LOW_CONFIDENCE)
        if unbounded:
            rejected.append(UNBOUNDED)
        reasons.append("low-confidence or unbounded occlusion requires fallback")
    elif payload["fallbackApplied"]:
        reasons.append("fallback retains origin=estimated")
    else:
        reasons.append("occlusion artifacts are inside the confidence bound")
    reasons.extend(plan["reasons"])
    rejected.extend(plan["rejectedClaims"])
    preserved = [
        evidence,
        plan["reasons"][0],
        plan["reasons"][1],
        plan["originalY"],
        plan["yPrime"],
        plan["shiftPixels"],
        [sample["origin"] for sample in samples],
    ]
    decision = "rejected" if rejected else "recorded"
    return _CORE.case_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
