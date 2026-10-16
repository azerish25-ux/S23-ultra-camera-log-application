#!/usr/bin/env python3
"""P115 Build a temporal integration reference.

Host fixture only. Integrate a stack of numeric frames over a declared shutter
window. This module does not probe a device, does not qualify a physical S23,
and does not execute the TC-P115-01 through TC-P115-08 modules.

sample[i] = sum(weight[k] * frame[k][i])

Weights must sum to 1. A negative weight is rejected and is not dropped.
A non-zero weight whose frame index lies outside the inclusive shutter window
is rejected and is not dropped. The retained sample is that same weighted sum.
An independent oracle that differs by more than 1e-9 is rejected.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P115"
TITLE = "Build a temporal integration reference"
WORKSTREAM = 15
DEPENDENCIES = ("P114",)
GOAL = "Create a controlled motion-blur oracle using known motion and synthetic intermediate samples."
METHOD = (
    "Integrate radiance over a declared exposure window with normalized weights. "
    "Use known moving shapes before optical-flow interpolation. Keep blur in the "
    "appropriate linear domain and test how occlusion changes visible contributions "
    "during the exposure."
)
FIXTURE = "A bright disk moving at constant velocity across a dark background with known subframe positions."
ORACLE = (
    "The integrated trail agrees with the reference exposure window and preserves "
    "total energy under the defined boundary policy."
)
MUTANT = "Average display-encoded frames without accounting for transfer or exposure weights."
DELIVERABLE = "Temporal integration reference and analytic motion fixtures"
TOLERANCE = 1e-9
BOUNDARY_POLICY = "nonzero-weight-outside-inclusive-window-rejected"
DOMAINS = ("linear", "display")
NUMERIC_EXAMPLE_FRAMES = [[0.0, 0.0], [2.0, 4.0], [0.0, 0.0]]
NUMERIC_EXAMPLE_WEIGHTS = [0.25, 0.5, 0.25]
NUMERIC_EXAMPLE_WINDOW = [0, 2]
NUMERIC_EXAMPLE_SAMPLE = [1.0, 2.0]

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "frames",
    "weights",
    "window",
    "oracle",
    "domain",
    "applyMutant",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "frames",
    "weights",
    "window",
    "oracle",
    "domain",
    "applyMutant",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integrate_frames(frames: list[list[float]], weights: list[float]) -> list[float]:
    """Weighted sum. Every weight is applied. Nothing is dropped or renormalized."""
    width = len(frames[0])
    sample = [0.0] * width
    for weight, frame in zip(weights, frames):
        for index, value in enumerate(frame):
            sample[index] += weight * value
    return sample


def _finite(value: object, label: str) -> float:
    require(not isinstance(value, bool), f"{label} must be a number")
    require(isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _frames(frames: object) -> list[list[float]]:
    require(isinstance(frames, list) and len(frames) > 0, "frames must be a non-empty list")
    parsed: list[list[float]] = []
    width: int | None = None
    for index, frame in enumerate(frames):
        require(isinstance(frame, list) and len(frame) > 0, f"frame {index} must be a non-empty list")
        if width is None:
            width = len(frame)
        else:
            require(len(frame) == width, "frames must share one length")
        parsed.append([_finite(item, f"frame {index} sample {sample}") for sample, item in enumerate(frame)])
    return parsed


def _weights(weights: object, count: int) -> list[float]:
    require(isinstance(weights, list) and len(weights) == count, "weights must match the frame count")
    return [_finite(item, f"weight {index}") for index, item in enumerate(weights)]


def _oracle(oracle: object, width: int) -> list[float]:
    require(isinstance(oracle, list) and len(oracle) == width, "oracle must match the sample length")
    return [_finite(item, f"oracle {index}") for index, item in enumerate(oracle)]


def _window(window: object, count: int) -> tuple[int, int]:
    require(isinstance(window, list) and len(window) == 2, "window must be an index range")
    start, end = window
    require(type(start) is int and type(end) is int, "window bounds must be integers")
    require(0 <= start <= end < count, "window is outside the frame stack")
    return start, end


def _identity(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    return result


def decide_integration(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    frames: list[list[float]],
    weights: list[float],
    window: tuple[int, int],
    oracle: list[float],
    domain: str,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Compare the weighted exposure sum with an independent oracle.

    The sample always uses every supplied weight. Negative weights and frames
    outside the shutter window stay in that sum, then the decision is rejected.
    """
    start, end = window
    sample = integrate_frames(frames, weights)
    negatives = [index for index, weight in enumerate(weights) if weight < 0.0]
    outside = [
        index
        for index, weight in enumerate(weights)
        if weight != 0.0 and (index < start or index > end)
    ]
    weight_sum = 0.0
    for weight in weights:
        weight_sum += weight
    mismatch = [index for index, value in enumerate(sample) if abs(value - oracle[index]) > TOLERANCE]
    sample_energy = 0.0
    for value in sample:
        sample_energy += value
    weighted_energy = 0.0
    for weight, frame in zip(weights, frames):
        frame_energy = 0.0
        for value in frame:
            frame_energy += value
        weighted_energy += weight * frame_energy
    energy_gap = abs(sample_energy - weighted_energy) > TOLERANCE

    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "boundary policy: " + BOUNDARY_POLICY,
    ]
    rejected: list[str] = []
    if apply_mutant:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if domain != "linear":
        rejected.append("display-encoded-average")
        reasons.append("display-encoded frames were not accepted as the exposure integral")
    if negatives:
        rejected.append("negative-weight")
        reasons.append(
            "negative weight rejected and not dropped at " + ",".join(str(index) for index in negatives)
        )
    if abs(weight_sum - 1.0) > TOLERANCE:
        rejected.append("unnormalized-temporal-weights")
        reasons.append("temporal weights must sum to 1")
    if outside:
        rejected.append("frame-outside-shutter-window")
        reasons.append(
            "frame outside the shutter window included in the sum at "
            + ",".join(str(index) for index in outside)
        )
    if mismatch:
        rejected.append("oracle-mismatch")
        reasons.append("integrated sample differs from the independent oracle by more than 1e-9")
    if energy_gap:
        rejected.append("energy-not-preserved")
        reasons.append("total energy was not preserved under the boundary policy")
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        reasons.append("linear exposure integral retained for " + evidence_id)
        reasons.append("method: " + METHOD)
    questions = [
        "physical S23 capture was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence_id, claim, list(weights), [start, end], list(sample)],
        "openQuestions": questions,
    }
    return _seal(result)


def _components(payload: dict) -> tuple:
    evidence = _identity(payload["evidenceId"], "evidenceId")
    claim = _identity(payload["claim"], "claim")
    frames = _frames(payload["frames"])
    weights = _weights(payload["weights"], len(frames))
    window = _window(payload["window"], len(frames))
    oracle = _oracle(payload["oracle"], len(frames[0]))
    domain = payload["domain"]
    require(domain in DOMAINS, "domain must be linear or display")
    require(type(payload["applyMutant"]) is bool, "applyMutant must be a bool")
    return evidence, claim, frames, weights, window, oracle, domain, payload["applyMutant"]


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to one temporal-integration fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, frames, weights, window, oracle, domain, apply_mutant = _components(document)
    return decide_integration(
        case_id=PHASE,
        evidence_id=evidence,
        claim=claim,
        frames=frames,
        weights=weights,
        window=window,
        oracle=oracle,
        domain=domain,
        apply_mutant=apply_mutant,
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Integrate one declared exposure. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = _identity(payload["caseId"], "caseId")
    evidence, claim, frames, weights, window, oracle, domain, apply_mutant = _components(payload)
    return decide_integration(
        case_id=case_id,
        evidence_id=evidence,
        claim=claim,
        frames=frames,
        weights=weights,
        window=window,
        oracle=oracle,
        domain=domain,
        apply_mutant=apply_mutant,
    )
