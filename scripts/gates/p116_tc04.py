"""TC-P116-04 Interpolation occlusion artifact.

Host fixture. Low confidence or unbounded occlusion artifacts must fall back.
Synthesized frames are marked origin=estimated. Calling them native captured
samples is a hidden hallucination.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-04"
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
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "confidence",
    "confidenceFloor",
    "occlusionPresent",
    "artifactScore",
    "artifactBound",
    "fallbackApplied",
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
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    if _CORE.HIDDEN_HALLUCINATION in rejected:
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
