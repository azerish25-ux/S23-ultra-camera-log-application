"""TC-P115-04 Interpolation occlusion artifact.

Host fixture. Synthesized frames stay marked in provenance. Low occlusion
confidence falls back or is bounded. Calling an interpolated frame a native
sensor sample is rejected.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P115-04"
NAME = "Interpolation occlusion artifact"
INTERVENTION = "Use crossing objects and newly revealed surfaces during generated intermediate samples."
EXPECTED = "Bound artifacts or fall back under confidence policy while marking synthesized frames in provenance."
NEGATIVE = "Calling interpolated frames native sensor samples must fail."
REPEAT = "Repeat reflective objects, repetitive patterns, and thin fast structures."
ORIGINS = ("sensor", "synthesized")
POLICIES = ("fallback", "bounded", "integrate-anyway")
REPEATS = ("reflective", "repetitive-pattern", "thin-fast")
FRAME_KEYS = ("origin", "markedSynthesized", "occlusionConfidence")
PAYLOAD_KEYS = ("evidenceId", "frames", "policy", "confidenceFloor", "repeat")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject native labels on synthesized frames and unbounded occlusion."""
    evidence, frames, policy, floor, repeat = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {repeat}", f"policy {policy}"]
    synthesized = [frame for frame in frames if frame["origin"] == "synthesized"]
    if any(not frame["markedSynthesized"] for frame in synthesized):
        rejected.append("interpolated-called-native")
        reasons.append(NEGATIVE)
    if synthesized and policy == "integrate-anyway":
        if "interpolated-called-native" not in rejected:
            rejected.append("synthesized-integrated-as-native")
        reasons.append("synthesized frames were not integrated as native samples")
    if any(frame["occlusionConfidence"] < floor for frame in frames) and policy == "integrate-anyway":
        rejected.append("occlusion-unbounded")
        reasons.append("low occlusion confidence was not bounded or sent to fallback")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("synthesized provenance stays marked and low confidence is bounded")
    preserved = [
        evidence,
        policy,
        [
            {
                "origin": frame["origin"],
                "markedSynthesized": frame["markedSynthesized"],
                "occlusionConfidence": frame["occlusionConfidence"],
            }
            for frame in frames
        ],
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    policy = payload["policy"]
    if policy not in POLICIES:
        raise ValueError("policy is unsupported")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    floor = _finite(payload["confidenceFloor"], "confidenceFloor")
    if floor < 0.0 or floor > 1.0:
        raise ValueError("confidenceFloor is outside 0..1")
    frames = payload["frames"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a non-empty list")
    parsed = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or set(frame) != set(FRAME_KEYS):
            raise ValueError(f"frame {index} keys are invalid")
        origin = frame["origin"]
        if origin not in ORIGINS:
            raise ValueError(f"frame {index} origin is unsupported")
        marked = frame["markedSynthesized"]
        if type(marked) is not bool:
            raise ValueError(f"frame {index} markedSynthesized must be a bool")
        if origin == "sensor" and marked:
            raise ValueError(f"frame {index} sensor sample cannot be marked synthesized")
        confidence = _finite(frame["occlusionConfidence"], f"frame {index} occlusionConfidence")
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError(f"frame {index} occlusionConfidence is outside 0..1")
        parsed.append(
            {"origin": origin, "markedSynthesized": marked, "occlusionConfidence": confidence}
        )
    return evidence, parsed, policy, floor, repeat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or evidence_missing(result):
        raise ValueError("result contract drifted")
    return result


def evidence_missing(result: dict) -> bool:
    return not result["reasons"] or result["preservedResults"][0] not in result["preservedResults"]
