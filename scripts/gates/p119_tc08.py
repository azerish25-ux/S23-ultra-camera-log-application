"""TC-P119-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film
finishing are checked together. A passing integral does not replace that
combined regression. The motion integral is the weighted frame sum.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P119-08"
NAME = "Combined temporal effects"
INTERVENTION = (
    "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
)
EXPECTED = "Preserve shared geometry and timing without doubled edges, unstable masks, or unexplained cadence changes."
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
REPEATS = ("scene-cut", "chunk-resume", "low-confidence-motion")
TOLERANCE = 1e-9
BOOL_KEYS = (
    "stabilization",
    "virtualFocus",
    "motionIntegration",
    "filmFinishing",
    "combinedRun",
    "individualPassesOnly",
    "doubledEdges",
    "unstableMasks",
    "cadenceChanged",
    "cadenceExplained",
    "sharedGeometry",
)
PAYLOAD_KEYS = (
    "evidenceId",
    *BOOL_KEYS,
    "frames",
    "weights",
    "window",
    "oracle",
    "repeat",
    "selectedLimitId",
    "measuredLimits",
    "guidance",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        path = Path(__file__).resolve().parent / "p119_add_practical_cinematographic_guidance.py"
        spec = importlib.util.spec_from_file_location("p119_add_practical_cinematographic_guidance", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CORE = module
    return _CORE


def integrate_frames(frames: list[list[float]], weights: list[float]) -> list[float]:
    width = len(frames[0])
    sample = [0.0] * width
    for weight, frame in zip(weights, frames):
        for index, value in enumerate(frame):
            sample[index] += weight * value
    return sample


def evaluate(payload: dict) -> dict:
    """Reject separate effect passes. Keep the combined exposure integral."""
    fields = _payload(payload)
    frames = fields["frames"]
    weights = fields["weights"]
    start, end = fields["window"]
    sample = integrate_frames(frames, weights)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["individualPassesOnly"] or not fields["combinedRun"]:
        rejected.append("independent-effects-replace-combined-regression")
        reasons.append(NEGATIVE)
    if not (
        fields["stabilization"]
        and fields["virtualFocus"]
        and fields["motionIntegration"]
        and fields["filmFinishing"]
    ):
        rejected.append("missing-combined-effect")
        reasons.append("stabilization, virtual focus, motion integration, and film finishing are all required")
    if fields["doubledEdges"]:
        rejected.append("doubled-edges")
    if fields["unstableMasks"]:
        rejected.append("unstable-masks")
    if not fields["sharedGeometry"]:
        rejected.append("geometry-not-shared")
    if fields["cadenceChanged"] and not fields["cadenceExplained"]:
        rejected.append("unexplained-cadence-change")
    if any(weight < 0.0 for weight in weights):
        rejected.append("negative-weight")
    if abs(sum(weights) - 1.0) > TOLERANCE:
        rejected.append("unnormalized-temporal-weights")
    outside = [index for index, weight in enumerate(weights) if weight != 0.0 and (index < start or index > end)]
    if outside:
        rejected.append("frame-outside-shutter-window")
    if any(abs(sample[index] - fields["oracle"][index]) > TOLERANCE for index in range(len(sample))):
        rejected.append("oracle-mismatch")
        reasons.append("integrated sample differs from the independent oracle by more than 1e-9")
    judged = _core().judge_guidance(fields["measuredLimits"], fields["selectedLimitId"], fields["guidance"])
    for claim in judged["rejectedClaims"]:
        if claim not in rejected:
            rejected.append(claim)
    reasons.extend(judged["reasons"])
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("combined regression retained the linear exposure integral")
    preserved = [fields["evidenceId"], NAME, list(weights), [start, end], list(sample)]
    preserved.extend(judged["preservedResults"])
    questions = ["physical S23 capture was not run", REPEAT]
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or decision not in {"recorded", "rejected"}:
        raise ValueError("result contract drifted")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    if fields["evidenceId"] not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    if weights not in result["preservedResults"] or [start, end] not in result["preservedResults"]:
        raise ValueError("weight list or window was not retained")
    return result


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _frames(frames: object) -> list[list[float]]:
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a non-empty list")
    parsed: list[list[float]] = []
    width: int | None = None
    for index, frame in enumerate(frames):
        if not isinstance(frame, list) or not frame:
            raise ValueError(f"frame {index} must be a non-empty list")
        if width is None:
            width = len(frame)
        elif len(frame) != width:
            raise ValueError("frames must share one length")
        parsed.append([_finite(item, f"frame {index}") for item in frame])
    return parsed


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    fields: dict = {
        "evidenceId": evidence,
        "repeat": repeat,
        "selectedLimitId": payload["selectedLimitId"],
        "measuredLimits": payload["measuredLimits"],
        "guidance": payload["guidance"],
    }
    for key in BOOL_KEYS:
        if type(payload[key]) is not bool:
            raise ValueError(f"{key} must be a bool")
        fields[key] = payload[key]
    frames = _frames(payload["frames"])
    weights = payload["weights"]
    if not isinstance(weights, list) or len(weights) != len(frames):
        raise ValueError("weights must match the frame count")
    window = payload["window"]
    if not isinstance(window, list) or len(window) != 2:
        raise ValueError("window must be an index range")
    start, end = window
    if type(start) is not int or type(end) is not int or not (0 <= start <= end < len(frames)):
        raise ValueError("window is outside the frame stack")
    oracle = payload["oracle"]
    if not isinstance(oracle, list) or len(oracle) != len(frames[0]):
        raise ValueError("oracle must match the sample length")
    fields["frames"] = frames
    fields["weights"] = [_finite(item, "weight") for item in weights]
    fields["window"] = (start, end)
    fields["oracle"] = [_finite(item, "oracle") for item in oracle]
    return fields
