"""TC-P108-07 Bokeh ordering and leakage.

Host fixture. Uniform background blur with no foreground coverage model must fail.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-07"
NAME = 'Bokeh ordering and leakage'
INTERVENTION = 'Render strong foreground defocus with bright lights behind an in-focus opaque subject.'
EXPECTED = 'Respect layering and normalized energy while declaring unavoidable missing-background approximations.'
NEGATIVE = 'Uniform background blur with no foreground coverage model must fail.'
REPEAT = 'Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.'
NEGATIVE_TOKEN = 'uniform-background-blur-without-coverage'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'foregroundCoverage', 'uniformBackgroundBlur', 'energyNormalized')

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



def _weights(values):
    gate = _gate()
    gate.require(isinstance(values, list), "foregroundCoverage must be a list")
    parsed = []
    for index, value in enumerate(values):
        number = gate.finite_number(value, f"foregroundCoverage[{index}]")
        gate.require(0.0 <= number <= 1.0, f"foregroundCoverage[{index}] must be inside [0, 1]")
        parsed.append(number)
    return parsed


def evaluate(payload: dict) -> dict:
    """Uniform background blur without a foreground coverage model is rejected."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    coverage = _weights(payload["foregroundCoverage"])
    gate.require(type(payload["uniformBackgroundBlur"]) is bool, "uniformBackgroundBlur must be a bool")
    gate.require(type(payload["energyNormalized"]) is bool, "energyNormalized must be a bool")
    lacks_coverage = len(coverage) == 0 or all(value == 0.0 for value in coverage)
    rejected = list(observation["rejected"])
    extra = []
    if payload["uniformBackgroundBlur"] and lacks_coverage:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("background blur was uniform and no foreground coverage was modelled")
    if not payload["energyNormalized"]:
        rejected.append("defocus-energy-not-normalized")
        extra.append("defocus energy was not normalized")
    if not rejected or (NEGATIVE_TOKEN not in rejected and "defocus-energy-not-normalized" not in rejected):
        extra.append("layering kept a foreground coverage model and normalized energy")
    return _finish(observation, rejected, extra)
