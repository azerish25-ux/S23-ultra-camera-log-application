"""TC-P108-05 Mixed-pixel boundaries.

Host fixture. A dilated binary person mask must not pass demanding boundary quality by itself.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-05"
NAME = 'Mixed-pixel boundaries'
INTERVENTION = 'Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds.'
EXPECTED = 'Preserve plausible partial coverage and bound temporal halos under the selected safe settings.'
NEGATIVE = 'A dilated binary person mask must not pass demanding boundary quality by itself.'
REPEAT = 'Repeat backlighting, crossing subjects, and different foreground-background contrast.'
NEGATIVE_TOKEN = 'dilated-binary-person-mask'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'coverage', 'halo', 'haloLimit', 'claimsBoundaryQuality')

_GATE = None


def _gate():
    global _GATE
    if _GATE is None:
        path = Path(__file__).resolve().parent / "p108_detect_occlusion_and_scene_discontinuities.py"
        spec = importlib.util.spec_from_file_location("p108_detect_occlusion_and_scene_discontinuities", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _GATE = module
    return _GATE


def _require_keys(payload: dict) -> None:
    gate = _gate()
    gate.require(isinstance(payload, dict), "payload must be an object")
    missing = set(PAYLOAD_KEYS) - set(payload)
    extra = set(payload) - set(PAYLOAD_KEYS)
    gate.require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    gate.require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))


def _finish(observation: dict, rejected: list[str], extra_reasons: list[str]) -> dict:
    gate = _gate()
    reasons = gate.case_reasons(
        CASE_ID,
        NAME,
        observation["repeat"],
        EXPECTED,
        INTERVENTION,
        observation["counts"],
        extra_reasons,
    )
    return gate.finish(
        case_id=CASE_ID,
        evidence=observation["evidence"],
        claim=CASE_ID,
        counts=observation["counts"],
        rejected=rejected,
        reasons=reasons,
        open_questions=[gate.OPEN_QUESTION, REPEAT],
    )



def _coverage(values):
    gate = _gate()
    gate.require(isinstance(values, list) and len(values) >= 1, "coverage must contain at least 1 weight")
    parsed = []
    for index, value in enumerate(values):
        number = gate.finite_number(value, f"coverage[{index}]")
        gate.require(0.0 <= number <= 1.0, f"coverage[{index}] must be inside [0, 1]")
        parsed.append(number)
    return parsed


def evaluate(payload: dict) -> dict:
    """Partial coverage is required. A dilated binary mask is not boundary quality."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    coverage = _coverage(payload["coverage"])
    halo = gate.finite_number(payload["halo"], "halo")
    halo_limit = gate.finite_number(payload["haloLimit"], "haloLimit")
    gate.require(halo >= 0.0 and halo_limit >= 0.0, "halo and haloLimit must be >= 0")
    gate.require(type(payload["claimsBoundaryQuality"]) is bool, "claimsBoundaryQuality must be a bool")
    binary = all(value == 0.0 or value == 1.0 for value in coverage)
    rejected = list(observation["rejected"])
    extra = []
    if payload["claimsBoundaryQuality"] and binary:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("coverage is only 0 or 1")
    elif halo > halo_limit:
        rejected.insert(0, "temporal-halo-unbounded")
        extra.append("temporal halo exceeded the selected safe limit")
    else:
        extra.append("partial coverage stayed inside the halo limit")
    return _finish(observation, rejected, extra)
