"""TC-P113-03 Temporal integration energy.

Linear-domain weighted energy and trail extent must match the exposure window
from the shutter formula. Display-encoded averages and unnormalized weights fail.
"""

from __future__ import annotations

import importlib.util
from fractions import Fraction
from pathlib import Path

CASE_ID = "TC-P113-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
REPEATS = ("constant-velocity", "acceleration", "partial-boundary")
DOMAINS = ("linear", "display")
NEGATIVE_TOKEN = "display-encoded-or-unnormalized-weights"
TOLERANCE = Fraction(1, 1_000_000_000)

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc03",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "domain",
    "samples",
    "weights",
    "normalized",
    "velocity",
    "acceleration",
    "shutterAngleDegrees",
    "fps",
    "independentEnergy",
    "trailExtent",
    "overlap",
    "sensorConfirmed",
    "measurementId",
    "syntheticIntegration",
)


def _near(left: Fraction, right: Fraction) -> bool:
    return abs(left - right) <= TOLERANCE


def _series(values: object, name: str) -> list[Fraction]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    return [_CORE.parse_fraction(item, name) for item in values]


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 temporal-integration repeat")
    if payload["domain"] not in DOMAINS:
        raise ValueError("domain must be linear or display")
    if type(payload["normalized"]) is not bool:
        raise ValueError("normalized must be a bool")
    if type(payload["syntheticIntegration"]) is not bool:
        raise ValueError("syntheticIntegration must be a bool")
    samples = _series(payload["samples"], "samples")
    weights = _series(payload["weights"], "weights")
    if len(samples) != len(weights):
        raise ValueError("samples and weights must have the same length")
    if repeat == "partial-boundary" and payload["overlap"] is None:
        raise ValueError("partial exposure requires overlap")
    if repeat != "partial-boundary" and payload["overlap"] is not None:
        raise ValueError("overlap is only valid for partial-boundary")
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
    window = _CORE.exposure_seconds(payload["shutterAngleDegrees"], payload["fps"])
    velocity = _CORE.parse_fraction(payload["velocity"], "velocity")
    acceleration = _CORE.parse_fraction(payload["acceleration"], "acceleration")
    total_weight = sum(weights, Fraction(0))
    if total_weight == 0:
        raise ValueError("weights must not sum to zero")
    energy = sum((weight * sample for weight, sample in zip(weights, samples)), Fraction(0))
    energy = energy / total_weight
    overlap = None
    if payload["overlap"] is not None:
        overlap = _CORE.parse_positive(payload["overlap"], "overlap")
        if overlap > 1:
            raise ValueError("overlap must be in (0, 1]")
    if repeat == "constant-velocity":
        trail = velocity * window
        expected_energy = energy
    elif repeat == "acceleration":
        trail = velocity * window + Fraction(1, 2) * acceleration * window * window
        expected_energy = energy
    else:
        trail = velocity * window * overlap
        expected_energy = energy * overlap
    claimed_energy = _CORE.parse_fraction(payload["independentEnergy"], "independentEnergy")
    claimed_trail = _CORE.parse_fraction(payload["trailExtent"], "trailExtent")
    extra: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        INTERVENTION,
        EXPECTED,
        f"repeat {repeat}",
        REPEAT,
        f"exposure window {_CORE.format_number(window)} s",
        f"linear energy {_CORE.format_number(expected_energy)}",
        f"trail extent {_CORE.format_number(trail)}",
    ]
    if payload["domain"] == "display":
        extra.append(NEGATIVE_TOKEN)
        extra.append("display-encoded-temporal-average")
        reasons.append(NEGATIVE)
    if payload["normalized"] is False or not _near(total_weight, Fraction(1)):
        if NEGATIVE_TOKEN not in extra:
            extra.append(NEGATIVE_TOKEN)
        extra.append("unnormalized-temporal-weights")
        reasons.append(NEGATIVE)
    elif payload["domain"] == "linear" and (
        not _near(expected_energy, claimed_energy) or not _near(trail, claimed_trail)
    ):
        extra.append("energy-or-trail-mismatch")
        reasons.append(
            "independent linear energy or trail extent missed the exposure window"
        )
    else:
        reasons.append("linear-domain energy and trail match within tolerance")
    return _CORE.reject_more(result, extra, reasons)
