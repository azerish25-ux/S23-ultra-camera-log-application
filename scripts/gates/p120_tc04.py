"""TC-P120-04 Interpolation occlusion artifact.

Host fixture. Low confidence or unbounded occlusion artifacts must fall back.
Synthesized samples stay disclosed. Calling interpolated frames native sensor
samples is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-04"
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
    "combinationPassed",
    "report",
    "confidence",
    "confidenceFloor",
    "occlusionPresent",
    "artifactScore",
    "artifactBound",
    "fallbackApplied",
    "labelledNative",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    confidence = _CORE.require_number(payload["confidence"], "confidence")
    floor = _CORE.require_number(payload["confidenceFloor"], "confidenceFloor")
    artifact = _CORE.require_number(payload["artifactScore"], "artifactScore")
    bound = _CORE.require_number(payload["artifactBound"], "artifactBound")
    for flag in ("occlusionPresent", "fallbackApplied", "labelledNative"):
        _CORE.require(type(payload[flag]) is bool, flag + " must be a bool")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    if payload["labelledNative"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("defectOrigin=flow")
    low_confidence = confidence < floor
    unbounded = payload["occlusionPresent"] and artifact > bound
    if (low_confidence or unbounded) and not payload["fallbackApplied"]:
        if low_confidence:
            rejected.append(LOW_CONFIDENCE)
        if unbounded:
            rejected.append(UNBOUNDED)
        reasons.append("low-confidence or unbounded occlusion requires fallback")
        reasons.append("defectOrigin=flow")
    elif payload["fallbackApplied"]:
        reasons.append("fallback keeps estimated samples disclosed")
    else:
        reasons.append("occlusion artifacts are inside the confidence bound")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
