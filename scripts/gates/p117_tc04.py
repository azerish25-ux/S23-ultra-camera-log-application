"""TC-P117-04 Interpolation occlusion artifact.

Host fixture. Low confidence or unbounded occlusion artifacts must fall back.
Synthesized frames stay origin=estimated. Calling them captured sensor samples
fails. Stabilization geometry uses the phase crop contract.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-04"
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
FRAME_KEYS = ("synthesized", "origin")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "confidence",
    "confidenceFloor",
    "occlusionPresent",
    "artifactScore",
    "artifactBound",
    "fallbackApplied",
    "frames",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    confidence = _CORE.require_number(payload["confidence"], "confidence")
    floor = _CORE.require_number(payload["confidenceFloor"], "confidenceFloor")
    artifact = _CORE.require_number(payload["artifactScore"], "artifactScore")
    bound = _CORE.require_number(payload["artifactBound"], "artifactBound")
    if not 0.0 <= confidence <= 1.0 or not 0.0 <= floor <= 1.0:
        raise ValueError("confidence must be in [0, 1]")
    if artifact < 0.0 or bound < 0.0:
        raise ValueError("artifact scores must be non-negative")
    for name in ("occlusionPresent", "fallbackApplied"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
    frames_in = payload["frames"]
    if not isinstance(frames_in, list) or not frames_in:
        raise ValueError("frames must be a non-empty list")
    frames = []
    for index, item in enumerate(frames_in):
        obj = _CORE.require_object(item, f"frames[{index}]", FRAME_KEYS)
        if type(obj["synthesized"]) is not bool:
            raise ValueError(f"frames[{index}].synthesized must be a bool")
        if obj["origin"] not in {"estimated", "captured"}:
            raise ValueError(f"frames[{index}].origin must be estimated or captured")
        frames.append({"synthesized": obj["synthesized"], "origin": obj["origin"]})
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    native = False
    tags = []
    for index, frame in enumerate(frames):
        tag = (
            f"frame[{index}] origin={frame['origin']} synthesized="
            + ("yes" if frame["synthesized"] else "no")
        )
        tags.append(tag)
        reasons.append(tag)
        if frame["synthesized"] and frame["origin"] != "estimated":
            native = True
    if native:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    low = confidence < floor
    unbounded = payload["occlusionPresent"] and artifact > bound + _CORE.ABSOLUTE_TOLERANCE
    if low and not payload["fallbackApplied"]:
        rejected.append(LOW_CONFIDENCE)
        reasons.append("confidence is below the floor and no fallback was applied")
    if unbounded and not payload["fallbackApplied"]:
        rejected.append(UNBOUNDED)
        reasons.append("occlusion artifact exceeds the bound and no fallback was applied")
    if (low or unbounded) and payload["fallbackApplied"] and not native:
        reasons.append("low-confidence occlusion fell back and synthesized frames stay estimated")
    preserved = [evidence]
    preserved.extend(tags)
    preserved.extend(analysis["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    return _CORE.seal_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
