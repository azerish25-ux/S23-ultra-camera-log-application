"""TC-P119-03 Temporal integration energy.

Host fixture. Integrate known synthetic motion in the linear domain and compare
it with an independent oracle. Display-encoded averages and unnormalized
weights are rejected. Negative weights and out-of-window frames are not dropped.
Guidance that is not bound to a measured limit is rejected as well.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P119-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
REPEATS = ("constant-velocity", "acceleration", "partial-exposure-boundary")
TOLERANCE = 1e-9
PAYLOAD_KEYS = (
    "evidenceId",
    "frames",
    "weights",
    "window",
    "oracle",
    "domain",
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
    """Weighted sum. Every weight is applied. Nothing is dropped or renormalized."""
    width = len(frames[0])
    sample = [0.0] * width
    for weight, frame in zip(weights, frames):
        for index, value in enumerate(frame):
            sample[index] += weight * value
    return sample


def evaluate(payload: dict) -> dict:
    """Integrate the stack, then reject guidance the measured mode cannot support."""
    fields = _payload(payload)
    frames = fields["frames"]
    weights = fields["weights"]
    start, end = fields["window"]
    sample = integrate_frames(frames, weights)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["domain"] != "linear":
        rejected.append("display-encoded-average")
        reasons.append(NEGATIVE)
    if any(weight < 0.0 for weight in weights):
        rejected.append("negative-weight")
        reasons.append("negative weight rejected and not dropped")
    if abs(sum(weights) - 1.0) > TOLERANCE:
        rejected.append("unnormalized-temporal-weights")
        reasons.append(NEGATIVE)
    outside = [index for index, weight in enumerate(weights) if weight != 0.0 and (index < start or index > end)]
    if outside:
        rejected.append("frame-outside-shutter-window")
        reasons.append("frame outside the shutter window stayed in the sum at " + ",".join(str(i) for i in outside))
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
        reasons.append("linear exposure integral retained")
    preserved = [fields["evidenceId"], NAME, list(weights), [start, end], list(sample)]
    preserved.extend(judged["preservedResults"])
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions, fields["evidenceId"], weights, [start, end])


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
        parsed.append([_finite(item, f"frame {index} sample {sample}") for sample, item in enumerate(frame)])
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
    domain = payload["domain"]
    if domain not in {"linear", "display"}:
        raise ValueError("domain must be linear or display")
    frames = _frames(payload["frames"])
    weights = payload["weights"]
    if not isinstance(weights, list) or len(weights) != len(frames):
        raise ValueError("weights must match the frame count")
    parsed_weights = [_finite(item, f"weight {index}") for index, item in enumerate(weights)]
    window = payload["window"]
    if not isinstance(window, list) or len(window) != 2:
        raise ValueError("window must be an index range")
    start, end = window
    if type(start) is not int or type(end) is not int:
        raise ValueError("window bounds must be integers")
    if not (0 <= start <= end < len(frames)):
        raise ValueError("window is outside the frame stack")
    oracle = payload["oracle"]
    if not isinstance(oracle, list) or len(oracle) != len(frames[0]):
        raise ValueError("oracle must match the sample length")
    parsed_oracle = [_finite(item, f"oracle {index}") for index, item in enumerate(oracle)]
    return {
        "evidenceId": evidence,
        "frames": frames,
        "weights": parsed_weights,
        "window": (start, end),
        "oracle": parsed_oracle,
        "domain": domain,
        "repeat": repeat,
        "selectedLimitId": payload["selectedLimitId"],
        "measuredLimits": payload["measuredLimits"],
        "guidance": payload["guidance"],
    }


def _result(decision, reasons, rejected, preserved, questions, evidence, weights, window) -> dict:
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
    if tuple(result) != RESULT_KEYS or decision in {"qualified", "allowed"}:
        raise ValueError("result contract drifted")
    if evidence not in result["preservedResults"] or weights not in result["preservedResults"]:
        raise ValueError("weight list was not retained")
    if window not in result["preservedResults"]:
        raise ValueError("window was not retained")
    return result
