"""TC-P108-01 History without reprojection.

Host fixture. A stationary-pixel average that leaves depth trails must fail.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-01"
NAME = 'History without reprojection'
INTERVENTION = 'Move a known object while previous depth remains in its original pixel coordinates.'
EXPECTED = 'Reject unaligned history or warp it correctly before temporal blending.'
NEGATIVE = 'A stationary-pixel average that leaves depth trails must fail.'
REPEAT = 'Repeat translation, rotation, scale change, and camera motion.'
NEGATIVE_TOKEN = 'stationary-pixel-average-depth-trail'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'objectMoved', 'previousDepth', 'depthAtOriginalPixel', 'warpedBeforeBlend')

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



def evaluate(payload: dict) -> dict:
    """Reject a stationary-pixel average whose depth at the old pixel is unchanged."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    for flag in ("objectMoved", "warpedBeforeBlend"):
        gate.require(type(payload[flag]) is bool, flag + " must be a bool")
    previous = gate.finite_number(payload["previousDepth"], "previousDepth")
    at_pixel = gate.finite_number(payload["depthAtOriginalPixel"], "depthAtOriginalPixel")
    trail = payload["objectMoved"] and (not payload["warpedBeforeBlend"]) and at_pixel == previous
    rejected = list(observation["rejected"])
    extra = []
    if trail:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("depth at the original pixel still equals the previous depth")
    else:
        extra.append("history was warped before blending or the original pixel does not keep a depth trail")
    return _finish(observation, rejected, extra)
