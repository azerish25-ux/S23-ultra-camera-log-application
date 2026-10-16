"""TC-P108-04 Scene-cut contamination.

Host fixture. Continuous timestamps alone must not preserve temporal state across a real cut.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-04"
NAME = 'Scene-cut contamination'
INTERVENTION = 'Join unrelated scenes or switch source clips while temporal state is populated.'
EXPECTED = 'Reset relevant history and prevent previous-image depth or color from leaking into the new shot.'
NEGATIVE = 'Continuous timestamps alone must not preserve temporal state across a real cut.'
REPEAT = 'Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination.'
NEGATIVE_TOKEN = 'history-carried-across-edit-boundary'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'editBoundary', 'timestampsContinuous', 'carryHistory')

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
    """A real cut resets history. Continuous timestamps do not keep the previous shot."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    for flag in ("editBoundary", "timestampsContinuous", "carryHistory"):
        gate.require(type(payload[flag]) is bool, flag + " must be a bool")
    rejected = list(observation["rejected"])
    extra = []
    carried = payload["editBoundary"] and payload["carryHistory"]
    if carried and payload["timestampsContinuous"]:
        rejected.insert(0, gate.MUTANT)
    if carried:
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("temporal state crossed an edit boundary")
    elif payload["editBoundary"]:
        extra.append("edit boundary reset history even though timestamps stayed continuous")
    else:
        extra.append("no edit boundary was claimed")
    return _finish(observation, rejected, extra)
