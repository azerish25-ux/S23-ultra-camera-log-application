"""TC-P117-03 Temporal integration energy.

Host fixture. Exposure integration is a normalized linear-domain sum over the
overlap of the requested window and the clip. Display-encoded averages and
unnormalized weights are rejected. Trail extent is |velocity| * overlap plus
half |acceleration| * overlap squared. Stabilization geometry stays shared.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
NEGATIVE_TOKEN = "display-encoded-average"
UNNORMALIZED_TOKEN = "unnormalized-temporal-weights"
ENERGY_TOKEN = "energy-mismatch"
TRAIL_TOKEN = "trail-extent-mismatch"
OUTSIDE_TOKEN = "exposure-outside-clip"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "domain",
    "weights",
    "linearValues",
    "velocity",
    "acceleration",
    "exposureStart",
    "exposureEnd",
    "clipStart",
    "clipEnd",
    "reportedEnergy",
    "reportedTrailExtent",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def overlap_duration(exposure_start: float, exposure_end: float, clip_start: float, clip_end: float) -> float:
    return max(0.0, min(exposure_end, clip_end) - max(exposure_start, clip_start))


def linear_energy(weights: list[float], values: list[float]) -> float:
    total = 0.0
    for weight, value in zip(weights, values):
        total += weight * value
    return total


def trail_extent(velocity: float, acceleration: float, duration: float) -> float:
    return abs(velocity) * duration + 0.5 * abs(acceleration) * duration * duration


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    domain = payload["domain"]
    if domain not in {"linear", "display"}:
        raise ValueError("domain must be linear or display")
    weights_in = payload["weights"]
    values_in = payload["linearValues"]
    if not isinstance(weights_in, list) or not isinstance(values_in, list) or not weights_in:
        raise ValueError("weights and linearValues must be non-empty lists")
    if len(weights_in) != len(values_in):
        raise ValueError("weights and linearValues must have the same length")
    weights = [_CORE.require_number(item, f"weights[{index}]") for index, item in enumerate(weights_in)]
    values = [_CORE.require_number(item, f"linearValues[{index}]") for index, item in enumerate(values_in)]
    velocity = _CORE.require_number(payload["velocity"], "velocity")
    acceleration = _CORE.require_number(payload["acceleration"], "acceleration")
    exposure_start = _CORE.require_number(payload["exposureStart"], "exposureStart")
    exposure_end = _CORE.require_number(payload["exposureEnd"], "exposureEnd")
    clip_start = _CORE.require_number(payload["clipStart"], "clipStart")
    clip_end = _CORE.require_number(payload["clipEnd"], "clipEnd")
    reported_energy = _CORE.require_number(payload["reportedEnergy"], "reportedEnergy")
    reported_trail = _CORE.require_number(payload["reportedTrailExtent"], "reportedTrailExtent")
    if exposure_end <= exposure_start or clip_end <= clip_start:
        raise ValueError("windows must be non-empty and increasing")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    duration = overlap_duration(exposure_start, exposure_end, clip_start, clip_end)
    requested = exposure_end - exposure_start
    energy = linear_energy(weights, values)
    weight_sum = 0.0
    for weight in weights:
        weight_sum += weight
    extent = trail_extent(velocity, acceleration, duration)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    reasons.append(
        "linearEnergy="
        + _CORE.format_number(energy)
        + " trailExtent="
        + _CORE.format_number(extent)
        + " overlap="
        + _CORE.format_number(duration)
    )
    rejected = list(analysis["rejectedClaims"])
    if domain != "linear":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if abs(weight_sum - 1.0) > _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(UNNORMALIZED_TOKEN)
        reasons.append("temporal weights must sum to 1 and are not renormalized")
    if duration <= _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(OUTSIDE_TOKEN)
        reasons.append("exposure window does not overlap the clip")
    elif requested - duration > _CORE.ABSOLUTE_TOLERANCE:
        reasons.append("partial exposure at the clip boundary uses the overlap duration")
    if not _CORE.close(energy, reported_energy):
        rejected.append(ENERGY_TOKEN)
        reasons.append("integrated energy does not match the reported linear sum")
    if not _CORE.close(extent, reported_trail):
        rejected.append(TRAIL_TOKEN)
        reasons.append("trail extent does not match velocity and acceleration over the overlap")
    preserved = [
        evidence,
        "linearEnergy=" + _CORE.format_number(energy),
        "trailExtent=" + _CORE.format_number(extent),
        list(weights),
    ]
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
