"""TC-P108-03 Relative-scale pumping.

Host fixture. Independent min-max normalization per frame must fail.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-03"
NAME = 'Relative-scale pumping'
INTERVENTION = 'Introduce a near object or scene-content change that alters raw model depth normalization.'
EXPECTED = 'Align valid relative depth consistently or reset honestly without arbitrary global focus shifts.'
NEGATIVE = 'Independent min-max normalization per frame must fail.'
REPEAT = 'Repeat stationary backgrounds with changing foreground occupancy.'
NEGATIVE_TOKEN = 'independent-min-max-normalization'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'frames', 'backgroundIndex', 'backgroundStationary')

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



def _scale_claim(frames, background_index, stationary):
    gate = _gate()
    gate.require(type(stationary) is bool, "backgroundStationary must be a bool")
    gate.require(type(background_index) is int and background_index >= 0, "backgroundIndex must be a non-negative int")
    gate.require(isinstance(frames, list) and len(frames) >= 2, "frames must contain at least 2 sequences")
    parsed = []
    width = None
    for frame_index, frame in enumerate(frames):
        gate.require(isinstance(frame, list) and len(frame) >= 2, f"frames[{frame_index}] must contain at least 2 numbers")
        if width is None:
            width = len(frame)
        gate.require(len(frame) == width, "frames must share one width")
        gate.require(background_index < width, "backgroundIndex is outside the frame")
        parsed.append([gate.finite_number(value, f"frames[{frame_index}][{sample}]") for sample, value in enumerate(frame)])
    if not stationary:
        return None
    background = [frame[background_index] for frame in parsed]
    if max(background) - min(background) <= 0.0:
        return None
    unit = all(min(frame) == 0.0 and max(frame) == 1.0 for frame in parsed)
    if unit:
        return NEGATIVE_TOKEN
    return "relative-scale-pump"


def evaluate(payload: dict) -> dict:
    """Reject per-frame min-max normalization that moves a stationary background."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    claim = _scale_claim(payload["frames"], payload["backgroundIndex"], payload["backgroundStationary"])
    rejected = list(observation["rejected"])
    extra = []
    if claim == NEGATIVE_TOKEN:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("each frame was independently scaled to [0, 1] and the stationary background moved")
    elif claim:
        rejected.insert(0, claim)
        extra.append("stationary background depth changed across frames")
    else:
        extra.append("stationary background depth stayed aligned")
    return _finish(observation, rejected, extra)
